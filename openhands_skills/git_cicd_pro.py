"""
Git + CI/CD Workflow Pro Skill.

Πραγματικό πλέον: αναλύει το συγκεκριμένο project/stack και προτείνει concrete
git workflow + CI/CD pipeline (με YAML όπου χρειάζεται) μέσω του μοντέλου, αντί
να τυπώνει σταθερά bullets.
"""

from openhands_skills.expert_base import ExpertSkill


class GitCICDPro(ExpertSkill):
    ROLE = "git_cicd"
    EXPERTISE = (
        "a DevOps engineer expert in Git workflows and CI/CD (GitHub Actions, "
        "GitLab CI, Docker, release automation)"
    )

    def suggest_git_workflow(self, project: str = "", context: dict = None) -> str:
        task = (
            "Recommend a concrete Git branching + commit + PR workflow tailored to "
            "the described project and team size. Explain when to use each branch, "
            "commit conventions, and PR gates. Be specific, not generic.\n\n"
            f"Project: {project or 'this project'}"
        )
        return self.consult(task, context, max_tokens=3000)

    def check_ci_cd(self, project: str = "", context: dict = None) -> str:
        task = (
            "Design a CI/CD pipeline for the described project. Provide a real, "
            "ready-to-use workflow file (GitHub Actions YAML) covering lint, tests, "
            "build, and deploy, plus notes on secrets and caching.\n\n"
            f"Project: {project or 'this project'}"
        )
        return self.consult(task, context, max_tokens=4000)


# Register
git_pro = GitCICDPro()
