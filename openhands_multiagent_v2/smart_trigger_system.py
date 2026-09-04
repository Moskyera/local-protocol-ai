"""
Smart Trigger System v2 - Αυτόματη ενεργοποίηση agents με πολύ έξυπνη ανίχνευση
"""

import re

from .advanced_supervisor import advanced_supervisor
from logger import log

class SmartTriggerSystem:
    def __init__(self):
        self.triggers = {
            "market_analysis": [
                "αγορά", "market", "btc", "crypto", "eth", "sol", "report", "snapshot", 
                "ανάλυση", "analysis", "τιμές", "prices", "whale", "smart money"
            ],
            "portfolio": [
                "portfolio", "allocation", "επένδυση", "συμβουλή", "πόσο btc", "cash", 
                "risk", "κατανομή", "recommendation"
            ],
            "debug": [
                "debug", "error", "bug", "λάθος", "πρόβλημα", "crash", "timeout", 
                "failed", "δεν δουλεύει", "exception"
            ],
            "code": [
                "κώδικας", "code", "refactor", "γραψε", "βελτίωσε", "fix", "function", 
                "class", "module"
            ],
            "full_briefing": [
                "full briefing", "πλήρης ενημέρωση", "όλα μαζί", "complete report", 
                "full update", "συνολική εικόνα"
            ],
            "macro": [
                "macro", "tech", "οικονομία", "economy", "ai sector", "τεχνολογία"
            ],
            "solidity": [
                "solidity", "evm", "smart contract", "erc20", "erc721", "defi", "audit contract",
                "write solidity", "gas optimize", "reentrancy", "foundry", "hardhat", "hvm",
                "ethereum contract", "blockchain code", "web3"
            ],
            "chain_analysis": [
                "chain analysis", "analyze address", "wallet trace", "contract activity", "where did it send",
                "from where received", "tx history", "explorer analysis", "on chain", "address activity",
                "trace flows", "what did the address do"
            ]
        }

    def detect_trigger(self, user_input: str):
        """Πολύ έξυπνη ανίχνευση trigger - Solidity/EVM has high priority for development tasks"""
        input_lower = user_input.lower().strip()

        log.info(f"Smart Trigger System analyzing: {user_input}")

        # Prioritize Chain Analysis (very useful for audits/debug/contract tracing)
        if any(kw in input_lower for kw in self.triggers.get("chain_analysis", [])):
            log.success("Trigger activated: chain_analysis")
            print("🔗 Smart Trigger detected: CHAIN ANALYSIS")
            return "chain_analysis"

        # Prioritize Solidity/EVM/PulseChain tasks (for OpenHands smart contract work)
        solidity_keywords = self.triggers.get("solidity", [])
        if any(kw in input_lower for kw in solidity_keywords):
            log.success("Trigger activated: solidity")
            print("🔥 Smart Trigger detected: SOLIDITY")
            return "solidity"

        for category, keywords in self.triggers.items():
            if category == "solidity":
                continue  # already checked
            if any(kw in input_lower for kw in keywords):
                log.success(f"Trigger activated: {category}")
                print(f"🔥 Smart Trigger detected: {category.upper()}")
                return category

        # Default fallback
        print("🤖 No specific trigger → Default to full analysis")
        return "default"

    def run(self, user_input: str):
        """Κεντρική εκτέλεση με trigger"""
        trigger = self.detect_trigger(user_input)

        if trigger == "market_analysis":
            return advanced_supervisor.plan_and_orchestrate(user_input)
        elif trigger == "portfolio":
            return advanced_supervisor.plan_and_orchestrate("Portfolio recommendation for current market")
        elif trigger == "debug":
            # These two branches used to RETURN A STRING and call nothing at all
            # ("Debugger Agent activated for error analysis"), so every debug and
            # coding request routed here silently did no work.
            from .debugger_agent_v2 import debugger
            return debugger.debug(user_input)
        elif trigger == "code":
            from .self_correcting_coder import self_correcting_coder
            build = self_correcting_coder.build(user_input, max_iterations=3)
            return build.to_report()
        elif trigger == "full_briefing":
            return advanced_supervisor.plan_and_orchestrate("Send full market briefing")
        elif trigger == "macro":
            return advanced_supervisor.plan_and_orchestrate("Macro & Tech analysis")
        elif trigger == "solidity":
            # This branch used to print a banner, ask the supervisor for a plan,
            # and append the literal string "[Auto-routed to Solidity Expert +
            # Coder + Reviewer + Tester + Debugger]" — naming five agents and
            # calling none of them. The note read like a receipt for work that
            # never happened. It now calls the expert.
            print("🔷 Solidity/EVM task detected - activating the Solidity expert")
            plan = advanced_supervisor.plan_and_orchestrate(user_input)
            try:
                from openhands_skills.solidity_expert import solidity_expert
                low = user_input.lower()
                if any(k in low for k in ("audit", "review", "vulnerab", "reentran", "έλεγχο")):
                    expert_out = solidity_expert.audit_solidity(user_input)
                    label = "Solidity audit"
                else:
                    expert_out = solidity_expert.write_solidity_contract(user_input)
                    label = "Solidity contract"
                return f"{plan}\n\n--- {label} (solidity_expert) ---\n{expert_out}"
            except Exception as e:
                log.error(f"smart_trigger solidity route failed: {e}")
                return f"{plan}\n\n[Solidity expert could not run: {e}]"

        elif trigger == "chain_analysis":
            # Same defect: it appended "[Auto-routed to Chain Analysis Expert]"
            # and, when the text mentioned a bug, "[Also routing to Debugger]" —
            # while calling neither. It now extracts the address and runs the
            # analysis, and says plainly when there is no address to analyse.
            print("🔗 Chain Analysis task detected - running the chain expert")
            plan = advanced_supervisor.plan_and_orchestrate(user_input)
            m = re.search(r"0x[a-fA-F0-9]{40}", user_input or "")
            if not m:
                return (f"{plan}\n\n[No 0x address found in the request, so no chain "
                        f"analysis was run. Send the address and I will trace it.]")
            try:
                from openhands_skills.chain_analysis_expert import chain_analysis_expert
                low = user_input.lower()
                chain = "pulsechain" if ("pulse" in low or "pls" in low) else "ethereum"
                report = chain_analysis_expert.analyze_address(
                    m.group(0), chain=chain, context=user_input)
                out = f"{plan}\n\n--- Chain analysis of {m.group(0)} on {chain} ---\n{report}"
                if any(k in low for k in ("bug", "error", "revert", "exploit", "suspicious")):
                    try:
                        from .debugger_agent_v2 import debugger
                        out += f"\n\n--- Debugger correlation ---\n{debugger.debug(user_input)}"
                    except Exception as e:
                        out += f"\n\n[Debugger could not run: {e}]"
                return out
            except Exception as e:
                log.error(f"smart_trigger chain_analysis route failed: {e}")
                return f"{plan}\n\n[Chain analysis could not run: {e}]"
        else:
            return advanced_supervisor.plan_and_orchestrate(user_input)

# Register
smart_trigger = SmartTriggerSystem()