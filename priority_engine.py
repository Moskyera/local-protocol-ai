# =========================================
# PRIORITY ENGINE
# =========================================

def calculate_priority_score(

    market_score,

    signal,

    smart_money,

    whale_activity,

    phase
):

    score = 0

    # =====================================
    # MARKET SCORE
    # =====================================

    score += market_score

    # =====================================
    # SIGNAL BONUS
    # =====================================

    if signal == "BUY":

        score += 20

    elif signal == "WATCH":

        score += 10

    elif signal == "SELL":

        score -= 10

    # =====================================
    # SMART MONEY
    # =====================================

    if smart_money == "ACCUMULATION":

        score += 15

    elif smart_money == "DISTRIBUTION":

        score -= 15

    # =====================================
    # WHALES
    # =====================================

    if whale_activity == "ACCUMULATING":

        score += 15

    elif whale_activity == "SELLING":

        score -= 15

    # =====================================
    # MARKET PHASE
    # =====================================

    if phase == "ACCUMULATION":

        score += 10

    elif phase == "MARKUP":

        score += 20

    elif phase == "DISTRIBUTION":

        score -= 20

    elif phase == "MARKDOWN":

        score -= 30

    # =====================================
    # NORMALIZE
    # =====================================

    if score > 100:

        score = 100

    if score < 0:

        score = 0

    # =====================================
    # LABEL
    # =====================================

    label = "LOW PRIORITY"

    if score >= 80:

        label = "ELITE SETUP"

    elif score >= 65:

        label = "HIGH PRIORITY"

    elif score >= 50:

        label = "WATCHLIST"

    return {

        "score": score,

        "label": label
    }