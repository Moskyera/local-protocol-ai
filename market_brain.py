from regime_engine import (
    analyze_market_regime
)

# =========================================
# MARKET BRAIN
# =========================================

def generate_market_brain():

    data = analyze_market_regime()

    stock_regime = data["stock_regime"]

    crypto_regime = data["crypto_regime"]

    overall = data["overall"]

    stock_bullish = data["stock_bullish"]

    stock_bearish = data["stock_bearish"]

    crypto_bullish = data["crypto_bullish"]

    crypto_bearish = data["crypto_bearish"]

    # =====================================
    # STOCK COMMENTARY
    # =====================================

    stock_comment = ""

    if stock_regime == "BULLISH":

        stock_comment = (
            "US equities remain resilient "
            "with buyers supporting large-cap "
            "technology and AI-related stocks."
        )

    elif stock_regime == "UNKNOWN":

        # UNKNOWN is not MIXED. Before this branch existed, a run in
        # which no quote was retrieved fell into the `else` below and
        # published confident commentary about rotational flows.
        stock_comment = (
            "Δεν υπάρχει εικόνα για τις μετοχές: δεν ανακτήθηκαν αρκετές τιμές "
            "για να βγει συμπέρασμα. Αυτό ΔΕΝ σημαίνει ουδέτερη αγορά — "
            "σημαίνει ότι δεν κοιτάξαμε."
        )

    elif stock_regime == "BEARISH":

        stock_comment = (
            "US equities are under pressure "
            "as selling activity spreads across "
            "major sectors."
        )

    else:

        stock_comment = (
            "US equities show mixed behavior "
            "with rotational flows between "
            "growth and defensive sectors."
        )

    # =====================================
    # CRYPTO COMMENTARY
    # =====================================

    crypto_comment = ""

    if crypto_regime == "BULLISH":

        crypto_comment = (
            "Crypto markets remain strong "
            "with improving sentiment across "
            "major digital assets."
        )

    elif crypto_regime == "UNKNOWN":

        # UNKNOWN is not MIXED. Before this branch existed, a run in
        # which no quote was retrieved fell into the `else` below and
        # published confident commentary about rotational flows.
        crypto_comment = (
            "Δεν υπάρχει εικόνα για τα crypto: δεν ανακτήθηκαν αρκετές τιμές "
            "για να βγει συμπέρασμα. Αυτό ΔΕΝ σημαίνει ουδέτερη αγορά."
        )

    elif crypto_regime == "BEARISH":

        crypto_comment = (
            "Crypto markets continue to weaken "
            "as broad selling pressure impacts "
            "both Bitcoin and altcoins."
        )

    else:

        crypto_comment = (
            "Crypto markets remain range-bound "
            "with mixed participation across "
            "major assets."
        )

    # =====================================
    # OVERALL COMMENTARY
    # =====================================

    overall_comment = ""

    if overall == "RISK-ON":

        overall_comment = (
            "Overall market conditions suggest "
            "a risk-on environment with improving "
            "investor confidence."
        )

    elif overall == "UNKNOWN":

        # UNKNOWN is not MIXED. Before this branch existed, a run in
        # which no quote was retrieved fell into the `else` below and
        # published confident commentary about rotational flows.
        overall_comment = (
            "Το συνολικό καθεστώς δεν υπολογίστηκε: έλειπαν τιμές σε τουλάχιστον "
            "μία από τις δύο αγορές. Καμία στάση risk-on/risk-off δεν "
            "προκύπτει από αυτό το τρέξιμο."
        )

    elif overall == "RISK-OFF":

        overall_comment = (
            "Overall market conditions suggest "
            "a defensive risk-off environment "
            "with elevated uncertainty."
        )

    else:

        overall_comment = (
            "Current cross-market behavior "
            "suggests a mixed macro environment "
            "with divergence between equities "
            "and crypto assets."
        )

    # =====================================
    # FINAL AI SUMMARY
    # =====================================

    final_summary = f"""

===================================
        AI MARKET BRAIN
===================================

STOCK MARKET ANALYSIS
---------------------

{stock_comment}

Bullish Stocks : {stock_bullish}
Bearish Stocks : {stock_bearish}

-----------------------------------

CRYPTO MARKET ANALYSIS
----------------------

{crypto_comment}

Bullish Crypto : {crypto_bullish}
Bearish Crypto : {crypto_bearish}

-----------------------------------

OVERALL MARKET REGIME
---------------------

{overall_comment}

Current Regime : {overall}

===================================

"""

    return final_summary