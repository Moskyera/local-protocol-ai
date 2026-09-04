from llm_agent import generate_market_report
from config import config
from logger import log
import os

def generate_ai_commentary(master_report: str, snapshot: str = "", news_items: list = None):
    log.info("Generating AI Commentary")

    context = f"""
Master BTC Technical Report:
{master_report}

Market Snapshot:
{snapshot or "No snapshot available"}

Recent News:
{chr(10).join([f"- {item.get('title','')}" for item in (news_items or [])[:5]]) if news_items else "No recent news"}

Task:
Γράψε ένα σύντομο (4-7 προτάσεις), φυσικό και επαγγελματικό market commentary.
"""

    try:
        commentary = generate_market_report(context)
        log.success("AI Commentary generated successfully")
        return commentary.strip()
    except Exception as e:
        log.warning(f"Ollama failed, using fallback: {e}")
        return "Η αγορά βρίσκεται σε φάση μετάβασης. Το BTC δίνει ανοδικά σήματα."