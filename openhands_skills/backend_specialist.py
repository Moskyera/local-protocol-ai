"""
Backend Specialist Skill for OpenHands
Professional Backend & API Specialist.
Focus: REST/GraphQL APIs, databases, authentication, server logic, data modeling, integration with frontend (React/Three.js sites).
"""

from logger import log
from typing import Dict, Any

from openhands_skills.expert_base import ExpertSkill

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


class BackendSpecialist(ExpertSkill):
    """
    Senior Backend Engineer for modern websites and web apps.
    Builds secure, scalable backend that powers beautiful frontends.
    """

    ROLE = "backend"
    EXPERTISE = (
        "a senior backend engineer expert in REST/GraphQL APIs, databases, auth, "
        "scalability and secure server design"
    )

    def __init__(self):
        self.focus = "Reliable data and logic layer that makes the website feel alive and professional."

    def build_backend(self, task: str, context: Dict = None) -> Dict[str, Any]:
        log.info(f"BackendSpecialist: Building backend for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " backend 2026", "modern backend patterns")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_stack": "Next.js API routes / Supabase / Firebase / Node + Express + Postgres (or PlanetScale)",
            "architecture": self.architecture_recommendations(),
            "auth_and_security": self.auth_security_best_practices(),
            "data_model_example": self.data_model_example(task),
            "api_design_tips": self.api_design_tips(),
            "integration_with_frontend": "Use TanStack Query or SWR on React side. Type-safe with Zod + OpenAPI.",
            "research": research[:1100] if research else "Serverless + edge functions for 2026 performance.",
            # Real, task-specific architecture reasoning from the model:
            "expert_analysis": self.consult(
                f"Design the backend for this task. Recommend the concrete stack, "
                f"data model, API surface, auth model and the top risks.\n\n{task}",
                context,
            ),
        }

        log.info("BackendSpecialist: backend architecture + expert analysis delivered.")
        return result

    def architecture_recommendations(self) -> list:
        return [
            "Edge functions for low-latency (Vercel/Cloudflare)",
            "Database: Postgres with Prisma or Drizzle ORM",
            "Auth: NextAuth / Clerk / Supabase Auth (with row level security)",
            "File storage: Vercel Blob / S3 / Supabase Storage",
            "Real-time: Supabase Realtime or Pusher if needed"
        ]

    def auth_security_best_practices(self) -> list:
        return [
            "Always use HTTPS + secure cookies",
            "Implement rate limiting on public endpoints",
            "Validate all input with Zod",
            "Use environment variables, never hardcode secrets",
            "Audit with OWASP checklist"
        ]

    def data_model_example(self, domain: str) -> str:
        return f"""// Example Prisma schema snippet for {domain}
model User {{
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  // add relations for projects, etc.
}}

model Project {{
  id          String   @id @default(cuid())
  title       String
  description String?
  // 3D assets, etc.
}}
"""

    def api_design_tips(self) -> list:
        return [
            "REST for simple CRUD, GraphQL or tRPC for complex",
            "Consistent error responses + pagination",
            "Version your APIs if public",
            "Document with Swagger / Scalar"
        ]

# Register
backend_specialist = BackendSpecialist()
print("🔧 BackendSpecialist registered. Ready for sub_type='backend'.")