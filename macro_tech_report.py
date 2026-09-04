from news_agent import get_market_news
from llm_agent import generate_market_report
from config import config
from logger import log
import os

def generate_macro_tech_report():
    log.info("Generating Macro & Tech Sentiment Report")

    news = get_market_news("Latest global economy tech AI stock market news") or []

    # With an empty news list the context below still asked for a macro report,
    # and the model duly produced one — sourced from nothing but its own prior,
    # published as today's read on the economy. A sentiment report with no
    # inputs is not a weak signal, it is not a signal.
    titles = [t for t in ((item.get("title") or "").strip() for item in news) if t]
    MIN_ARTICLES = 2
    if len(titles) < MIN_ARTICLES:
        log.error(f"Macro/Tech report: only {len(titles)} article(s) retrieved "
                  f"(need {MIN_ARTICLES}) — refusing to write a macro read with no inputs")
        return (f"(Macro/Tech sentiment was NOT computed: the news feed returned "
                f"{len(titles)} article(s). Δεν γράφτηκε εκτίμηση χωρίς δεδομένα.)")

    context = f"""
Recent News:
{chr(10).join([f"- {t}" for t in titles[:6]])}

Task:
Write a short (4-6 sentences) Macro & Tech Sentiment Report.
Focus on:
- Global economic outlook
- Technology / AI sector trends
- Key risks and opportunities
- Overall market sentiment

Use natural, professional language.
"""

    # Same defect as ai_advisor_engine: this returned a hardcoded POSITIVE macro
    # read ("positive momentum, with AI leading growth ... cautiously optimistic")
    # whenever the model was unreachable. A sentiment call nobody computed.
    try:
        from llm_client import is_llm_error
    except Exception:
        def is_llm_error(t):
            return not (t or "").strip() or (t or "").strip().startswith("(")

    try:
        report = generate_market_report(context)
    except Exception as e:
        log.error(f"Macro report error: {e}")
        return f"(LLM error - Macro/Tech report could not run: {type(e).__name__}: {str(e)[:120]})"

    if is_llm_error(report):
        log.error("Macro/Tech report: model returned an error sentinel")
        return "(LLM error - Macro/Tech report: the model did not answer)"

    log.success("Macro & Tech Report generated")
    return report.strip()
