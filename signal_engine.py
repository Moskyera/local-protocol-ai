from market_data_service import get_chart_data
from config import config
from logger import log

# =========================================
# ADVANCED AI SIGNAL ENGINE
# =========================================

def generate_signal(symbol=config.DEFAULT_SYMBOL):
    log.debug(f"Generating signal for {symbol}")
    df = get_chart_data(symbol)
    latest = df.iloc[-1]

    price = latest["close"]
    sma20 = latest["SMA20"]
    rsi = latest["RSI"]
    macd = latest["MACD"]
    macd_signal = latest["MACD_SIGNAL"]

    market_signal = "NEUTRAL"
    confidence = 50
    market_state = "RANGING"
    reason = "Market conditions remain balanced."

    if rsi > 60:
        market_state = "TRENDING BULLISH"
    elif rsi < 40:
        market_state = "TRENDING BEARISH"
    elif 45 <= rsi <= 55:
        market_state = "RANGING"
    else:
        market_state = "VOLATILE"

    if (rsi >= 60 and macd > macd_signal and price > sma20):
        market_signal = "STRONG BUY"
        confidence = 92
        reason = "Strong bullish momentum with positive MACD crossover and price above SMA20."
    elif (rsi > 50 and macd > macd_signal and price > sma20):
        market_signal = "BUY"
        confidence = 80
        reason = "Momentum improving with bullish MACD structure and price holding above SMA20."
    elif (macd > macd_signal and rsi >= 45):
        market_signal = "WATCH"
        confidence = 65
        reason = "Bearish momentum weakening with possible reversal structure forming."
    elif (rsi <= 35 and macd < macd_signal and price < sma20):
        market_signal = "STRONG SELL"
        confidence = 93
        reason = "Strong downside pressure with bearish momentum accelerating."
    elif (rsi < 45 and macd < macd_signal and price < sma20):
        market_signal = "SELL"
        confidence = 82
        reason = "Weak market structure with bearish MACD behavior and price below SMA20."

    log.info(f"Signal generated: {market_signal} | Confidence: {confidence}% | RSI: {rsi:.2f}")
    return {
        "symbol": symbol,
        "signal": market_signal,
        "confidence": confidence,
        "market_state": market_state,
        "price": round(price, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd, 2),
        "macd_signal": round(macd_signal, 2),
        "reason": reason
    }