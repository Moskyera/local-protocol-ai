from market_data_service import get_chart_data
from config import config
from logger import log

def analyze_multi_timeframe(symbol=config.DEFAULT_SYMBOL):
    log.debug(f"Multi-timeframe analysis for {symbol}")
    timeframes = {
        "15m": "SHORT TERM",
        "1h": "INTRADAY",
        "4h": "SWING",
        "1d": "MACRO"
    }

    results = {}

    for tf, label in timeframes.items():
        signal = generate_signal_with_timeframe(symbol, tf)
        results[label] = signal

    log.info(f"Completed multi-timeframe analysis for {symbol}")
    return results


def generate_signal_with_timeframe(symbol, timeframe):
    df = get_chart_data(symbol, timeframe=timeframe, limit=100)
    latest = df.iloc[-1]

    price = latest["close"]
    sma20 = latest["SMA20"]
    rsi = latest["RSI"]
    macd = latest["MACD"]
    macd_signal = latest["MACD_SIGNAL"]

    market_signal = "NEUTRAL"

    if (rsi > 55 and macd > macd_signal and price > sma20):
        market_signal = "BULLISH"
    elif (rsi < 45 and macd < macd_signal and price < sma20):
        market_signal = "BEARISH"

    return {
        "signal": market_signal,
        "rsi": round(rsi, 2),
        "macd": round(macd, 2),
        "price": round(price, 2)
    }