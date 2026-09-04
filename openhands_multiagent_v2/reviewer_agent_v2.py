"""
Reviewer Agent v2 - Πραγματικός agent code review.

Κάνει πραγματικό deep review μέσω του μοντέλου (correctness, design, edge
cases, performance, maintainability) και για Solidity προσθέτει τον
εξειδικευμένο audit. Δεν είναι πλέον κενό template.
"""

from logger import log
from .base_llm_agent import BaseLLMAgent

try:
    from openhands_skills.solidity_expert import solidity_expert
except Exception:  # pragma: no cover
    solidity_expert = None

try:
    from .code_intelligence import code_intelligence
except Exception:  # pragma: no cover
    code_intelligence = None


class ReviewerAgent(BaseLLMAgent):
    ROLE = "reviewer"
    # Slightly higher temperature than coder: we want the model to surface
    # non-obvious concerns, not just restate the code.
    DEFAULT_TEMPERATURE = 0.3
    SYSTEM_PROMPT = (
        "You are a demanding staff-level code reviewer. Review the given code or "
        "diff and report concrete, actionable findings grouped by severity "
        "(Blocker / Major / Minor / Nit). For each finding give: file/line or "
        "symbol, what is wrong, why it matters, and a suggested fix. Check "
        "correctness, edge cases, error handling, concurrency, resource leaks, "
        "API misuse, readability and test coverage. If the code is solid, say so "
        "plainly and note only genuine improvements — do not invent problems."
    )

    def review(self, code_or_pr: str) -> str:
        log.info("Reviewer Agent v2: Performing deep code review")

        # Ground the review in deterministic analyzers (ruff/pyflakes/mypy).
        tool_report = ""
        if code_intelligence is not None:
            try:
                tool_report = code_intelligence.analyze_code(code_or_pr).to_report()
            except Exception as e:
                tool_report = f"(code intelligence error: {e})"

        review = self.complete(
            "Review the following code / pull request. A deterministic analyzer "
            "toolchain (ruff, pyflakes, mypy) reported the findings below — treat "
            "them as ground truth, explain the important ones in plain terms, and "
            "add the higher-level design/correctness issues the tools cannot "
            f"see.\n\n### Analyzer findings\n{tool_report or '(analyzers unavailable)'}"
            f"\n\n### Code\n{code_or_pr}"
        )

        # Layer the specialised Solidity/PulseChain audit on top when relevant.
        if solidity_expert is not None and any(
            kw in code_or_pr.lower()
            for kw in ("solidity", "contract", "pragma solidity", "evm", "pulsechain")
        ):
            log.info("Reviewer Agent v2: Adding Solidity/PulseChain audit")
            audit = solidity_expert.audit_solidity(code_or_pr)
            return f"{review}\n\n---\n### 🔷 Solidity / PulseChain audit\n{audit}"

        return review


# Register
reviewer = ReviewerAgent()
