"""
Strategic Oracle Agent v2.2 - Multi-scenario στρατηγικές προβλέψεις.

Πριν: τραβούσε real data (master/snapshot/macro) και μετά τα ΑΓΝΟΟΥΣΕ,
επιστρέφοντας hardcoded template με "..." placeholders.
Τώρα: τροφοδοτεί τα πραγματικά data στο μοντέλο (market model / gemma) και
παράγει αληθινή vision με πιθανότητες + επίπεδα. Fallback στο template αν το
backend είναι κάτω. Persistent memory διατηρείται.
"""

from logger import log
from openhands_skills.tool_integration_hub import tool_hub
from .base_llm_agent import BaseLLMAgent

try:
    from openhands_skills.persistent_memory import persistent_memory
except Exception:  # pragma: no cover
    persistent_memory = None


class StrategicOracle(BaseLLMAgent):
    ROLE = "strategic_oracle"
    USE_CODING_MODEL = False  # market reasoning → use the market model (gemma), not the coder
    DEFAULT_TEMPERATURE = 0.4
    SYSTEM_PROMPT = (
        "You are a disciplined markets strategist. From the provided master "
        "report, snapshot and macro data, produce a multi-scenario outlook: Base "
        "/ Bull / Bear, each with an explicit probability (summing to 100%), the "
        "reasoning grounded in the data, and concrete key price levels. Then give "
        "an actionable recommendation: position sizing stance, risk management, "
        "time horizon, and invalidation level. Ground every claim in the data "
        "given — never invent numbers that are not supported."
    )

    _FALLBACK = (
        "🌌 STRATEGIC ORACLE VISION - {symbol}\n"
        "(LLM unavailable — structural template only)\n"
        "Base 60% / Bull 25% / Bear 15%. Re-run when the LLM backend is up."
    )

    def generate_vision(self, symbol: str = "BTC/USDT") -> str:
        log.info(f"Strategic Oracle activated for {symbol}")

        master = tool_hub.run_master_report(symbol)
        snapshot = tool_hub.run_market_snapshot()
        macro = tool_hub.run_macro_report()

        vision = self.complete(
            f"Symbol: {symbol}\n\n"
            f"### Master report\n{str(master)[:4000]}\n\n"
            f"### Market snapshot\n{str(snapshot)[:2000]}\n\n"
            f"### Macro\n{str(macro)[:2000]}\n\n"
            "Produce the multi-scenario strategic vision now."
        )

        # `vision.startswith("(")` caught the error sentinels and nothing else.
        # A DRAFT is the model's scratchpad, recovered when it spends its whole
        # budget reasoning and never writes an answer — real text that does not
        # start with a parenthesis, so it passed straight through.
        try:
            from llm_client import is_llm_error, is_llm_draft
        except Exception:  # pragma: no cover
            def is_llm_error(t):
                return not (t or "").strip() or (t or "").strip().startswith("(")

            def is_llm_draft(t):
                return False

        failed = is_llm_error(vision)
        drafted = (not failed) and is_llm_draft(vision)

        if failed:
            vision = self._FALLBACK.format(symbol=symbol)
        elif drafted:
            vision = ("⚠️ ΔΕΝ είναι στρατηγικό όραμα — το μοντέλο ξόδεψε όλο το "
                      "budget του σκεπτόμενο και δεν έγραψε απάντηση. Ακολουθεί "
                      "το πρόχειρό του, αδιόρθωτο:\n\n" + vision)

        # ONLY a real answer goes into the vector database. Before this, both
        # the fallback and the scratchpad were written with
        # type="strategic_vision", so every failed run added another canned
        # paragraph to the memory that retrieve_relevant() later surfaces as
        # though it were analysis. A store that cannot refuse poisons itself.
        if persistent_memory is not None and not failed and not drafted:
            try:
                persistent_memory.store(
                    text=vision,
                    metadata={"type": "strategic_vision", "symbol": symbol},
                )
            except Exception as e:
                log.warning(f"Strategic Oracle: memory store failed: {e}")
        elif failed or drafted:
            log.warning(f"Strategic Oracle: not storing this run for {symbol} — "
                        f"{'backend failure' if failed else 'draft only'}")

        return vision


# Register
strategic_oracle = StrategicOracle()
