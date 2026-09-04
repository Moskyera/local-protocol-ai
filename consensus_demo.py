from consensus_engine import (
    generate_consensus
)

btc = generate_consensus(
    "BTC/USDT"
)

print("\n===================================")
print("        AI CONSENSUS ENGINE")
print("===================================\n")

print(
    f"Consensus  : {btc['consensus']}"
)

print(
    f"Confidence : {btc['confidence']}%"
)

print(
    f"Bullish TF : {btc['bullish']}"
)

print(
    f"Bearish TF : {btc['bearish']}"
)

print(
    f"Neutral TF : {btc['neutral']}"
)

print("\nExplanation:")
print(
    btc["explanation"]
)

print("\n===================================\n")