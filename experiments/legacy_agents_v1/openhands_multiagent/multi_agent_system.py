"""
Multi-Agent System Orchestrator for OpenHands
Συντονίζει Supervisor + όλους τους specialist agents
"""

from supervisor_agent import supervisor
from market_analyst_agent import market_analyst
from coder_agent import coder
from tester_agent import tester
from reviewer_agent import reviewer
from debugger_agent import debugger
from logger import log

class MultiAgentSystem:
    def run_full_task(self, user_task: str):
        log.info(f"Multi-Agent System started for task: {user_task}")

        print("\n" + "="*60)
        print("🚀 MULTI-AGENT SYSTEM STARTED")
        print("="*60)

        # Step 1: Supervisor σχεδιάζει
        plan = supervisor.plan_task(user_task)

        # Step 2: Market Analyst
        market_data = market_analyst.analyze_market()

        # Step 3: Coder
        code = coder.write_or_refactor_code(user_task)

        # Step 4: Tester
        tests = tester.run_tests(user_task)

        # Step 5: Reviewer
        review = reviewer.review_code(user_task)

        # Step 6: Debugger (αν χρειάζεται)
        debug = debugger.debug_and_fix("Any issues found")

        # Step 7: Supervisor Final Integration
        final = supervisor.coordinate({
            "market": market_data,
            "code": code,
            "tests": tests,
            "review": review
        })

        print("\n🎯 MULTI-AGENT TASK COMPLETED SUCCESSFULLY")
        return final

# Register the full system
multi_agent = MultiAgentSystem()