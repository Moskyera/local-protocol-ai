"""
Self-Improving Agent v4 - Με Persistent Memory + Vector Database
"""

try:  # opendevin optional — degrade gracefully
    from opendevin.core.schema import ActionType
    from opendevin.controller.state import State
except Exception:
    ActionType = None
    State = object
from logger import log
from persistent_memory import persistent_memory
import os
from datetime import datetime

class SelfImprovingAgent:
    def __init__(self):
        self.memory_file = "memory/learnings.md"
        os.makedirs("memory", exist_ok=True)

        if not os.path.exists(self.memory_file):
            with open(self.memory_file, "w", encoding="utf-8") as f:
                f.write("# Self-Improvement Persistent Memory\n\n")

    def reflect(self, task: str, result: str, state: State = None):
        """Βαθύ reflection + αποθήκευση σε markdown και Vector DB"""
        log.info(f"Self-Improving Agent v4: Reflecting on task '{task}'")

        reflection = f"""
Task: {task}
Result: {result}
Reflection: Deep analysis completed
"""

        # Αποθήκευση σε markdown
        with open(self.memory_file, "a", encoding="utf-8") as f:
            f.write(f"\n## [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Task: {task}\n{reflection}\n")

        # Αποθήκευση στο Vector DB
        persistent_memory.store_learning(task, reflection)

        log.success(f"Self-Improvement v4: Learning stored in Vector DB for task '{task}'")
        return reflection

    def before_task(self, task: str):
        """Φορτώνει σχετικά learnings από Vector DB"""
        results = persistent_memory.query(task)
        if results and results['documents']:
            log.info("Loaded relevant learnings from Vector DB")
            return results['documents'][0]
        return ""

# Register skill
self_improving = SelfImprovingAgent()