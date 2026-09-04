from market_data_service import get_chart_data
from config import config

# =========================================
# SMART MONEY ANALYSIS
# =========================================

def analyze_smart_money(symbol=config.DEFAULT_SYMBOL):
    df = get_chart_data(symbol, timeframe="1h", limit=120)

    avg_volume = df["volume"].tail(72).mean()
    current_volume = float(df["volume"].iloc[-1])
    current_price = float(df["close"].iloc[-1])
    sma20 = float(df["SMA20"].iloc[-1])
    sma50 = float(df["close"].rolling(50).mean().iloc[-1])

    bullish_structure = (current_price > sma20 and sma20 > sma50)
    bearish_structure = (current_price < sma20 and sma20 < sma50)

    state = "NEUTRAL"
    insight = "No strong institutional activity detected."

    if (current_volume > avg_volume * 1.5 and current_price > sma20 and not bullish_structure):
        state = "STEALTH ACCUMULATION"
        insight = "Smart money appears to be absorbing supply."
    elif (bullish_structure and current_volume > avg_volume):
        state = "BULLISH INSTITUTIONAL FLOW"
        insight = "Institutional participation supporting bullish trend."
    elif (current_price > sma20 and current_volume < avg_volume * 0.7):
        state = "WEAK RALLY"
        insight = "Current rally lacks strong institutional support."
    elif (bearish_structure and current_volume > avg_volume * 1.5):
        state = "DISTRIBUTION"
        insight = "Possible institutional distribution behavior detected."
    elif (current_volume > avg_volume * 2 and abs(current_price - sma20) / sma20 > 0.08):
        state = "EXHAUSTION MOVE"
        insight = "Market may be entering an exhaustion phase."

    return {
        "state": state,
        "insight": insight,
        "volume": round(current_volume, 2),
        "avg_volume": round(avg_volume, 2),
        "price": round(current_price, 2)
    }