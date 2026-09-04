from multi_timeframe_engine import analyze_multi_timeframe
from config import config
from logger import log

def generate_consensus(symbol=config.DEFAULT_SYMBOL):
    log.debug(f"Generating consensus for {symbol}")
    data = analyze_multi_timeframe(symbol)

    bullish = 0
    bearish = 0
    neutral = 0

    for tf, info in data.items():
        signal = info["signal"]
        if signal == "BULLISH":
            bullish += 1
        elif signal == "BEARISH":
            bearish += 1
        else:
            neutral += 1

    consensus = "NEUTRAL"
    confidence = 50
    explanation = "Market conditions remain mixed."

    if bullish >= 3:
        consensus = "FULL BULLISH REVERSAL"
        confidence = 90
        explanation = "Bullish momentum expanding across multiple timeframes."
    elif bearish >= 3:
        consensus = "STRONG BEARISH TREND"
        confidence = 92
        explanation = "Bearish momentum dominating across higher timeframes."
    elif bullish >= 1 and bearish >= 2:
        consensus = "BEAR MARKET RALLY"
        confidence = 76
        explanation = "Short-term bullish momentum inside a broader bearish market structure."
    elif bullish == 2 and bearish <= 1:
        consensus = "EARLY REVERSAL PHASE"
        confidence = 68
        explanation = "Recovery signals emerging but macro confirmation remains incomplete."

    log.info(f"Consensus: {consensus} | Confidence: {confidence}% | Bullish: {bullish} | Bearish: {bearish}")
    return {
        "symbol": symbol,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "consensus": consensus,
        "confidence": confidence,
        "explanation": explanation
    }