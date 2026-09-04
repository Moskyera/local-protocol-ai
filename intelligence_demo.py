from market_intelligence import (
    generate_final_market_report
)

report = generate_final_market_report()

# =========================================
# NEWS REPORT
# =========================================

print("\n===================================")
print("      NEWS SENTIMENT REPORT")
print("===================================\n")

for item in report["news"]["items"]:

    print(item)

print(
    f"\nOverall News Sentiment: "
    f"{report['news']['overall']}"
)

# =========================================
# MARKET REPORT
# =========================================

print("\n===================================")
print("      MARKET MOVERS REPORT")
print("===================================\n")

for item in report["market"]:

    print(item)

# =========================================
# FINAL AI REPORT
# =========================================

print("\n===================================")
print("      FINAL AI MARKET OPINION")
print("===================================\n")

print(report["final_ai"])

print("\n===================================\n")