"""
React Specialist Skill for OpenHands
Advanced React / frontend architecture specialist.
Focus: Component systems, performance, state management, hooks patterns, Next.js, accessibility in React, testing.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


class ReactSpecialist:
    def __init__(self):
        self.focus = "Scalable, performant, beautiful React codebases."

    def build_react_architecture(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Senior React architect deliverable: full architecture plan + patterns + performance strategy."""
        log.info(f"ReactSpecialist: Architecting React for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " react 2026", "react performance patterns")
            except Exception:
                pass

        result = {
            "task": task,
            "recommended_stack": "React 19 + TypeScript + Vite (or Next.js App Router) + Tailwind v4 + Framer Motion + TanStack Query",
            "architecture": {
                "folder_structure": "feature-based + shared/ui + shared/lib (colocation for components)",
                "patterns": [
                    "Compound Components (e.g. <Card> <Card.Header> <Card.Body>)",
                    "Custom Hooks for all cross-cutting concerns (useMobile, useReducedMotion, useThreePerformance)",
                    "Render Props / Children as Function only when truly needed",
                    "Error Boundaries + Suspense at route and heavy 3D boundaries"
                ],
                "state_strategy": "Zustand/Jotai for global + useState/useReducer locally. Avoid prop drilling.",
                "server_components": "Use React Server Components for data-heavy pages (Next.js). Keep client islands small."
            },
            "performance_roadmap": self.performance_roadmap(),
            "mobile_architecture": "Heavy 3D and complex animations must be lazy-loaded + feature-flagged per device class.",
            "professional_checklist": [
                "Bundle size budget: < 220kb gzipped initial for mobile",
                "Lighthouse CI: Performance ≥ 90, Accessibility ≥ 95 on mobile",
                "React Profiler + why-did-you-render in development",
                "Real device testing on low-end Android + latest iPhone"
            ],
            "research": research[:1300] if research else "Senior React 19 + modern patterns from 2025-2026."
        }

        print("⚛️ ReactSpecialist: Senior architecture delivered.")
        return result

    def performance_roadmap(self) -> Dict[str, list]:
        return {
            "bundle": [
                "Route-based code splitting + React.lazy for heavy 3D",
                "Tree-shake framer-motion and three.js aggressively",
                "Use import() for conditional heavy features"
            ],
            "runtime": [
                "Virtual lists for any long content (tanstack/virtual or react-window)",
                "Memoize only after measuring with React Profiler",
                "useTransition for expensive state updates"
            ],
            "rendering": [
                "React Server Components where data is static or server-fetched",
                "Suspense boundaries around 3D and data-heavy sections"
            ]
        }

    def _performance_focus(self) -> list:
        return [
            "Virtualize long lists (react-window or tanstack virtual)",
            "Image optimization (next/image or unpic)",
            "Route-based code splitting",
            "Keep bundle size under 200-250kb gzipped for mobile first load",
            "Use React Compiler when available"
        ]

    # GOD-TIER DEEP METHODS
    def god_tier_react_architecture(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: 10x React architecture with formal gates, a11y, testing, 3D islands, crypto flows, Hacash data layers, full handoffs."""
        log.info(f"ReactSpecialist (GOD TIER): God-like React architecture for: {task[:60]}")
        base = self.build_react_architecture(task, context)

        god = {
            **base,
            "god_tier_additions": {
                "mandatory": [
                    "Start with task_tracker full array + persistent_memory.retrieve",
                    "Error boundaries + Suspense around every 3D, payment, and on-chain panel",
                    "React Compiler / useMemo profiling + why-did-you-render in dev",
                    "Full a11y: ARIA, focus management, reduced motion, keyboard for all interactive 3D/controls",
                    "Bundle budget enforcement in CI (<220kb gz initial mobile)"
                ],
                "state_for_onchain_hacash": "TanStack Query with stale-while-revalidate for RPC data. Separate stores for L1 blocks, L2 channels (multi-sig state), HVM contract state. Manual refresh button always available as escape hatch.",
                "crypto_payments_islands": "Lazy load Stripe + ethers + WASM payment components. Never block initial render. Show skeleton + 'Connect wallet / Choose payment' flow.",
                "testing_gates": "Component tests (React Testing Library) for critical flows. Visual regression (Chromatic or Percy). E2E for payment + explorer refresh. Property tests for any state machine (channel states etc).",
                "handoffs": "designer.god_tier_design_system for tokens/components, threejs_expert.god_tier for 3D islands, mobile.god_tier for responsive + touch, website_builder.god_tier_build_modern_website as orchestrator, programmer for WASM/backend, crypto_payments_expert for the payment primitives, hacash_* for data models."
            },
            "god_tier_level": "10x React means the codebase is a joy to extend, the 3D and money flows are rock solid, mobile feels native, and every specialist downstream has clean handoff artifacts."
        }
        print("⚛️ ReactSpecialist (GOD TIER): God-like React architecture delivered.")
        return god

    def god_tier_react_performance_and_testing_gates(self) -> Dict[str, Any]:
        return {
            "perf": self.performance_roadmap(),
            "extra_gates": [
                "Lighthouse CI mobile P≥92, LCP <2.5s, TBT <200ms even with 3D lazy loaded",
                "Real device matrix: iPhone 15/16, Pixel 8/9, Samsung A-series + 3G throttling",
                "React Profiler flamegraphs checked in PRs for heavy routes",
                "Bundle analyzer + treeshake report on every build"
            ],
            "hacash_crypto_notes": "On-chain polling or WS must not cause re-renders of 3D scenes. Use proper selectors and React.memo / useDeferredValue."
        }

# Register
react_specialist = ReactSpecialist()
print("⚛️ ReactSpecialist (GOD TIER) registered. Ready for sub_type='react'. 10x React with 3D islands, on-chain/Hacash data, payments, a11y, perf gates.")