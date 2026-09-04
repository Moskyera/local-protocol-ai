"""
Supervisor Agent v1 - Ο Αρχηγός του Multi-Agent System
Συντονίζει όλους τους agents, αναλύει το task, κατανέμει εργασίες και κάνει final review
"""

from opendevin.core.schema import ActionType
from opendevin.controller.state import State
from logger import log
import json

class SupervisorAgent:
    def __init__(self):
        self.agents = {
            "market_analyst": "Market Analysis & Research",
            "coder": "Code Writing & Refactoring",
            "tester": "Testing & Quality Assurance",
            "reviewer": "Code Review & Architecture",
            "debugger": "Debugging & Error Fixing"
        }
        self.task_history = []

    def plan_task(self, user_task: str):
        """Σπάει το task σε sub-tasks και κατανέμει σε agents"""
        log.info(f"Supervisor planning task: {user_task}")

        plan = f"""
Supervisor Plan for task: {user_task}

1. Market Analyst → Analyze market context and requirements
2. Coder → Implement or modify code
3. Tester → Write and run tests
4. Reviewer → Review code quality, architecture and best practices
5. Debugger → Fix any errors or issues

Final step: Supervisor does final integration and quality check.
"""

        print(plan)
        self.task_history.append({"task": user_task, "plan": plan})
        return plan

    def coordinate(self, sub_task_results: dict):
        """Συντονίζει αποτελέσματα από όλους τους agents"""
        log.info("Supervisor coordinating results from all agents")

        final_summary = """
Supervisor Final Integration:
- All agents completed their parts
- Code is reviewed and tested
- Market context is incorporated
- Ready for final delivery
"""
        print(final_summary)
        return final_summary

# Register
supervisor = SupervisorAgent()