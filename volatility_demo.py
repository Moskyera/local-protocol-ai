from volatility_engine import (
    analyze_volatility
)

btc = analyze_volatility(
    "BTC/USDT"
)

eth = analyze_volatility(
    "ETH/USDT"
)

print("\n===================================")
print("       VOLATILITY ENGINE")
print("===================================\n")

# =====================================
# BTC
# =====================================

print("BTC VOLATILITY")
print("-----------------------------------")

print(
    f"Price Change : "
    f"{btc['change_percent']}%"
)

print(
    f"RSI          : "
    f"{btc['rsi']}"
)

print(
    f"MACD Delta   : "
    f"{btc['macd_delta']}"
)

print("\nAlerts:")

for alert in btc["alerts"]:

    print(f"- {alert}")

print("\n-----------------------------------\n")

# =====================================
# ETH
# =====================================

print("ETH VOLATILITY")
print("-----------------------------------")

print(
    f"Price Change : "
    f"{eth['change_percent']}%"
)

print(
    f"RSI          : "
    f"{eth['rsi']}"
)

print(
    f"MACD Delta   : "
    f"{eth['macd_delta']}"
)

print("\nAlerts:")

for alert in eth["alerts"]:

    print(f"- {alert}")

print("\n===================================\n")