"""
Tester Agent v2 - Πραγματικός agent παραγωγής tests.

Παράγει πραγματικά test suites μέσω του μοντέλου (pytest για Python,
Foundry για Solidity). ΔΕΝ ισχυρίζεται πλέον ψεύτικα "all tests passed" —
προαιρετικά μπορεί να τρέξει πραγματικά pytest σε δοσμένο path και να
επιστρέψει το αληθινό αποτέλεσμα.
"""

import subprocess
import sys
from typing import Optional

from logger import log
from .base_llm_agent import BaseLLMAgent

try:
    from openhands_skills.solidity_expert import solidity_expert
except Exception:  # pragma: no cover
    solidity_expert = None


class TesterAgent(BaseLLMAgent):
    ROLE = "tester"
    # Was inheriting 8192. For a one-line function the model happily spent ~2000
    # tokens importing Decimal and Fraction, which is why this agent took 13x
    # longer than every other one. Tests should be proportionate to the code.
    DEFAULT_MAX_TOKENS = 2048
    SYSTEM_PROMPT = (
        "You are a senior test engineer. Write a pytest suite for the given code "
        "or feature.\n"
        "SCOPE THE TESTS TO THE CODE. A one-line function needs a handful of "
        "assertions, not an exhaustive matrix — do not invent exotic types "
        "(Decimal, Fraction, numpy) unless the code actually handles them.\n"
        "Cover, in this order and only where they apply: the happy path, "
        "boundary values, invalid input, error paths, and a security/abuse case "
        "when the code touches input, files, network or shell.\n"
        "Return ONE fenced code block, then at most three bullet points naming "
        "what is NOT covered. No commentary beyond that."
    )

    def run_tests(self, feature: str) -> str:
        log.info(f"Tester Agent v2: Generating tests for {feature}")

        if solidity_expert is not None and any(
            kw in feature.lower()
            for kw in ("solidity", "evm", "erc", "pulsechain", "smart contract")
        ):
            log.info("Tester Agent v2: Foundry tests via Solidity Expert")
            chain = self.target_chain(feature)
            return solidity_expert.write_tests(feature, target_chain=chain)

        return self.complete(
            f"Write a complete automated test suite for the following "
            f"feature/code:\n\n{feature}"
        )

    def execute_pytest(self, target_path: str, extra_args: Optional[list] = None) -> str:
        """Actually run pytest against a path and return the real output.

        This is the honest counterpart to the old fake "all tests passed".
        """
        # sys.executable, NOT bare "python". Measured on this machine, the three
        # interpreters a bare name can hit:
        #   the venv        C:/AI/ai-env/Scripts/python.exe          (has pytest)
        #   the Store stub  .../WindowsApps/python
        #   uv's cpython    .../uv/python/cpython-3.14-.../python.exe (NO pytest)
        # The subprocess picked the last one, so this reported
        # "pytest FAILED (exit 1) -- No module named pytest" for a suite that
        # passes. Every run the tester agent performed failed, whatever the code
        # did, and the self-correcting coder loop reads this verdict.
        cmd = [sys.executable, "-m", "pytest", target_path, "-q"] + (extra_args or [])
        log.info(f"Tester Agent v2: running {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            tail = (proc.stdout or "") + (proc.stderr or "")
            if "No module named pytest" in tail:
                return ("(pytest is not installed in this interpreter: "
                        f"{sys.executable} — no tests were run, so this is NOT "
                        "a test failure)")
            status = "PASSED" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
            return f"pytest {status}\n\n{tail[-4000:]}"
        except FileNotFoundError:
            return "(pytest not installed — run: pip install pytest)"
        except subprocess.TimeoutExpired:
            return "(pytest timed out after 600s)"
        except Exception as e:
            return f"(pytest execution error: {e})"


# Register
tester = TesterAgent()
