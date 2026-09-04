from llm_agent import generate_market_report
from config import config
from logger import log
import os

def generate_ai_advisor(master_report: str, snapshot: str = "", probability: int = 0):
    log.info("Generating AI Advisor (Reasoning + Portfolio)")

    context = f"""
Master Report:
{master_report}

Market Snapshot:
{snapshot or "No snapshot available"}

AI Probability Score: {probability}%

Task:
Write a short but valuable AI Advisor section (5-8 sentences) with two parts:

1. **Advanced Reasoning**: Explain why the system gives the current signal (STRONG BUY, BUY, WATCH, etc.). Mention main technical and macroeconomic reasons.

2. **Portfolio Recommendation**: Give practical distribution proposals (BTC allocation %, Cash allocation %, risk level). Explain why this is the ideal strategy right now.

Use natural, professional language.
"""

    # NO HARDCODED MARKET VIEW. This used to return, on any exception:
    #   "Market shows strong technical signals with bullish momentum. RSI in
    #    healthy zone, MACD above signal line. Recommended allocation:
    #    60% BTC, 40% Cash. Risk level: Moderate."
    # A specific allocation, with a direction, that nothing computed — published
    # in the daily briefing under "iNFO DUST ADVISOR" and indistinguishable from
    # a real reading. Inventing a bullish call when the model is down is the
    # most expensive lie this system could tell.
    try:
        from llm_client import is_llm_error
    except Exception:
        def is_llm_error(t):
            return not (t or "").strip() or (t or "").strip().startswith("(")

    try:
        advisor_text = generate_market_report(context)
    except Exception as e:
        log.error(f"AI Advisor error: {e}")
        return f"(LLM error - AI Advisor could not run: {type(e).__name__}: {str(e)[:120]})"

    # generate_market_report RETURNS an error string instead of raising, so the
    # except above almost never fires and the sentinel used to flow onward as
    # analysis.
    if is_llm_error(advisor_text):
        log.error("AI Advisor: model returned an error sentinel")
        return "(LLM error - AI Advisor: the model did not answer)"

    log.success("AI Advisor generated successfully")
    return advisor_text.strip()
