from market_data_service import get_chart_data
from config import config
from logger import log

def analyze_volatility(symbol=config.DEFAULT_SYMBOL):
    log.debug(f"Analyzing volatility for {symbol}")
    df = get_chart_data(symbol)
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    alerts = []

    current_price = latest["close"]
    previous_price = previous["close"]
    change_percent = ((current_price - previous_price) / previous_price) * 100

    current_macd = latest["MACD"]
    previous_macd = previous["MACD"]
    macd_delta = current_macd - previous_macd
    rsi = latest["RSI"]

    if abs(change_percent) >= 2:
        alerts.append(f"High volatility detected ({round(change_percent, 2)}%)")
    if abs(macd_delta) >= 50:
        alerts.append("Momentum acceleration detected")
    if rsi > 60 and current_macd > 0:
        alerts.append("Possible bullish breakout forming")
    if rsi < 40 and current_macd < 0:
        alerts.append("Possible bearish breakdown forming")
    if rsi >= 75:
        alerts.append("Extreme overbought conditions")
    if rsi <= 25:
        alerts.append("Extreme oversold conditions")

    if len(alerts) == 0:
        alerts.append("Market volatility remains stable")

    log.info(f"Volatility analysis complete for {symbol} | Change: {change_percent:.2f}%")
    return {
        "symbol": symbol,
        "change_percent": round(change_percent, 2),
        "macd_delta": round(macd_delta, 2),
        "rsi": round(rsi, 2),
        "alerts": alerts
    }