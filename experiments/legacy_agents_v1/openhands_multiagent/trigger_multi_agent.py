"""
Trigger-Based Multi-Agent System for OpenHands
Ο Supervisor ενεργοποιείται αυτόματα με keywords και κατανέμει εργασίες
"""

from supervisor_agent import supervisor
from market_analyst_agent import market_analyst
from coder_agent import coder
from tester_agent import tester
from reviewer_agent import reviewer
from debugger_agent import debugger
from logger import log

class TriggerMultiAgent:
    def __init__(self):
        self.triggers = {
            "market": ["αγορά", "market", "btc", "crypto", "analysis", "report", "snapshot"],
            "portfolio": ["portfolio", "allocation", "επένδυση", "συμβουλή"],
            "debug": ["debug", "error", "bug", "πρόβλημα", "λάθος"],
            "code": ["κώδικας", "code", "refactor", "γραψε"],
            "full": ["full briefing", "πλήρης ενημέρωση", "όλα μαζί"]
        }

    def detect_and_run(self, user_input: str):
        """Αυτόματη ανίχνευση trigger και εκτέλεση"""
        user_input_lower = user_input.lower()

        log.info(f"Trigger detection for input: {user_input}")

        # Market Analysis trigger
        if any(k in user_input_lower for k in self.triggers["market"]):
            print("🔍 Trigger detected: Market Analysis")
            supervisor.plan_task(user_input)
            market_analyst.analyze_market()
            return "Market Analysis executed"

        # Portfolio trigger
        elif any(k in user_input_lower for k in self.triggers["portfolio"]):
            print("💼 Trigger detected: Portfolio Advisor")
            supervisor.plan_task(user_input)
            return "Portfolio Advisor executed"

        # Debug trigger
        elif any(k in user_input_lower for k in self.triggers["debug"]):
            print("🐞 Trigger detected: Debugging")
            debugger.debug_and_fix(user_input)
            return "Debugging executed"

        # Full briefing trigger
        elif any(k in user_input_lower for k in self.triggers["full"]):
            print("🌍 Trigger detected: Full Briefing")
            supervisor.plan_task(user_input)
            return "Full Multi-Agent Briefing executed"

        else:
            print("🤖 No specific trigger detected → Default to Supervisor planning")
            supervisor.plan_task(user_input)
            return "Supervisor planning started"

# Register the trigger system
trigger_system = TriggerMultiAgent()