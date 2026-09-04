"""
Documentation & Onboarding Master Skill.

Πραγματικός πλέον: παράγει αληθινό README / onboarding περιεχόμενο μέσω του
μοντέλου με βάση το task/context, αντί να τυπώνει "README generated successfully".
Κρατά τα ίδια method names (generate_readme / create_onboarding_guide).
"""

from openhands_skills.expert_base import ExpertSkill


class DocsOnboarding(ExpertSkill):
    ROLE = "docs"
    EXPERTISE = (
        "a senior technical writer who produces clear, accurate developer "
        "documentation (READMEs, onboarding guides, API docs)"
    )

    def generate_readme(self, project: str = "", context: dict = None) -> str:
        """Generate a real, project-specific README via the model."""
        task = (
            "Write a complete, professional README.md for the following project. "
            "Include: title, one-line pitch, features, prerequisites, install, "
            "usage examples, configuration (env vars), and a short skills/modules "
            f"overview. Output valid Markdown.\n\nProject: {project or 'this project'}"
        )
        return self.consult(task, context, max_tokens=4000)

    def create_onboarding_guide(self, project: str = "", context: dict = None) -> str:
        """Generate a real onboarding guide for new users/contributors."""
        task = (
            "Write a step-by-step onboarding guide for a new contributor to the "
            "following project: how to set up, run, verify it works, and where to "
            f"start contributing. Be concrete.\n\nProject: {project or 'this project'}"
        )
        return self.consult(task, context, max_tokens=3000)


# Register
docs_master = DocsOnboarding()
