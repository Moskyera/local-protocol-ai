from report_engine import (
    generate_news_report,
    generate_market_report
)

from llm_agent import generate_market_report as ai_report

# =========================================
# FINAL AI REPORT
# =========================================

def generate_final_market_report():

    # =====================================
    # NEWS
    # =====================================

    news = generate_news_report()

    # =====================================
    # MARKET
    # =====================================

    market = generate_market_report()

    # =====================================
    # BUILD AI CONTEXT
    # =====================================

    combined_context = f"""
NEWS REPORT:

{news['items']}

Overall News Sentiment:
{news['overall']}

MARKET REPORT:

{market}

Analyze:
- overall market regime
- crypto strength/weakness
- stock market sentiment
- risk-on / risk-off conditions
- volatility
- institutional sentiment

Return:
- Final Market Opinion
- Risks
- Opportunities
- Short Summary
"""

    # =====================================
    # AI REASONING
    # =====================================

    final_ai = ai_report(
        combined_context
    )

    return {
        "news": news,
        "market": market,
        "final_ai": final_ai
    }