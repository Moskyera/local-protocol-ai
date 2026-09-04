"""
ExpertSkill - κοινή LLM-backed βάση για τα persona skills.

Πολλά skills ήταν "θέατρο": επέστρεφαν στατικά templates/prints χωρίς να
σκέφτονται το πραγματικό task. Αυτή η βάση δίνει σε κάθε expert ένα πραγματικό
`consult()` που καλεί το τοπικό μοντέλο με το domain persona του, ώστε το output
να είναι task-specific — όχι boilerplate.

Τα skills κρατούν τα υπάρχοντα method names / return shapes· απλά προσθέτουν
πραγματικό περιεχόμενο (π.χ. ένα "expert_analysis" key) αντί μόνο για στατικά
checklists. Έτσι δεν σπάει κανένας caller.
"""

from __future__ import annotations

from typing import Optional

try:
    from logger import log
except Exception:  # pragma: no cover
    import logging
    log = logging.getLogger("expert_base")

try:
    from config import config
    _CODING_MODEL = getattr(config, "CODING_MODEL", None)
except Exception:
    _CODING_MODEL = None

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

try:
    from llm_client import is_usable as _usable
except Exception:  # pragma: no cover - llm_client is always present in-tree
    def _usable(text):
        t = (text or "").strip()
        return bool(t) and not t.startswith("(")


