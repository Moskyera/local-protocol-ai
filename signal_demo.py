from signal_engine import (
    generate_signal
)

btc = generate_signal(
    "BTC/USDT"
)

eth = generate_signal(
    "ETH/USDT"
)

print("\n===================================")
print("     ADVANCED AI SIGNAL ENGINE")
print("===================================\n")

# =====================================
# BTC
# =====================================

print("BTC SIGNAL")
print("-----------------------------------")

print(
    f"Signal       : {btc['signal']}"
)

print(
    f"Confidence   : {btc['confidence']}%"
)

print(
    f"Market State : {btc['market_state']}"
)

print(
    f"Price        : ${btc['price']}"
)

print(
    f"RSI          : {btc['rsi']}"
)

print(
    f"MACD         : {btc['macd']}"
)

print(
    f"Reason       : {btc['reason']}"
)

print("\n-----------------------------------\n")

# =====================================
# ETH
# =====================================

print("ETH SIGNAL")
print("-----------------------------------")

print(
    f"Signal       : {eth['signal']}"
)

print(
    f"Confidence   : {eth['confidence']}%"
)

print(
    f"Market State : {eth['market_state']}"
)

print(
    f"Price        : ${eth['price']}"
)

print(
    f"RSI          : {eth['rsi']}"
)

print(
    f"MACD         : {eth['macd']}"
)

print(
    f"Reason       : {eth['reason']}"
)

print("\n===================================\n")