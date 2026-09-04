from market_data_service import get_chart_data
from config import config

# =========================================
# WHALE ANALYSIS
# =========================================

def detect_whale_activity(symbol=config.DEFAULT_SYMBOL):
    df = get_chart_data(symbol, timeframe="1h", limit=100)

    avg_volume = df["volume"].tail(48).mean()
    current_volume = float(df["volume"].iloc[-1])
    current_price = float(df["close"].iloc[-1])
    previous_price = float(df["close"].iloc[-2])
    price_change = ((current_price - previous_price) / previous_price) * 100

    whale_state = "NORMAL"
    whale_message = "No unusual whale activity detected."

    if (current_volume > avg_volume * 2 and price_change > 1):
        whale_state = "WHALE ACCUMULATION"
        whale_message = "Large volume spike with bullish price expansion."
    elif (current_volume > avg_volume * 2 and price_change < -2):
        whale_state = "LIQUIDATION EVENT"
        whale_message = "Heavy sell pressure and possible long liquidations."
    elif (current_volume > avg_volume * 1.5 and abs(price_change) > 3):
        whale_state = "BREAKOUT PRESSURE"
        whale_message = "Strong directional move with elevated participation."

    return {
        "state": whale_state,
        "message": whale_message,
        "volume": round(current_volume, 2),
        "avg_volume": round(avg_volume, 2),
        "price_change": round(price_change, 2)
    }