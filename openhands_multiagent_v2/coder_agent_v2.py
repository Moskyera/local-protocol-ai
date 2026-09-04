"""
Coder Agent v2 - Πραγματικός agent παραγωγής/refactor κώδικα.

Πλέον καλεί το τοπικό μοντέλο (qwen3-coder / gemma μέσω llm_client) αντί να
επιστρέφει hardcoded string. Για Solidity/EVM/PulseChain tasks συνεχίζει να
χρησιμοποιεί τον εξειδικευμένο solidity_expert.
"""

from logger import log
from .base_llm_agent import BaseLLMAgent

try:
    from openhands_skills.solidity_expert import solidity_expert
except Exception:  # pragma: no cover
    solidity_expert = None


class CoderAgent(BaseLLMAgent):
    ROLE = "coder"
    SYSTEM_PROMPT = (
        "You are a world-class senior software engineer. Write clean, modular, "
        "production-grade code. Always include: type hints, docstrings, precise "
        "error handling, structured logging, and inline comments only where they "
        "add value. Prefer standard-library and well-established dependencies. "
        "Return the complete code inside a single fenced code block, then a short "
        "bullet list of design decisions and any assumptions. Never invent APIs — "
        "if something is ambiguous, state the assumption explicitly."
    )

    def write_or_refactor(self, task: str) -> str:
        log.info(f"Coder Agent v2: Working on → {task}")

        # Domain shortcut: smart contracts go through the Solidity expert.
        if solidity_expert is not None and self.looks_like_solidity(task):
            log.info("Coder Agent v2: Delegating to Solidity Expert (PulseChain/EVM mode)")
            chain = self.target_chain(task)
            return solidity_expert.write_solidity_contract(task, target_chain=chain)

        return self.complete(
            f"Task:\n{task}\n\n"
            "Implement it fully. If the task implies a specific language or "
            "framework, follow it; otherwise choose the most appropriate one and "
            "say why."
        )


# Register
coder = CoderAgent()
