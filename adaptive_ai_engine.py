# =========================================
# ADAPTIVE AI CONFIDENCE ENGINE
# =========================================

def calculate_adaptive_confidence(

    signal,

    consensus,

    volatility,

    regime,

    performance_accuracy
):

    confidence = 50

    # =====================================
    # SIGNAL BOOST
    # =====================================

    if signal in [

        "BUY",

        "STRONG BUY"
    ]:

        confidence += 10

    elif signal in [

        "SELL",

        "STRONG SELL"
    ]:

        confidence += 10

    # =====================================
    # CONSENSUS BOOST
    # =====================================

    if consensus in [

        "FULL BULLISH REVERSAL",

        "EARLY REVERSAL PHASE"
    ]:

        confidence += 15

    elif consensus in [

        "FULL BEARISH TREND",

        "BEAR MARKET RALLY"
    ]:

        confidence += 15

    # =====================================
    # REGIME ADJUSTMENT
    # =====================================

    if regime == "BULLISH":

        confidence += 10

    elif regime == "BEARISH":

        confidence -= 10

    # =====================================
    # VOLATILITY ADJUSTMENT
    # =====================================

    if volatility == "ELEVATED":

        confidence -= 10

    elif volatility == "STABLE":

        confidence += 5

    # =====================================
    # PERFORMANCE BOOST
    # =====================================

    if performance_accuracy >= 60:

        confidence += 15

    elif performance_accuracy >= 50:

        confidence += 10

    elif performance_accuracy < 40:

        confidence -= 10

    # =====================================
    # LIMITS
    # =====================================

    confidence = max(

        0,

        min(
            confidence,
            100
        )
    )

    return confidence

# =========================================
# AI OUTLOOK ENGINE
# =========================================

def generate_ai_outlook(

    confidence,

    regime
):

    # =====================================
    # STRONG BULLISH
    # =====================================

    if (

        confidence >= 80

        and

        regime == "BULLISH"
    ):

        return (
            "Strong bullish continuation "
            "likely."
        )

    # =====================================
    # MODERATE BULLISH
    # =====================================

    elif confidence >= 65:

        return (
            "Recovery structure "
            "developing."
        )

    # =====================================
    # NEUTRAL
    # =====================================

    elif confidence >= 45:

        return (
            "Market consolidating "
            "without clear direction."
        )

    # =====================================
    # BEARISH
    # =====================================

    else:

        return (
            "Bearish pressure "
            "still dominant."
        )