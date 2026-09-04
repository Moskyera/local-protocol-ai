"""
DevOps Engineer Skill for OpenHands
Professional DevOps & Deployment Specialist.
Focus: CI/CD pipelines, deployment to modern platforms (Vercel, Netlify, AWS), monitoring, security, scaling, infrastructure as code.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class DevOpsEngineer(ExpertSkill):
    """
    Senior DevOps Engineer for web projects.
    Turns beautiful designs and code into reliable, monitored production websites.
    """

    def __init__(self):
        self.focus = "Shipping fast, safe, and observable websites with professional infrastructure."

    def handle_deployment(self, task: str, context: Dict = None) -> Dict[str, Any]:
        log.info(f"DevOpsEngineer: Handling deployment for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " devops 2026", "modern web deployment")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_platform": "Vercel (for Next.js/React/Three.js) or Cloudflare Pages + Workers",
            "ci_cd_pipeline": self.ci_cd_pipeline(),
            "monitoring_setup": self.monitoring_setup(),
            "security_hardening": self.security_hardening(),
            "scaling_strategies": "Edge caching, ISR/SSG, serverless functions, auto-scaling DBs",
            "research": research[:1000] if research else "2026 best practices: GitHub Actions + preview deployments."
        }

        print("🚀 DevOpsEngineer: Professional deployment & infra plan delivered.")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior DevOps/SRE engineer expert in CI/CD, IaC, observability and hardening.")
        self.mark_analysis(result)
        return result

    def ci_cd_pipeline(self) -> str:
        return """# Example GitHub Actions workflow (add to .github/workflows/deploy.yml)
name: Deploy
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install
      - run: pnpm build
      - uses: vercel/action@master  # or netlify
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
"""

    def monitoring_setup(self) -> list:
        return [
            "Vercel Analytics + Speed Insights",
            "Sentry for error tracking",
            "Uptime monitoring (Better Uptime / Pingdom)",
            "Lighthouse CI in pipeline for performance regression",
            "Real User Monitoring (RUM)"
        ]

    def security_hardening(self) -> list:
        return [
            "Enable all Vercel/Netlify security headers",
            "Regular dependency audits (npm audit / Snyk)",
            "WAF if on AWS/Cloudflare",
            "Secrets management (never in code)",
            "Regular penetration testing for high-value sites"
        ]

# Register
devops_engineer = DevOpsEngineer()
print("🚀 DevOpsEngineer registered. Ready for sub_type='devops'.")