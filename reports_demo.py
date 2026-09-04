from report_engine import (
    generate_news_report,
    generate_market_report
)

# =========================================
# NEWS REPORT
# =========================================

news = generate_news_report()

print("\n===================================")
print("      NEWS SENTIMENT REPORT")
print("===================================\n")

for item in news["items"]:

    print(item)

print(
    f"\nOverall Market Sentiment: "
    f"{news['overall']}"
)

# =========================================
# MARKET REPORT
# =========================================

market = generate_market_report()

print("\n===================================")
print("      MARKET MOVERS REPORT")
print("===================================\n")

for item in market:

    print(item)

print("\n===================================\n")