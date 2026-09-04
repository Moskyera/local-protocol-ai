"""
Debugger Agent - Εντοπίζει και διορθώνει bugs
"""

from debugging_expert import debug_expert
from logger import log

class DebuggerAgent:
    def debug_and_fix(self, error: str):
        log.info(f"Debugger Agent: Fixing error - {error}")
        fix = debug_expert.debug_error(error)
        return fix

# Register
debugger = DebuggerAgent()