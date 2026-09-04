"""
TypeScript Expert Skill for OpenHands
Professional TypeScript Specialist.
Focus: Advanced TypeScript patterns, strict type safety, performance in TS/JS, modern frontend architecture (React, Next.js), type-safe APIs, testing, build optimization.
For high-quality, maintainable frontend code in serious projects.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


from openhands_skills.expert_base import ExpertSkill


class TypescriptExpert(ExpertSkill):
    """
    Senior TypeScript Specialist.
    Delivers type-safe, performant, professional-grade TypeScript codebases.
    Especially strong for React/Next.js + 3D integrations.
    """

    def __init__(self):
        self.focus = "Building rock-solid, scalable, type-safe frontend applications that professional teams can maintain and extend."

    def build_typescript_architecture(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Advanced TS architecture + patterns + performance + type-safe integration plan."""
        log.info(f"TypescriptExpert: Building TS architecture for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " typescript 2026", "advanced typescript patterns React Next.js performance")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_stack": "TypeScript 5+ + React 19 / Next.js + strict tsconfig + Zod for runtime validation",
            "type_safety_strategy": self.type_safety_strategy(),
            "advanced_patterns": self.advanced_patterns(),
            "performance_in_ts": self.performance_in_typescript(),
            "integration_with_3d_backend": self.integration_with_3d_backend(),
            "testing_typescript": self.testing_typescript(),
            "research": research[:1100] if research else "2026 TypeScript best practices, branded types, template literal types, performance."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("typescript:architecture", f"{task} | professional TypeScript system for client work")
            except Exception:
                pass

        print("📘 TypescriptExpert: Complete professional TypeScript architecture delivered.")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior TypeScript engineer expert in type-safe, high-performance React/Next frontends.")
        self.mark_analysis(result)
        return result

    def type_safety_strategy(self) -> list:
        return [
            "Strict tsconfig (strict: true, noImplicitAny, strictNullChecks, etc.)",
            "Branded types / nominal typing for domain concepts (e.g. UserId, Price)",
            "Zod or io-ts for runtime validation + inferred types",
            "Template literal types for API route safety",
            "Discriminated unions for state machines and error handling"
        ]

    def advanced_patterns(self) -> list:
        return [
            "Compound components with proper typing",
            "Generic components and hooks (use with care for DX)",
            "Type-safe API clients (tRPC or generated clients from OpenAPI)",
            "Higher-order components / render props with full type inference",
            "Utility types library (deep partial, exact, etc.) for your domain"
        ]

    def performance_in_typescript(self) -> list:
        return [
            "Tree-shaking friendly imports (no barrel files for heavy libs)",
            "React.memo + useMemo with proper dependency typing",
            "Code splitting at route and component level (React.lazy + Suspense)",
            "Typed workers / WASM bindings for heavy computation",
            "Bundle analysis (webpack-bundle-analyzer or vite-bundle-visualizer) in CI"
        ]

    def integration_with_3d_backend(self) -> str:
        return """Type-safe integration patterns:
- Define strict interfaces for 3D asset metadata, scene configs, interaction events
- Use discriminated unions for different 3D modes (viewer, configurator, etc.)
- Backend: generate types from Prisma/OpenAPI and share with frontend
- Runtime validation on all data coming from backend or user interactions
- Error boundaries typed to catch 3D loading/runtime errors gracefully
"""

    def testing_typescript(self) -> list:
        return [
            "Vitest or Jest with ts-jest + type-aware testing",
            "React Testing Library + user-event for component tests",
            "MSW (Mock Service Worker) for API mocking with full type safety",
            "Playwright tests with typed page objects",
            "Type tests (tsd or vitest type tests) for critical utility types"
        ]

# Register
typescript_expert = TypescriptExpert()
print("📘 TypescriptExpert registered. Ready for sub_type='typescript'. Professional TS for serious frontends.")