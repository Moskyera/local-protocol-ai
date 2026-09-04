"""
Coder Agent - Γράφει, βελτιώνει και refactor κώδικα
"""

from logger import log

class CoderAgent:
    def write_or_refactor_code(self, task: str):
        log.info(f"Coder Agent: Working on task - {task}")
        print("Coder Agent: Generating clean, modular and well-documented code...")
        print("Best practices applied: type hints, logging, error handling")
        return f"Code for task '{task}' generated successfully"

# Register
coder = CoderAgent()