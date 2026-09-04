from config import config
from logger import log

def calculate_market_score(signal, regime, phase, volatility, smart_money, whale_activity, rsi, macd):
    log.debug(f"Calculating market score for {signal} | Regime: {regime}")

    trend_score = 50
    momentum_score = 50
    smart_money_score = 50
    volatility_score = 50
    institutional_score = 50

    if regime == "BULLISH":
        trend_score += 25
    elif regime == "BEARISH":
        trend_score -= 20

    if phase in ["FULL BULLISH TREND", "EARLY BULLISH REVERSAL"]:
        trend_score += 20
    elif phase in ["PANIC SELLING", "DISTRIBUTION"]:
        trend_score -= 20

    if rsi > 55:
        momentum_score += 20
    elif rsi < 45:
        momentum_score -= 20
    if macd > 0:
        momentum_score += 15
    else:
        momentum_score -= 10

    if smart_money in ["BULLISH INSTITUTIONAL FLOW", "STEALTH ACCUMULATION"]:
        smart_money_score += 30
    elif smart_money in ["DISTRIBUTION", "WEAK RALLY"]:
        smart_money_score -= 20

    if whale_activity == "WHALE ACCUMULATION":
        institutional_score += 30
    elif whale_activity == "LIQUIDATION EVENT":
        institutional_score -= 25

    if volatility == "STABLE":
        volatility_score += 20
    elif volatility == "ELEVATED":
        volatility_score -= 20

    final_score = (trend_score + momentum_score + smart_money_score + volatility_score + institutional_score) / 5
    final_score = max(0, min(round(final_score), 100))

    # Interpretation
    if final_score >= 80:
        interpretation = "Excellent market structure with strong institutional participation."
    elif final_score >= 65:
        interpretation = "Healthy market environment with improving momentum."
    elif final_score >= 50:
        interpretation = "Mixed market conditions with moderate opportunity."
    elif final_score >= 35:
        interpretation = "Weak market structure with elevated caution."
    else:
        interpretation = "High-risk environment with bearish pressure."

    log.info(f"Market Score: {final_score}/100 | Phase: {phase}")
    return {
        "final_score": final_score,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "smart_money_score": smart_money_score,
        "volatility_score": volatility_score,
        "institutional_score": institutional_score,
        "interpretation": interpretation
    }