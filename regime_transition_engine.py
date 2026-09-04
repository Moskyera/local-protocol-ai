from config import config
from logger import log

def detect_market_phase(rsi, macd, signal, regime, volatility):
    log.debug(f"Detecting market phase | RSI:{rsi} | MACD:{macd} | Regime:{regime}")

    if rsi < 30 and regime == "BEARISH" and volatility == "ELEVATED":
        return "PANIC SELLING", "Extreme fear conditions dominating the market."
    elif 35 <= rsi <= 50 and macd < 0 and signal in ["WATCH", "BUY"]:
        return "ACCUMULATION", "Buyers slowly returning while bearish momentum weakens."
    elif rsi > 50 and macd > 0 and regime == "BEARISH":
        return "EARLY BULLISH REVERSAL", "Momentum improving inside a broader bearish structure."
    elif rsi > 60 and macd > 0 and regime == "BULLISH":
        return "FULL BULLISH TREND", "Strong bullish momentum and trend continuation."
    elif rsi > 65 and signal in ["WATCH", "SELL"]:
        return "DISTRIBUTION", "Possible smart money profit-taking behavior."
    elif regime == "BEARISH" and rsi > 45 and macd < 0:
        return "BEAR MARKET RALLY", "Temporary bullish recovery inside a bearish market."
    
    return "NEUTRAL", "Market currently lacking clear directional structure."