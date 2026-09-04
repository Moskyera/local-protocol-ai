from multi_timeframe_engine import (
    analyze_multi_timeframe
)

btc = analyze_multi_timeframe(
    "BTC/USDT"
)

print("\n===================================")
print("     MULTI TIMEFRAME ANALYSIS")
print("===================================\n")

for timeframe, data in btc.items():

    print(f"{timeframe}")
    print("-----------------------------------")

    print(
        f"Signal : {data['signal']}"
    )

    print(
        f"Price  : ${data['price']}"
    )

    print(
        f"RSI    : {data['rsi']}"
    )

    print(
        f"MACD   : {data['macd']}"
    )

    print("\n")