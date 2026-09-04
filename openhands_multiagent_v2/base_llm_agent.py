"""
Base LLM Agent - Πραγματική βάση για ΟΛΟΥΣ τους development agents.

Πριν από αυτό, οι coder/tester/reviewer agents απλά έκαναν print() και
επέστρεφαν hardcoded strings ("All tests passed with high confidence") χωρίς
να καλούν ποτέ το μοντέλο. Αυτή η κλάση διορθώνει τη ρίζα του προβλήματος:
κάθε agent τώρα στέλνει πραγματικό prompt στο τοπικό llama.cpp backend
(gemma για market / qwen3-coder για coding) και επιστρέφει πραγματικό output.

Χρήση:
    class CoderAgent(BaseLLMAgent):
        ROLE = "coder"
        SYSTEM_PROMPT = "You are a world-class software engineer..."

        def write_or_refactor(self, task: str) -> str:
            return self.complete(task)
"""

from __future__ import annotations

from typing import Optional
import re

try:
    from logger import log
except Exception:  # pragma: no cover - logger optional in isolated tests
    import logging
    log = logging.getLogger("base_llm_agent")


try:
    from openhands_skills.agent_metrics import track as _track
except Exception:  # pragma: no cover - measurement must never break an agent
    from contextlib import contextmanager

    @contextmanager
    def _track(agent, **fields):
        class _Null:
            def note(self, **kw):
                pass
        yield _Null()

# Central config (model aliases, base url). Optional so the class still imports
# in stripped-down environments.
try:
    from config import config
    _CODING_MODEL = getattr(config, "CODING_MODEL", None)
except Exception:
    config = None
    _CODING_MODEL = None


class BaseLLMAgent:
    """Common, real LLM-backed behaviour shared by every development agent."""

    #: Short role label used in logs / prompts.
    ROLE: str = "agent"

    #: System prompt that defines the persona. Subclasses override.
    SYSTEM_PROMPT: str = "You are a helpful, precise senior software engineer."

    #: If True, requests are routed with the coding-model alias so the caller
    #: can (optionally) target a code-specialised backend.
    USE_CODING_MODEL: bool = True

    #: Sensible defaults; subclasses / call sites can override per call.
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_MAX_TOKENS: int = 8192

    def __init__(self, model: Optional[str] = None):
        # Explicit override wins; else coding alias when requested; else backend default.
        self._model = model or (_CODING_MODEL if self.USE_CODING_MODEL else None)

    # ------------------------------------------------------------------ #
    # Core                                                               #
    # ------------------------------------------------------------------ #
    def complete(
        self,
        user_prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Send a real request to the local LLM and return the answer.

        Never raises to the caller: on backend failure it returns a clear
        error string so orchestration keeps flowing instead of crashing.
        """
        # Import here so a missing backend never breaks module import.
        try:
            from llm_client import chat
        except Exception as e:  # backend not wired in this environment
            log.error(f"[{self.ROLE}] llm_client unavailable: {e}")
            return f"(LLM backend unavailable for {self.ROLE} agent: {e})"

        sys_p = system_prompt if system_prompt is not None else self.SYSTEM_PROMPT
        log.info(f"[{self.ROLE}] LLM call ({len(user_prompt)} chars in)")

        # agent_metrics was written to answer "which agent runs, how often, how
        # slowly, and does it succeed" — and was wired into ONE module out of
        # eighty-five, so it recorded nothing worth reading. Every v2 agent's
        # model call passes through here. This is the place worth measuring.
        with _track("agent:" + self.ROLE, prompt_chars=len(user_prompt)) as _run:
            try:
                out = chat(
                    user_prompt,
                    model=self._model,
                    temperature=self.DEFAULT_TEMPERATURE if temperature is None else temperature,
                    max_tokens=self.DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens,
                    system_prompt=sys_p,
                )
                text = (out or "").strip()
                # ok=False for an empty answer: the call did not raise, but it
                # produced nothing, and a metrics file that counts that as a
                # success is the same lie in a smaller place.
                _run.note(reply_chars=len(text), ok=bool(text))
                return text
            except Exception as e:
                log.error(f"[{self.ROLE}] LLM call failed: {e}")
                _run.note(ok=False, failure=f"{type(e).__name__}")
                return f"({self.ROLE} agent LLM error: {e})"

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def section(self, title: str, text: str) -> str:
        """A markdown section whose HEADER matches what is under it.

        Agent output goes straight under a confident heading:

            ### 🔒 Deep security audit (LLM)
            (security agent LLM error: backend down)

        The sentinel is visible, but the structure asserts the opposite of what
        happened, and a reader scanning headings in a security report concludes
        the audit ran. The heading is the part people trust.

        The text is always kept — a reader should see exactly what came back.
        Only the heading changes, to stop claiming something that did not occur.
        """
        try:
            from llm_client import is_llm_error, is_llm_draft
        except Exception:  # pragma: no cover
            def is_llm_error(t):
                return not (t or "").strip() or str(t).strip().startswith("(")

            def is_llm_draft(t):
                return False

        body = text if text is not None else ""
        if is_llm_error(body):
            return (f"### ⚠️ {title} — ΔΕΝ ΕΓΙΝΕ\n"
                    f"Το μοντέλο δεν απάντησε. Αυτό ΔΕΝ είναι αποτέλεσμα:\n\n{body}")
        if is_llm_draft(body):
            return (f"### ⚠️ {title} — ΜΟΝΟ ΠΡΟΧΕΙΡΟ\n"
                    f"Το μοντέλο σκέφτηκε αλλά δεν έγραψε απάντηση. Ακολουθεί "
                    f"το πρόχειρό του, αδιόρθωτο:\n\n{body}")
        return f"### {title}\n{body}"

    @staticmethod
    def extract_code(text: str) -> str:
        """Return the first fenced code block if present, else the raw text."""
        m = re.search(r"```(?:[a-zA-Z0-9_+-]*)\n(.*?)```", text, re.DOTALL)
        return m.group(1).strip() if m else text.strip()

    # A single unambiguous word is enough on its own.
    _SOLIDITY_STRONG = re.compile(
        r"\b(solidity|pragma\s+solidity|smart\s+contracts?|pulsechain|"
        r"erc[- ]?(20|165|721|1155|4626)s?|openzeppelin|"
        r"msg\.sender|\w+\.sol)\b", re.I)

    # These are only suggestive; on their own an "erc" or a "defi" proves nothing.
    _SOLIDITY_WEAK = re.compile(
        r"\b(erc|evm|hvm|defi|pls|plsx|token|tokens|wallet|onchain|on-chain)\b", re.I)

    @staticmethod
    def looks_like_solidity(text: str) -> bool:
        """Was `any(kw in t for kw in (... "erc", "defi", "evm" ...))` — a plain
        substring test. "erc" is inside e-comm*erc*e, p*erc*entage, m*erc*hant,
        s*e*a*rc*h; "defi" is inside *defi*ne and *defi*nition. Measured: four of
        five ordinary programming tasks were classified as Solidity, and each one
        got a canned ERC-20 contract back instead of the work that was asked for.

        A strong marker stands alone; a weak one needs a second weak marker.
        """
        t = text or ""
        if BaseLLMAgent._SOLIDITY_STRONG.search(t):
            return True
        return len(set(m.lower() for m in BaseLLMAgent._SOLIDITY_WEAK.findall(t))) >= 2

    @staticmethod
    def target_chain(text: str) -> str:
        t = text or ""
        return ("pulsechain"
                if re.search(r"\b(pulsechain|pulse|pls|plsx|hex)\b", t, re.I)
                else "ethereum")
