# =========================================
# AI PORTFOLIO ENGINE
# =========================================

def generate_portfolio_strategy(

    market_score,

    regime,

    volatility,

    smart_money,

    whale_activity
):

    # =====================================
    # DEFAULTS
    # =====================================

    btc_allocation = 20
    cash_allocation = 80

    risk_mode = "DEFENSIVE"

    strategy = (
        "Capital preservation mode."
    )

    # =====================================
    # STRONG BULLISH ENVIRONMENT
    # =====================================

    if (

        market_score >= 80

        and

        regime == "BULLISH"
    ):

        btc_allocation = 90
        cash_allocation = 10

        risk_mode = "AGGRESSIVE"

        strategy = (

            "Strong bullish environment "
            "favoring aggressive exposure."
        )

    # =====================================
    # HEALTHY MARKET
    # =====================================

    elif market_score >= 65:

        btc_allocation = 70
        cash_allocation = 30

        risk_mode = "MODERATE"

        strategy = (

            "Healthy market conditions "
            "with balanced opportunity."
        )

    # =====================================
    # MIXED MARKET
    # =====================================

    elif market_score >= 50:

        btc_allocation = 50
        cash_allocation = 50

        risk_mode = "CAUTIOUS"

        strategy = (

            "Mixed market environment "
            "requiring balanced positioning."
        )

    # =====================================
    # WEAK MARKET
    # =====================================

    elif market_score >= 35:

        btc_allocation = 30
        cash_allocation = 70

        risk_mode = "DEFENSIVE"

        strategy = (

            "Weak market structure "
            "favoring defensive positioning."
        )

    # =====================================
    # HIGH RISK MARKET
    # =====================================

    else:

        btc_allocation = 10
        cash_allocation = 90

        risk_mode = "MAX DEFENSE"

        strategy = (

            "High-risk environment "
            "favoring capital protection."
        )

    # =====================================
    # SMART MONEY BOOST
    # =====================================

    if smart_money in [

        "STEALTH ACCUMULATION",

        "BULLISH INSTITUTIONAL FLOW"
    ]:

        btc_allocation += 10
        cash_allocation -= 10

    # =====================================
    # WHALE BOOST
    # =====================================

    if whale_activity == (
        "WHALE ACCUMULATION"
    ):

        btc_allocation += 10
        cash_allocation -= 10

    # =====================================
    # HIGH VOLATILITY DEFENSE
    # =====================================

    if volatility == "ELEVATED":

        btc_allocation -= 10
        cash_allocation += 10

    # =====================================
    # LIMITS
    # =====================================

    btc_allocation = max(
        0,
        min(
            btc_allocation,
            100
        )
    )

    cash_allocation = max(
        0,
        min(
            cash_allocation,
            100
        )
    )

    return {

        "btc_allocation":
        btc_allocation,

        "cash_allocation":
        cash_allocation,

        "risk_mode":
        risk_mode,

        "strategy":
        strategy
    }