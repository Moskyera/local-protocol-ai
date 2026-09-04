"""
Debugging Expert Skill v3 for OpenHands
Εντοπίζει, αναλύει, προτείνει και δίνει fixes για errors με υψηλή ακρίβεια
"""

from logger import log

try:
    from llm_client import is_usable
except Exception:  # pragma: no cover
    def is_usable(t):
        t = (t or '').strip()
        return bool(t) and not t.startswith('(')
import traceback
import re

from openhands_skills.expert_base import ExpertSkill

class DebuggingExpert(ExpertSkill):
    #: Symptom -> likely cause for this stack specifically. This table, and the
    #: fix list below it, sat AFTER a `return` statement and had never once
    #: executed.
    COMMON_CAUSES = {
        "timeout": "LLM (llama.cpp) too slow, not loaded, or all slots busy",
        "404": "Primary LLM (http://localhost:8080/v1) not reachable / wrong model alias",
        "connectionerror": "LLM backend or an external API not reachable",
        "importerror": "Missing import or circular import",
        "modulenotfounderror": "Package not installed in C:/AI/ai-env",
        "keyerror": "Missing key in config or .env",
        "nameerror": "A name that does not exist — often inside a try/except that hides it",
        "429": "Rate limit reached (Finnhub, Tavily or another API)",
        "unicodedecodeerror": "A file read as utf-8 that is not utf-8 — try utf-8-sig",
        "revert": "Contract reverted — check require/assert and the caller's allowance",
        "reentrancy": "State written after an external call; use checks-effects-interactions",
        "out of gas": "Unbounded loop or an external call in a loop",
        "oracle": "Single price source; use TWAP or several sources",
    }

    FIX_STEPS = (
        "1. Confirm the model is up:  curl http://localhost:8080/v1/models\n"
        "2. Check .env for LLM_MODEL, OPENAI_BASE_URL\n"
        "3. For slot exhaustion, check /props total_slots against MOSKY_MAP_WORKERS\n"
        "4. Rebuild the runtime if MCP skills changed:\n"
        "   docker build -t my-openhands-runtime -f runtime/Dockerfile ."
    )

    def debug_error(self, error_message: str, file_path: str = None,
                    code_snippet: str = None, stack_trace: str = None) -> str:
        """Diagnose an error, using everything that was passed in.

        THIS METHOD RETURNED FROM ITS OWN MIDDLE. A `return` sat immediately
        after three `if` statements that only matched "revert", "reentrancy",
        "gas" and "oracle" — so for any ordinary Python error the diagnosis
        string was empty and the caller received exactly:

            "Debug analysis complete. \nSmart Diagnosis:\n Suggested next: Run
             full audit with solidity_expert."

        100 characters announcing a completed analysis that contained nothing,
        and recommending a Solidity audit for a UnicodeDecodeError. Everything
        below that return — the cause table, the concrete fix steps — was dead
        code and had never run. Measured identical for two unrelated errors.
        """
        log.error(f"Debugging: {error_message}")
        msg = (error_message or "").strip()
        if not msg:
            return "(no error message was passed, so nothing was diagnosed)"

        low = msg.lower() + " " + (stack_trace or "").lower()
        matched = [f"- {kw}: {cause}"
                   for kw, cause in self.COMMON_CAUSES.items() if kw in low]

        # The real diagnosis, from the actual error, snippet and traceback.
        answer = self.consult(
            "Diagnose this error. Say what went wrong, at which line if you can "
            "tell, and the smallest change that fixes it. If the message alone is "
            "not enough, say exactly what you would need to see. Do not suggest a "
            "Solidity or contract audit unless this error is from contract code.\n\n"
            f"Error: {msg}\n"
            + (f"File: {file_path}\n" if file_path else "")
            + (f"\nCode:\n{code_snippet[:3000]}\n" if code_snippet else "")
            + (f"\nTraceback:\n{stack_trace[:3000]}\n" if stack_trace else ""),
            max_tokens=1200,
        )

        parts = [f"Error: {msg}"]
        if file_path:
            parts.append(f"File: {file_path}")
        if matched:
            parts.append("Known causes matching this message:\n" + "\n".join(matched))
        if is_usable(answer):
            parts.append("Diagnosis:\n" + answer.strip())
        else:
            parts.append("Diagnosis: NOT AVAILABLE — the model did not answer. "
                         "Nothing above this line is a diagnosis of your error.")
        parts.append("Checks for this stack:\n" + self.FIX_STEPS)
        return "\n\n".join(parts)

    def auto_suggest_fix(self, error_type: str):
        """Αυτόματη πρόταση fix"""
        log.info(f"Auto-suggesting fix for {error_type}")
        print(f"Auto-fix suggestion for {error_type} applied")
        return f"Auto-fix suggestion for {error_type} completed"

# Register skill
debug_expert = DebuggingExpert()