class ExpertSkill:
    """Real LLM-backed persona. Subclasses set ROLE + EXPERTISE."""

    ROLE: str = "expert"

    def __init_subclass__(cls, **kw):
        """Give every subclass a distinct ROLE unless it sets one.

        Twenty-six subclasses never set ROLE, so they all identified as
        "expert": in the log line, in the failure sentinel
        ("(expert 'expert' error: ...)"), and — since the metrics layer was
        wired in — in every metrics row, all twenty-six writing to the same
        name. A measurement that cannot tell SEOExpert from HacashL3Expert
        cannot answer the one question it exists for.

        Derived from the class name, so it stays right when a class is renamed:
        SEOExpert -> seo_expert, HacashL3Expert -> hacash_l3_expert.
        """
        super().__init_subclass__(**kw)
        if "ROLE" not in cls.__dict__:
            import re as _re
            name = _re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", cls.__name__)
            name = _re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
            cls.ROLE = name.lower()
    #: One-paragraph description of the persona / domain mastery.
    EXPERTISE: str = "a senior software professional"
    #: Extra hard rules appended to the system prompt.
    RULES: str = (
        "Be concrete and specific to THIS task. No filler, no marketing fluff. "
        "Give actionable output the user can apply directly. State assumptions "
        "explicitly. If something is genuinely fine, say so — do not invent work."
    )
    USE_CODING_MODEL: bool = True
    DEFAULT_TEMPERATURE: float = 0.3
    DEFAULT_MAX_TOKENS: int = 6000

    def _system_prompt(self, extra: Optional[str] = None) -> str:
        base = f"You are {self.EXPERTISE}. {self.RULES}"
        return f"{base}\n\n{extra}" if extra else base

    def grammar(self) -> Optional[str]:
        """GBNF constraining what this expert may emit. None for most.

        Overridden by skills whose output alphabet is known — see DocAnalyst,
        where it is the only thing that stops the model emitting characters from
        unrelated scripts inside Greek words.
        """
        return None

    def mark_analysis(self, result: dict, key: str = "expert_analysis") -> dict:
        """Flag whether the model actually answered, in the result itself.

        Twenty-one skills do

            result["expert_analysis"] = self.consult(...)

        and consult() returns "(expert 'role' error: ...)" on backend failure.
        The sentinel went straight into the result dict, in a field named
        expert_analysis, next to a printed banner saying the work was
        delivered. A caller — or a person — reading that dict sees a populated
        analysis field and has to recognise the sentinel by eye to know the
        model never answered.

        The text is kept, because a reader should see what came back. What is
        added is a machine-readable flag and, when it failed, a warning that
        says so in words.
        """
        text = result.get(key, "")
        ok = _usable(text)
        result[f"{key}_is_real"] = ok
        if not ok:
            result["analysis_warning"] = (
                f"'{key}' is NOT analysis — the model did not answer. "
                f"Everything else in this result is static reference material."
            )
            log.warning(f"[{self.ROLE}] {key} came back as a failure sentinel")
        return result

    def analyse(self, what: str, inputs: dict, reference: dict = None,
                extra_system: str = None, max_tokens: int = None) -> dict:
        """A real answer about `inputs`, with any fixed material kept separate.

        Ten methods across this stack were measured returning BYTE-IDENTICAL
        output for two unrelated requests — a hardcoded dict built once and
        handed back whatever you asked. The worst of them,
        ProgrammerExpert.god_tier_code_review, awarded "9/10" and listed
        specific bugs about Hacash mining nonces and L2 channel races for any
        code at all, including a three-line divide-by-zero. It did not merely
        ignore the input; it invented findings about code it never read.

        Static reference material is genuinely useful and is kept — but it is
        returned under *_reference keys, behind an explicit note saying it does
        not depend on the input, so it can never again be mistaken for
        analysis. The analysis itself comes from the model, per call.

        Returns {"answer", "answered", "inputs", ...*_reference} and, when the
        model did not answer, a "warning" saying so instead of letting the
        reference material stand in for a result.
        """
        parts = []
        for k, v in (inputs or {}).items():
            if v is None:
                continue
            text = v if isinstance(v, str) else str(v)
            if not text.strip():
                continue
            parts.append(f"{k}:\n{text}")
        body = "\n\n".join(parts) if parts else "(no input was supplied)"

        answer = self.consult(f"{what}\n\n{body}", extra_system=extra_system,
                              max_tokens=max_tokens)
        ok = _usable(answer)

        out = {
            "answer": answer,
            "answered": ok,
            "inputs": {k: (str(v)[:600] if v is not None else None)
                       for k, v in (inputs or {}).items()},
        }
        if not ok:
            out["warning"] = (
                "The model did not return a usable answer, so this output "
                "contains NO analysis of your input. Anything below is fixed "
                "reference material."
            )
        if reference:
            out["reference_only"] = (
                "Every *_reference key below is fixed material. It does not "
                "depend on your input and is not a finding about it."
            )
            for k, v in reference.items():
                out[f"{k}_reference"] = v
        return out

    def consult(
        self,
        task: str,
        context: Optional[dict] = None,
        *,
        extra_system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Real, task-specific expert answer from the local model.

        Never raises: returns a clear error string on backend failure so the
        surrounding skill (and its static reference data) keeps working.
        """
        try:
            from llm_client import chat
        except Exception as e:
            log.error(f"[{self.ROLE}] llm_client unavailable: {e}")
            return f"(expert '{self.ROLE}' unavailable: LLM backend not reachable)"

        ctx = ""
        if context:
            try:
                import json
                ctx = "\n\nContext:\n" + json.dumps(
                    {k: str(v)[:1200] for k, v in context.items()},
                    ensure_ascii=False, indent=2,
                )
            except Exception:
                ctx = f"\n\nContext: {str(context)[:1500]}"

        model = _CODING_MODEL if self.USE_CODING_MODEL else None
        with _track("skill:" + self.ROLE, task_chars=len(task or "")) as _run:
            try:
                out = chat(
                    f"Task:\n{task}{ctx}",
                    model=model,
                    temperature=self.DEFAULT_TEMPERATURE if temperature is None else temperature,
                    max_tokens=self.DEFAULT_MAX_TOKENS if max_tokens is None else max_tokens,
                    system_prompt=self._system_prompt(extra_system),
                    grammar=self.grammar(),
                )
                text = (out or "").strip()
                _run.note(reply_chars=len(text), ok=_usable(text))
                return text
            except Exception as e:
                log.error(f"[{self.ROLE}] consult failed: {e}")
                _run.note(ok=False, failure=f"{type(e).__name__}")
                return f"(expert '{self.ROLE}' error: {e})"
