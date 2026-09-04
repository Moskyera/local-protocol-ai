from regime_engine import (
    analyze_market_regime
)

# =========================================
# ANALYZE
# =========================================

data = analyze_market_regime()

print("\n===================================")
print("      MARKET REGIME ENGINE")
print("===================================\n")

print(
    f"Stocks Regime : "
    f"{data['stock_regime']}"
)

print(
    f"Crypto Regime : "
    f"{data['crypto_regime']}"
)

print(
    f"Overall Market : "
    f"{data['overall']}"
)

print("\n-----------------------------------\n")

print(
    f"Stocks Bullish : "
    f"{data['stock_bullish']}"
)

print(
    f"Stocks Bearish : "
    f"{data['stock_bearish']}"
)

print()

print(
    f"Crypto Bullish : "
    f"{data['crypto_bullish']}"
)

print(
    f"Crypto Bearish : "
    f"{data['crypto_bearish']}"
)

print("\n===================================\n")