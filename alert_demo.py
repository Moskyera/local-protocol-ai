from alert_engine import (
    generate_alerts
)

btc_alerts = generate_alerts(
    "BTC/USDT"
)

eth_alerts = generate_alerts(
    "ETH/USDT"
)

print("\n===================================")
print("         AI ALERT ENGINE")
print("===================================\n")

# =====================================
# BTC ALERTS
# =====================================

print("BTC ALERTS")
print("-----------------------------------")

for alert in btc_alerts:

    print(f"- {alert}")

print("\n-----------------------------------\n")

# =====================================
# ETH ALERTS
# =====================================

print("ETH ALERTS")
print("-----------------------------------")

for alert in eth_alerts:

    print(f"- {alert}")

print("\n===================================\n")