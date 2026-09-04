def analyze_market(data, indicators):

    analysis = []

    rsi = indicators["rsi"]
    macd = indicators["macd"]
    macd_signal = indicators["macd_signal"]
    price = indicators["price"]
    sma20 = indicators["sma20"]

    # =========================================
    # RSI ANALYSIS
    # =========================================

    if rsi > 70:

        analysis.append(
            "RSI indicates overbought conditions."
        )

    elif rsi < 30:

        analysis.append(
            "RSI indicates oversold conditions."
        )

    else:

        analysis.append(
            "RSI remains in neutral territory."
        )

    # =========================================
    # MACD ANALYSIS
    # =========================================

    if macd > macd_signal:

        analysis.append(
            "MACD bullish crossover detected."
        )

    else:

        analysis.append(
            "MACD bearish momentum detected."
        )

    # =========================================
    # TREND ANALYSIS
    # =========================================

    if price > sma20:

        analysis.append(
            "Price trades above SMA20 support."
        )

    else:

        analysis.append(
            "Price trades below SMA20 resistance."
        )

    # =========================================
    # FINAL SENTIMENT
    # =========================================

    bullish = 0
    bearish = 0

    for item in analysis:

        text = item.lower()

        if (
            "bullish" in text
            or "above" in text
            or "oversold" in text
        ):
            bullish += 1

        if (
            "bearish" in text
            or "below" in text
            or "overbought" in text
        ):
            bearish += 1

    if bullish > bearish:

        sentiment = "BULLISH"

    elif bearish > bullish:

        sentiment = "BEARISH"

    else:

        sentiment = "NEUTRAL"

    return {
        "sentiment": sentiment,
        "analysis": analysis
    }