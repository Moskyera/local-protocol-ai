"""
Capability Evolver Skill v4 Final - Με Vector Database
"""

from logger import log
from persistent_memory import persistent_memory
import os
from datetime import datetime

class CapabilityEvolver:
    def __init__(self):
        self.skills_dir = "openhands_skills"
        os.makedirs(self.skills_dir, exist_ok=True)

    def analyze_and_evolve(self, task: str, result: str, duration: float = 0):
        """Αναλύει performance και αποθηκεύει στο Vector DB"""
        log.info(f"Capability Evolver v4 analyzing task: {task}")

        analysis = f"""
## Evolution Analysis [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]
Task: {task}
Duration: {duration:.2f}s
Result: {result}

Capability Insights:
- Patterns detected
- Opportunities for automation
- Suggested new skills or improvements
"""

        # Αποθήκευση στο Vector DB
        persistent_memory.store_learning(task, analysis)

        print(analysis)
        return analysis

    def create_skill(self, skill_name: str, description: str, purpose: str):
        """Δημιουργεί πλήρες νέο skill"""
        file_path = f"{self.skills_dir}/{skill_name}.py"
        
        template = f'''"""
{skill_name.replace("_", " ").title()} Skill
{purpose}
"""

from logger import log

class {skill_name.replace("_", "").title()}:
    def __init__(self):
        log.info(f"{{skill_name}} skill initialized")

    def run(self, input_data: str):
        """Main execution method"""
        log.info(f"Executing {skill_name} with input: {{input_data[:100]}}...")
        return f"{{skill_name}} executed successfully"

# Register skill
{skill_name} = {skill_name.replace("_", "").title()}()
'''

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(template)

        log.success(f"New skill created: {file_path}")
        return f"Skill '{skill_name}' created successfully at {file_path}"

    def suggest_evolution(self, context: str = ""):
        """Propose concrete capability upgrades for THIS system.

        Previously printed three hardcoded bullets and returned the string
        "Evolution suggestions generated" — the caller got a status message
        instead of any suggestions.
        """
        try:
            from openhands_skills.expert_base import ExpertSkill

            class _E(ExpertSkill):
                ROLE = "capability_evolver"
                EXPERTISE = ("a systems architect who proposes concrete, "
                             "verifiable upgrades to a local multi-agent stack")
            return _E().consult(
                "Propose the highest-value concrete improvements to this agent "
                "system. For each: what it fixes, how to verify it worked, and "
                "the risk. Prefer things that are measurable over things that "
                "merely sound advanced.\n\n" + (context or
                "Local llama.cpp backend, MCP skills, deterministic analyzers, "
                "self-correcting coder, web and CAD builders."),
                max_tokens=2000)
        except Exception as e:
            return f"(capability_evolver unavailable: {e})"

# Register skill
evolver = CapabilityEvolver()