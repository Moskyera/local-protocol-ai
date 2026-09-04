from news_agent import get_market_news
from market_agent import get_crypto_price
from sentiment_agent import analyze_headline_sentiment

# =========================================
# AI NEWS REPORT
# =========================================

def generate_news_report():

    news = get_market_news(
        "Latest crypto stock AI market news"
    )

    report = []

    bullish = 0
    bearish = 0
    neutral = 0

    for item in news[:5]:

        title = item["title"]

        result = analyze_headline_sentiment(
            title
        )

        sentiment = result["sentiment"]

        emoji = "🟡"

        # =====================================
        # POSITIVE
        # =====================================

        if sentiment == "POSITIVE":

            emoji = "🟢"
            bullish += 1

        # =====================================
        # NEGATIVE
        # =====================================

        elif sentiment == "NEGATIVE":

            emoji = "🔴"
            bearish += 1

        # =====================================
        # NEUTRAL
        # =====================================

        else:

            neutral += 1

        report.append(
            f"{emoji} {title}\n"
            f"Confidence: {result['confidence']}\n"
            f"Reason: {result['reason']}\n"
        )

    # =========================================
    # OVERALL MARKET SENTIMENT
    # =========================================

    if bullish > bearish:

        overall = "BULLISH"

    elif bearish > bullish:

        overall = "BEARISH"

    else:

        overall = "MIXED"

    return {
        "overall": overall,
        "items": report
    }

# =========================================
# MARKET MOVERS REPORT
# =========================================

def generate_market_report():

    symbols = [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT"
    ]

    report = []

    for symbol in symbols:

        data = get_crypto_price(symbol)

        price = round(data["price"], 2)

        change = round(data["change"], 2)

        emoji = "🟢"

        if change < 0:

            emoji = "🔴"

        report.append(
            f"{emoji} {symbol} | "
            f"${price} | "
            f"{change}%"
        )

    return report