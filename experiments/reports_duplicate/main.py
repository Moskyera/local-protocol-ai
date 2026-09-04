from news_agent import get_market_news
from market_agent import get_crypto_price
from indicators import get_market_indicators
from ai_analyst import analyze_market
from llm_agent import generate_market_report

print("\n===================================")
print("   AI MARKET INTELLIGENCE SYSTEM")
print("===================================\n")

# =========================================
# LIVE MARKET DATA
# =========================================

market = get_crypto_price("BTC/USDT")

print("=== LIVE MARKET ===\n")

print(f"Symbol : {market['symbol']}")
print(f"Price  : ${market['price']}")
print(f"24h %  : {market['change']}")
print(f"Volume : {market['volume']}")

# =========================================
# TECHNICAL ANALYSIS
# =========================================

ta = get_market_indicators("BTC/USDT")

print("\n=== TECHNICAL ANALYSIS ===\n")

print(f"RSI          : {ta['rsi']}")
print(f"MACD         : {ta['macd']}")
print(f"MACD Signal  : {ta['macd_signal']}")
print(f"SMA20        : {ta['sma20']}")

# =========================================
# AI ANALYSIS
# =========================================

analysis = analyze_market(
    market,
    ta
)

print("\n=== AI MARKET ANALYSIS ===\n")

print(
    f"Market Sentiment: "
    f"{analysis['sentiment']}\n"
)

for item in analysis["analysis"]:

    print(f"- {item}")

# =========================================
# NEWS
# =========================================

print("\n=== MARKET NEWS ===\n")

news = get_market_news(
    "Latest Bitcoin NVIDIA AI market news"
)

for i, item in enumerate(news[:3], 1):

    print(f"\n[{i}] {item['title']}")
    print(item["url"])

# =========================================
# AI FULL MARKET REPORT
# =========================================

print("\n=== GENERATING AI REPORT ===\n")

prompt = f"""
You are an elite AI financial analyst.

Analyze the following market conditions.

BTC Price: {market['price']}
24h Change: {market['change']}

RSI: {ta['rsi']}
MACD: {ta['macd']}
MACD Signal: {ta['macd_signal']}
SMA20: {ta['sma20']}

Sentiment: {analysis['sentiment']}

News Headlines:
{[item['title'] for item in news[:3]]}

Write:
- short market summary
- bullish/bearish interpretation
- risks
- possible scenarios
"""

report = generate_market_report(prompt)

print("\n=== AI FULL MARKET REPORT ===\n")

print(report)

print("\n===================================")
print("      ANALYSIS COMPLETE")
print("===================================\n")