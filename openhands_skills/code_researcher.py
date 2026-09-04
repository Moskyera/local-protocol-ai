"""
Code Researcher Expert Skill for OpenHands
Dedicated researcher for the programming team.
Focus: GitHub, modern libraries, code patterns, UI/UX techniques, animation/3D/web tech updates — purely for implementation (websites + general code).

Works together with:
- ProgrammerExpert (sub_type="programmer")
- WebsiteBuilder (sub_type="website")

Can be delegated directly via hierarchical supervisor (sub_type="code_researcher").

Uses safe bounded research when available (no bloat).
"""

from logger import log
from typing import Dict, Any, List, Optional
from datetime import datetime

from openhands_skills.expert_base import ExpertSkill

try:
    from safe_research_wrapper import safe_research_and_evolve, force_compact_summary
except Exception:
    safe_research_and_evolve = None
    force_compact_summary = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class CodeResearcher(ExpertSkill):
    """
    Technical researcher specialized in code + modern web development.
    Goal: feed fresh, high-quality implementation ideas to ProgrammerExpert and WebsiteBuilder.
    """

    def __init__(self):
        self.focus_areas = [
            "modern web animations (framer-motion, gsap, motion)",
            "3D on the web (three.js, @react-three/fiber, drei, react-three/drei)",
            "UI component libraries & design systems 2025-2026 (shadcn/ui, aceternity, radix, tailwind v4)",
            "fonts & typography (variable fonts, next/font, self-hosted)",
            "particle systems, canvas effects, WebGL",
            "scroll animations, Lenis, ScrollTrigger, parallax",
            "glassmorphism, neumorphism, modern glass + blur effects",
            "performance & accessibility for rich frontends",
            "trending GitHub repos for creative web experiences"
        ]

    def research_modern_web_techniques(self, topic: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Research fresh ideas for visuals, animations, 3D, fonts, interactions for websites.
        """
        log.info(f"Code Researcher: Researching modern web techniques for: {topic}")

        query = f"modern web {topic} 2025 2026 animation 3D three.js framer-motion github examples best practices"

        research = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "recommendations": [],
            "example_repos": [],
            "code_patterns": [],
            "stack_suggestions": []
        }

        # Try bounded safe research first (preferred)
        if safe_research_and_evolve:
            try:
                raw = safe_research_and_evolve(query, max_results=min(max_results, 4))
                if force_compact_summary and isinstance(raw, dict):
                    raw = force_compact_summary(str(raw))
                research["safe_research"] = raw
            except Exception as e:
                log.warning(f"safe_research in code_researcher skipped: {e}")

        # Curated high-value modern patterns (always available, high signal)
        if "3d" in topic.lower() or "three" in topic.lower() or "webgl" in topic.lower():
            research["recommendations"].extend([
                "Use @react-three/fiber + drei for React 3D (very popular 2025+)",
                "Three.js + postprocessing for nice effects (bloom, depth of field)",
                "Simple CDN three.js for pure HTML/standalone sites"
            ])
            research["example_repos"].append("https://github.com/pmndrs/react-three-fiber (official, active)")
            research["code_patterns"].append("Basic rotating 3D torus with mouse interaction + environment map")

        if "animation" in topic.lower() or "framer" in topic.lower() or "motion" in topic.lower():
            research["recommendations"].extend([
                "Framer Motion v11+ (best DX for React animations, variants, gestures, layout)",
                "GSAP for complex timeline/scroll animations (still king for pro work)",
                "Motion One or native Web Animations API for lighter weight"
            ])
            research["example_repos"].append("https://github.com/framer/motion")

        if "font" in topic.lower() or "typography" in topic.lower():
            research["recommendations"].extend([
                "Variable fonts (Inter, Space Grotesk, Satoshi, General Sans)",
                "next/font or @fontsource for self-hosting + performance",
                "font-feature-settings for nice ligatures and stylistic sets"
            ])

        if "particle" in topic.lower() or "canvas" in topic.lower():
            research["recommendations"].extend([
                "tsParticles (very powerful, React/Vanilla support)",
                "Simple canvas + requestAnimationFrame for custom lightweight particles",
                "OGL or Three.js for GPU particles"
            ])

        # General modern 2025-2026 stack
        research["stack_suggestions"] = [
            "React 19 + Tailwind v4 + Framer Motion + shadcn/ui + @radix-ui",
            "Astro or Next.js App Router for sites",
            "Lenis for buttery smooth scroll + GSAP ScrollTrigger",
            "Aceternity UI or Magic UI for beautiful copy-paste components with great motion"
        ]

        research["general_advice"] = """
For a truly modern website in 2026:
- Start with Tailwind + a good font stack (variable fonts)
- Add micro-interactions everywhere (hover, scroll, focus)
- One hero 3D or canvas element is enough (don't overdo)
- Use framer-motion for React or CSS + small JS for static
- Performance first: prefer CSS transforms, will-change, reduced motion respect
"""

        if persistent_memory:
            try:
                persistent_memory.store_learning(f"code_research:{topic}", str(research)[:1500])
            except Exception:
                pass

        print(f"🔬 Code Researcher: Fresh implementation ideas ready for '{topic}'")
        return research

    def get_github_code_ideas(self, query: str, language: str = "typescript", max_results: int = 4) -> Dict[str, Any]:
        """Targeted search for code patterns and repos (fed to programmer/website)."""
        log.info(f"Code Researcher: GitHub code ideas for '{query}' ({language})")

        result = {
            "query": query,
            "language": language,
            "ideas": [],
            "suggested_imports": [],
            "implementation_tips": []
        }

        # High-signal curated ideas (the safe_research can supplement)
        q = query.lower()
        if "3d" in q or "three" in q:
            result["ideas"].append("react-three-fiber + drei + drei/examples for quick beautiful 3D scenes")
            result["suggested_imports"].extend(["@react-three/fiber", "@react-three/drei", "three"])
            result["implementation_tips"].append("Wrap in Canvas, use useFrame for animation loop, OrbitControls for dev")

        if "animation" in q:
            result["ideas"].append("Framer Motion: use motion.div + variants + whileInView for scroll-triggered")
            result["suggested_imports"].append("framer-motion")

        if "particle" in q or "effect" in q:
            result["ideas"].append("tsParticles or lightweight custom canvas particles for hero backgrounds")
            result["implementation_tips"].append("Respect prefers-reduced-motion media query")

        if "font" in q or "type" in q:
            result["ideas"].append("Use fontsource or next/font for Inter + a display variable font (Space Grotesk)")

        result["general_modern_practices"] = [
            "Always add dark mode + system preference",
            "Use CSS container queries + modern layout (grid + subgrid)",
            "Micro-animations on every interactive element (scale, opacity, blur)",
            "Lenis or smooth-scrollbar for premium feel on long pages"
        ]

        return result

    def recommend_stack_for_modern_website(self, task_description: str) -> dict:
        """A stack chosen for THIS site.

        Recommended Next.js + Tailwind + Framer Motion + Three.js for every
        input. Measured identical for a real-time trading terminal and a static
        recipe blog — two projects whose correct stacks share almost nothing.
        """
        log.info(f"Code Researcher: Recommending stack for: {task_description[:60]}")
        return self.analyse(
            "Choose a tech stack for this specific site and justify each choice "
            "against its actual requirements — data freshness, interactivity, SEO, "
            "hosting, team size. Name what you would deliberately NOT use here and "
            "why. Do not add 3D or heavy animation unless this project needs it.",
            {"project": task_description},
            reference={"modern_default_stack": {
                "framework": "Next.js 15 / Vite + React 19 (or Astro for content-heavy)",
                "styling": "Tailwind CSS v4 + shadcn/ui",
                "animations": "Framer Motion (React) or GSAP + Lenis",
                "3d": "Three.js + @react-three/fiber/drei (one hero element)",
                "fonts": "Inter (body) + Space Grotesk or Satoshi (headings)",
                "note": "A starting point for content-led marketing sites, not a recommendation for every project.",
            }},
            max_tokens=1600,
        )

    def feed_programmer_and_website(self, task: str, context: str = "") -> str:
        """Convenience: returns ready-to-inject research notes for the other specialists."""
        research = self.research_modern_web_techniques(task)
        ideas = self.get_github_code_ideas(task)

        notes = f"""
=== CODE RESEARCHER FEED (for ProgrammerExpert + WebsiteBuilder) ===
Task: {task}

Key modern recommendations:
{chr(10).join('- ' + r for r in research.get('recommendations', [])[:6])}

Stack suggestion:
{research.get('stack_suggestions', ['React + Tailwind + Framer + Three'])}

GitHub/code patterns:
{chr(10).join('- ' + i for i in ideas.get('ideas', []))}

Implementation tips:
{chr(10).join('- ' + t for t in ideas.get('implementation_tips', []))}

General modern advice:
{research.get('general_advice', '')}
"""
        return notes.strip()

    def inject_into_implementation(self, existing_code: str, research_topic: str) -> str:
        """Takes existing code and returns a version with modern visual/research ideas applied (suggestions)."""
        research = self.research_modern_web_techniques(research_topic, max_results=3)
        return f"""// Enhanced by CodeResearcher with fresh 2025-2026 patterns
// Research topic: {research_topic}

{existing_code}

// Suggested additions from research:
// - Add framer-motion or GSAP for the hero
// - Insert a <Canvas> Three.js element (see drei docs)
// - Use variable font + font-feature-settings
// - Add tsParticles or canvas particles as subtle background
// - Glassmorphism: backdrop-blur + bg-white/10 + border-white/20

// Full research context: {str(research)[:800]}
"""


# Register
code_researcher = CodeResearcher()
print("🔬 Code Researcher registered. Ready for sub_type='code_researcher' and to feed programmer/website specialists.")