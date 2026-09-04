"""
Prompt Engineer & Optimizer Skill.

Πραγματικό πλέον: επιστρέφει το ΒΕΛΤΙΩΜΕΝΟ prompt. Προηγουμένως τύπωνε
"Improved: Added Chain-of-Thought..." και επέστρεφε το string
"Prompt optimized successfully" — δηλαδή δεν βελτίωνε τίποτα και ο caller
έπαιρνε ένα μήνυμα κατάστασης αντί για prompt.
"""

from openhands_skills.expert_base import ExpertSkill

_RULES = (
    "You are a prompt engineer. Rewrite prompts so a mid-sized local model can "
    "follow them reliably. Apply: an explicit role, the concrete task, hard "
    "constraints, the exact output format, and one short worked example when it "
    "removes ambiguity. Keep it tight — verbosity hurts small models. "
    "Return ONLY the rewritten prompt, nothing else."
)


class PromptOptimizer(ExpertSkill):
    ROLE = "prompt_optimizer"
    EXPERTISE = "a prompt engineer who makes instructions unambiguous for local models"
    DEFAULT_TEMPERATURE = 0.2

    def optimize_prompt(self, original_prompt: str) -> str:
        """Return an improved version of an existing prompt."""
        if not (original_prompt or "").strip():
            return "(no prompt supplied)"
        return self.consult(
            f"Improve this prompt:\n\n{original_prompt}",
            extra_system=_RULES, max_tokens=1500)

    def create_better_prompt(self, task: str) -> str:
        """Write a well-formed prompt from a bare task description."""
        if not (task or "").strip():
            return "(no task supplied)"
        return self.consult(
            f"Write a high-quality prompt that instructs a model to do this "
            f"task:\n\n{task}",
            extra_system=_RULES, max_tokens=1500)


# Register
prompt_optimizer = PromptOptimizer()
