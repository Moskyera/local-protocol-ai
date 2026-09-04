"""
Designer Expert Skill for OpenHands
UI/UX + Visual Designer specialist.
Focus: Design systems, color palettes, typography, aesthetics, layout, mobile-first design, user flows, accessibility, visual polish.
Works together with:
- WebsiteBuilder (sub_type="website")
- ProgrammerExpert
- ThreeJSExpert, ReactSpecialist, MobileResponsiveExpert

Can be delegated directly via hierarchical supervisor (sub_type="designer").
"""

from logger import log
from typing import Dict, Any, List, Optional

from openhands_skills.expert_base import ExpertSkill

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


class Designer(ExpertSkill):
    """
    Visual + UX Designer.
    Goal: Make websites look and feel professional, cohesive, and excellent on all devices (especially mobile).
    """

    def __init__(self):
        self.design_principles = [
            "Mobile-first design (design for phones first, then scale up)",
            "Strong visual hierarchy and breathing room",
            "Consistent design system (colors, typography, spacing, components)",
            "Touch-friendly targets (min 44px), good contrast",
            "Performance-aware visuals (prefer CSS over heavy images/3D when possible on mobile)",
            "Micro-interactions that feel premium but not distracting",
            "Accessibility (WCAG AA minimum)"
        ]

    def design_website(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Professional full design direction. Returns production-ready specs that a senior designer would deliver."""
        log.info(f"Designer: Designing for: {task[:70]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " visual design mobile-first", "design systems 2026")
            except Exception:
                pass

        palette = self.create_color_palette(task)
        tokens = self.generate_design_tokens(palette, task)

        design = {
            "task": task,
            "design_system": self._create_design_system(task),
            "design_tokens": tokens,  # Ready-to-use JSON for Tailwind / CSS vars / Figma
            "color_palette": palette,
            "typography_scale": self.generate_typography_scale(),
            "mobile_first_strategy": self._mobile_first_strategy(),
            "mobile_ux_checklist": self.mobile_ux_checklist(),
            "visual_direction": self._visual_direction(task),
            "component_specs": self._component_specs(),
            "research_notes": research[:1600] if research else "Professional modern design principles (2026).",
            "senior_recommendations": [
                "Start every project with a 375px mobile canvas in Figma.",
                "Define tokens first (spacing, type, color, radius, motion) before any UI.",
                "Always include reduced-motion variants and high-contrast mode.",
                "For 3D elements: provide static fallback + 'enhance' toggle on mobile.",
                "Measure real thumb reach zones on iPhone 15/16 and Pixel 8/9."
            ]
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("designer:website", f"{task} | senior mobile-first design direction")
            except Exception:
                pass

        print("🎨 Designer: Senior-level design direction delivered (tokens, mobile checklist, pro specs).")
        return design

    def generate_design_tokens(self, palette: Dict[str, str], project: str) -> Dict[str, Any]:
        """Returns a professional design token set (inspired by real design systems like Material 3 / Tailwind / shadcn)."""
        return {
            "colors": palette,
            "spacing": {
                "base": "0.5rem",
                "scale": [0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8, 12, 16],
                "fluid": "clamp(0.75rem, 2vw, 1.25rem)"
            },
            "typography": self.generate_typography_scale(),
            "radius": {"sm": "0.375rem", "md": "0.75rem", "lg": "1rem", "xl": "1.5rem", "full": "9999px"},
            "shadow": {
                "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
                "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
                "glass": "0 8px 32px rgb(0 0 0 / 0.12)"
            },
            "motion": {
                "spring": "cubic-bezier(0.23, 1, 0.32, 1)",
                "duration": {"fast": "120ms", "normal": "200ms", "slow": "320ms"}
            },
            "project": project
        }

    def generate_typography_scale(self) -> Dict[str, str]:
        """Professional fluid typography scale (mobile-first, accessible)."""
        return {
            "xs": "clamp(0.75rem, 1.8vw, 0.875rem)",
            "sm": "clamp(0.875rem, 2vw, 1rem)",
            "base": "clamp(1rem, 2.2vw, 1.125rem)",
            "lg": "clamp(1.125rem, 2.5vw, 1.25rem)",
            "xl": "clamp(1.25rem, 3vw, 1.5rem)",
            "2xl": "clamp(1.5rem, 4vw, 2rem)",
            "3xl": "clamp(1.875rem, 5vw, 2.5rem)",
            "display": "clamp(2.5rem, 8vw, 4.5rem)"
        }

    def mobile_ux_checklist(self) -> List[str]:
        """Senior mobile UX checklist (what a real mobile designer checks)."""
        return [
            "Thumb zone: primary CTAs in the bottom 60% of the screen on 375px",
            "Tap targets minimum 44×44px with 8px padding between",
            "Text contrast 4.5:1 minimum (AA), 7:1 for body text on dark backgrounds",
            "No horizontal scroll on base mobile",
            "Safe-area-inset support for notched devices (iOS + Android)",
            "Reduced motion respected everywhere (especially 3D and heavy animations)",
            "Lighthouse mobile score target ≥ 90 (performance + accessibility)",
            "Tested on real devices: iPhone 15/16, Pixel 8/9, Samsung mid-range"
        ]

    #: The six keys generate_design_tokens() indexes. The shape is a contract.
    PALETTE_KEYS = ("bg", "surface", "text", "accent", "accent2", "glass")

    #: Used when the model cannot be reached — and labelled as such by the
    #: caller, rather than passed off as a palette designed for the brief.
    FALLBACK_PALETTE = {
        "bg": "#0A0A0A", "surface": "#171717", "text": "#EDEDED",
        "accent": "#67E8F9", "accent2": "#A78BFA",
        "glass": "rgba(255,255,255,0.055)",
    }

    def create_color_palette(self, brand_vibe: str = "modern premium") -> dict:
        """A palette derived from `brand_vibe`, not selected from two constants.

        This used to be a two-branch lookup: if the vibe mentioned "premium" or
        "luxury" you got a gold-on-black set, and for EVERYTHING else — neon
        cyberpunk, calm scandinavian, a children's brand — you got the same
        cyan/violet dark palette. Measured: two opposite briefs returned
        byte-identical colours. A palette that ignores the brand is not a
        design decision, it is a default with a docstring.

        The shape is unchanged because generate_design_tokens() indexes these
        exact six keys.
        """
        import json as _json
        import re as _re

        vibe = (brand_vibe or "").strip() or "modern premium"

        prompt = (
            "Design a cohesive six-colour system for this brand direction.\n\n"
            f"Brand direction: {vibe}\n\n"
            "Return ONLY a JSON object, no prose, with exactly these keys:\n"
            '  bg, surface, text, accent, accent2, glass\n'
            "bg/surface/text/accent/accent2 must be #RRGGBB hex. glass must be an\n"
            "rgba(...) string. bg and text must have a contrast ratio of at least\n"
            "7:1 against each other. surface must be distinguishable from bg but\n"
            "clearly in the same family. Let the direction genuinely drive the\n"
            "hues — a calm brief must not come back neon."
        )
        raw = self.consult(prompt, temperature=0.4, max_tokens=400)

        palette, source = None, "fallback"
        m = _re.search(r"\{.*?\}", raw or "", _re.S)
        if m:
            try:
                cand = _json.loads(m.group(0))
                hexes = all(
                    isinstance(cand.get(k), str)
                    and _re.fullmatch(r"#[0-9a-fA-F]{6}", cand[k].strip())
                    for k in ("bg", "surface", "text", "accent", "accent2"))
                glass = isinstance(cand.get("glass"), str) and \
                    cand["glass"].strip().lower().startswith("rgba(")
                if hexes and glass:
                    palette = {k: cand[k].strip() for k in self.PALETTE_KEYS}
                    source = "designed_for_this_brief"
            except Exception as e:
                log.warning(f"Designer: palette JSON unusable: {e}")

        if palette is None:
            log.warning(f"Designer: falling back to the default palette for "
                        f"vibe={vibe!r} — the model did not return a usable one")
            palette = dict(self.FALLBACK_PALETTE)

        # Carried alongside the tokens, never in place of them, so a caller can
        # tell a designed palette from the stand-in.
        palette["_source"] = source
        palette["_brand_vibe"] = vibe
        return palette

    def mobile_breakpoints(self) -> str:
        """Recommended responsive breakpoints and approach."""
        return """
Mobile-first breakpoints (Tailwind style):
- base (mobile): 320px - 639px
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px

Strategy:
1. Design the entire experience for 375px first.
2. Use container queries + fluid units (clamp, svh, dvh).
3. Touch targets ≥ 44px, comfortable thumb reach.
4. Reduce motion and 3D complexity below 640px.
5. Test on real phones (not just browser devtools).
"""

    def _create_design_system(self, task: str) -> Dict[str, Any]:
        return {
            "typography": "Inter (body) + Space Grotesk or Satoshi (display). Variable fonts preferred.",
            "spacing": "8px base grid, generous whitespace on desktop, tighter but still comfortable on mobile.",
            "elevation": "Glassmorphism or very subtle shadows. On mobile prefer blur + transparency.",
            "motion": "Subtle, purposeful. Respect prefers-reduced-motion. Use spring physics for feel.",
            "brand_note": f"Tailored for: {task}"
        }

    def _mobile_first_strategy(self) -> List[str]:
        return [
            "Stack everything vertically by default on mobile.",
            "Use large, clear tap areas and legible text (min 16px body on phone).",
            "Collapse complex navigation into hamburger or bottom bar.",
            "Lazy-load heavy 3D / images on mobile or provide 'lite' mode.",
            "Test thumb zones (bottom 1/3 of screen is easiest to reach one-handed)."
        ]

    def _visual_direction(self, task: str) -> str:
        return f"Modern, clean, premium feel with excellent contrast. Strong use of negative space. One hero visual moment (3D or bold typography). Micro details that reward attention without overwhelming. Optimized for both desktop delight and mobile clarity."

    def _component_specs(self) -> Dict[str, str]:
        return {
            "buttons": "Rounded 2xl or full, generous padding, clear hover/focus/active states. On mobile bigger height.",
            "cards": "Glass or soft surface, good internal padding, subtle lift on hover (desktop only).",
            "navigation": "Desktop: elegant horizontal. Mobile: bottom nav or clean hamburger with slide-in.",
            "3d_integration": "Treat 3D as hero or accent. On mobile: lower quality or static fallback."
        }

# GOD-TIER DEEP METHODS (appended before registration)
    def god_tier_design_website(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: Full senior design direction with tokens, 3D guidelines, mobile obsession, accessibility as first-class, crypto/Hacash specific aesthetics, handoff perfection."""
        log.info(f"Designer (GOD TIER): God-like design direction for: {task[:60]}")
        base = self.design_website(task, context)

        god = {
            **base,
            "god_tier_additions": {
                "design_system": self.god_tier_design_system(task),
                "3d_and_motion_guidelines": "Motion is purposeful and premium. 3D is used for delight + clarity (diamond ownership, hashrate energy, channel flow), never for decoration that hurts perf or accessibility. Always provide static + reduced-motion variants.",
                "crypto_payments_aesthetics": "Trust + clarity first. Glass + subtle 3D for configurators. Clear states (intent, confirming, on-chain confirmed, failed). High contrast for numbers and addresses. Never hide fees or important on-chain info.",
                "hacash_visual_language": "Futuristic but grounded (cyan/violet accents on deep dark, glass, excellent mono for addresses). Scarcity and precision for diamonds/HAC. Live data feels alive but calm (subtle pulses, not flashing).",
                "accessibility_as_design": "WCAG 2.2 AA baked into every token and component spec. Contrast, focus, touch targets, reduced motion — non-negotiable in the design system.",
                "handoff_artifacts": "Full Figma (or equivalent) + tokens.json + component specs + 3D mood references + mobile breakpoint examples + interaction specs for payments and on-chain updates."
            },
            "handoffs": "website_builder.god_tier_build_modern_website, react_specialist.god_tier, threejs_expert.god_tier, mobile_responsive_expert.god_tier, programmer for any custom visual logic, crypto_payments for payment UI patterns, all hacash_* for explorer semantics.",
            "god_tier_level": "The design makes the technical excellence visible and trustworthy. Clients feel they got a $100k+ design system even on smaller scopes because of the rigor and reusability."
        }
        print("🎨 Designer (GOD TIER): God-like design system + direction delivered.")
        return god

    def god_tier_design_system(self, project: str) -> Dict[str, Any]:
        """The living design system spec (tokens + components + 3D + motion + a11y) that every other specialist consumes."""
        tokens = self.generate_design_tokens(self.create_color_palette(project), project)
        return {
            "tokens": tokens,
            "typography": self.generate_typography_scale(),
            "shadows_and_motion": (tokens.get("shadows", {}) if isinstance(tokens, dict) else {}) | {"motion": {"spring": "cubic-bezier(0.23, 1, 0.32, 1)"}},
            "3d_guidelines": "Use 3D to communicate value, ownership, flow, or energy. Keep poly count and texture budgets explicit. Provide static fallback in every spec.",
            "component_primitives": "Button, Card (glass), Input (address/tx), Table (virtualized for explorers), Modal, Toast, Toggle (for 3D quality), Progress (for payments/settlements). All with a11y and mobile variants built-in.",
            "hacash_crypto_specific": "Address mono always, amount emphasis, state badges (L1 settled / L2 updating / HVM executed), scarcity indicators for HACD.",
            "a11y_contract": "4.5:1 minimum (body 7:1 on dark). 44px+ targets. Focus visible. Reduced motion default for heavy animations/3D. Screen reader support documented per component."
        }

    def god_tier_accessible_and_inclusive_design(self) -> List[str]:
        """Non-negotiable god-tier accessibility and inclusivity rules."""
        return [
            "WCAG 2.2 AA minimum, AAA contrast where possible",
            "Full keyboard navigation + visible focus for every interactive element (including custom 3D controls)",
            "Respect prefers-reduced-motion at the token and component level",
            "Color is never the only indicator",
            "Touch targets 44-48px minimum, generous spacing on mobile",
            "High contrast mode support + forced-colors media query",
            "Live regions for dynamic on-chain / payment state updates",
            "Tested with VoiceOver + TalkBack on real devices"
        ]

# Register
designer = Designer()
print("🎨 Designer (GOD TIER) registered. Ready for sub_type='designer'. God-level design systems, 3D guidelines, mobile-first, crypto/Hacash aesthetics, a11y as foundation.")