from market_data_service import get_chart_data
from config import config
from logger import log

def generate_alerts(symbol=config.DEFAULT_SYMBOL):
    log.debug(f"Generating alerts for {symbol}")
    df = get_chart_data(symbol)
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    alerts = []

    rsi_now = latest["RSI"]
    rsi_prev = previous["RSI"]
    macd_now = latest["MACD"]
    macd_prev = previous["MACD"]
    signal_now = latest["MACD_SIGNAL"]
    signal_prev = previous["MACD_SIGNAL"]
    price = latest["close"]
    sma20 = latest["SMA20"]

    if rsi_prev < 50 and rsi_now >= 50:
        alerts.append("RSI crossed above 50 (bullish momentum shift)")
    if rsi_prev > 50 and rsi_now <= 50:
        alerts.append("RSI crossed below 50 (bearish momentum shift)")
    if rsi_now >= 70:
        alerts.append("Market entering overbought territory")
    if rsi_now <= 30:
        alerts.append("Market entering oversold territory")
    if macd_prev < signal_prev and macd_now > signal_now:
        alerts.append("Bullish MACD crossover detected")
    if macd_prev > signal_prev and macd_now < signal_now:
        alerts.append("Bearish MACD crossover detected")
    if price > sma20:
        alerts.append("Price trading above SMA20 support")
    if price < sma20:
        alerts.append("Price trading below SMA20 resistance")

    if len(alerts) == 0:
        alerts.append("No major technical events detected")

    log.info(f"Generated {len(alerts)} alerts for {symbol}")
    return alerts