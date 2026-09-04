"""
Debugger Agent v2 - Ειδικός στην ανάλυση και επίλυση complex errors
(Ενισχυμένος για Solidity / EVM / PulseChain)
"""

from openhands_skills.debugging_expert import debug_expert
from openhands_skills.solidity_expert import solidity_expert
import re
from logger import log
from .base_llm_agent import BaseLLMAgent

class DebuggerAgent(BaseLLMAgent):
    ROLE = "debugger"
    SYSTEM_PROMPT = (
        "You are an expert debugger. Given an error message, stack trace or "
        "buggy code, find the root cause. Explain the cause precisely, then give "
        "a concrete minimal fix (with code), and finally how to reproduce and "
        "verify it. Do not guess wildly — reason from the evidence provided."
    )

    #: Fixed reference. Useful, but it is the same six lines for every error,
    #: so it is labelled rather than presented as a diagnosis.
    _BUG_DB = """Common DeFi/Solidity failure modes (reference — not findings about your error):
- Reentrancy: nonReentrant + checks-effects-interactions
- Oracle manipulation: multiple oracles + TWAP
- Flash loan: reentrancy guard + balance checks
- Integer issues: Solidity 0.8+ (or SafeMath below it)
- Access control: Ownable + roles
PulseChain: lower gas makes multi-step attacks cheaper — test on a fork."""

    def debug(self, error: str):
        """Diagnose an error. The contract branch used to diagnose nothing.

        Any error text containing "contract", "revert", "evm", "gas" etc. took a
        branch that: passed the ERROR MESSAGE to solidity_expert.audit_solidity
        as though it were Solidity source (it is not, so the auditor refused),
        appended a hardcoded six-line bug list, and returned a fixed
        "1. Reproduce 2. Isolate 3. Patch 4. Re-audit 5. Test on fork".

        It never called the model. The generic branch below it did. So the
        "advanced Solidity/PulseChain" path returned strictly less analysis than
        the ordinary one, for exactly the errors it claimed to specialise in.
        """
        log.info(f"Debugger Agent v2: analyzing → {str(error)[:120]}")
        if not (error or "").strip():
            return "(no error text was passed, so nothing was diagnosed)"

        try:
            low = error.lower()
            onchain = any(kw in low for kw in (
                "solidity", "evm", "contract", "pulsechain", "revert",
                "out of gas", "reentrancy"))

            context_parts = []

            # Audit the code only when there IS code. audit_solidity on an error
            # message returns a refusal, which was then presented as "the audit".
            if onchain and self.looks_like_solidity(error):
                try:
                    context_parts.append("Solidity audit of the supplied source:\n"
                                         + str(solidity_expert.audit_solidity(error)))
                except Exception as e:
                    log.warning(f"Debugger: solidity audit failed: {e}")

            # Real on-chain context, when a real address is present.
            addresses = re.findall(r"0x[a-fA-F0-9]{40}", error)
            if onchain and addresses:
                try:
                    from openhands_skills.chain_analysis_expert import chain_analysis_expert
                    ch = "pulsechain" if "pulse" in low else "ethereum"
                    context_parts.append(
                        f"Chain analysis of {addresses[0]}:\n"
                        + str(chain_analysis_expert.analyze_address(
                            addresses[0], chain=ch, context=error)))
                    if any(w in low for w in ("deployer", "creator", "deploy")):
                        creator = chain_analysis_expert.analyze_contract_creator(
                            addresses[0], chain=ch, context=error)
                        context_parts.append("Contract creator:\n"
                                             + str(creator.get("summary", "")))
                except Exception as e:
                    log.warning(f"Debugger: chain analysis failed: {e}")
            elif onchain and any(w in low for w in ("deployer", "creator", "deploy")):
                # The old code called analyze_contract_creator("0x0") here and
                # reported the result. The zero address is not the deployer.
                context_parts.append(
                    "No contract address was present in the error, so no creator "
                    "analysis was run.")

            # THE DIAGNOSIS. This is what the branch was missing.
            prompt = f"Diagnose and fix this error / bug:\n\n{error}"
            if context_parts:
                prompt += "\n\n### Gathered context\n" + "\n\n".join(
                    p[:3000] for p in context_parts)
            diagnosis = self.complete(prompt)

            if not onchain:
                return diagnosis
            return (f"{diagnosis}\n\n{self._BUG_DB}"
                    + ("\n\n### Context used\n" + "\n\n".join(
                        p[:1500] for p in context_parts) if context_parts else ""))

        except Exception as e:
            log.error(f"Debugger v2 error handling: {e}")
            return (f"(debugger failed during analysis: {type(e).__name__}: "
                    f"{str(e)[:200]}) — nothing above this line is a diagnosis.")


# Register
debugger = DebuggerAgent()