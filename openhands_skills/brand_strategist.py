"""
Brand Strategist Skill for OpenHands
Professional Brand Strategist for serious client work.
Focus: Full brand identity development, visual guidelines, tone of voice, positioning, brand architecture, consistency across digital touchpoints.
For production websites that represent real businesses.
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


class BrandStrategist(ExpertSkill):
    """
    Senior Brand Strategist.
    Delivers complete, client-ready brand systems that guide design, content, and development.
    Used for serious professional projects.
    """

    def __init__(self):
        self.focus = "Creating cohesive, memorable, professional brand identities that elevate the website and the business behind it."

    def create_brand_strategy(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full brand strategy + guidelines + assets specs for the website project."""
        log.info(f"BrandStrategist: Creating brand strategy for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " brand strategy 2026", "professional brand identity best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "brand_audit_framework": self.brand_audit_framework(),
            "brand_positioning": self.brand_positioning_statement(task),
            "visual_identity_system": self.visual_identity_system(),
            "tone_of_voice": self.tone_of_voice_guide(),
            "brand_application_for_website": self.website_brand_application(),
            "deliverables_checklist": self.deliverables_checklist(),
            "research": research[:1300] if research else "2026 professional branding standards, consistency systems, and digital-first brand architecture."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("brand:strategy", f"{task} | professional brand system for client work")
            except Exception:
                pass

        print("🏷️ BrandStrategist: Complete professional brand strategy delivered (client-ready).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior brand strategist expert in positioning, identity and voice for serious (incl. web3) products.")
        self.mark_analysis(result)
        return result

    def brand_audit_framework(self) -> list:
        return [
            "Current brand perception vs desired positioning",
            "Competitor brand analysis (visual + verbal)",
            "Audience insights & brand archetypes",
            "Brand equity audit (awareness, loyalty, associations)",
            "Consistency gaps across existing touchpoints"
        ]

    def brand_positioning_statement(self, project: str) -> str:
        return f"""For [target audience] who [need], {project} is the [category] that [key benefit] because [reason to believe].
Brand archetype: [e.g. Creator / Ruler / Explorer]
Differentiation: Professional-grade modern experiences with depth and craft."""

    def visual_identity_system(self) -> Dict[str, Any]:
        return {
            "logo_usage": "Primary, secondary, monochrome, reversed. Clear space rules, minimum size, animation guidelines.",
            "color_system": "Primary palette (2-3 colors) + secondary + neutrals + semantic (success/error). Accessibility tested (WCAG AA).",
            "typography": "Primary display + body. Variable fonts preferred. Hierarchy, pairing rules, web fallbacks.",
            "imagery_style": "Photography direction, illustration style, 3D asset guidelines, motion principles.",
            "iconography": "Style, weight, grid, animation.",
            "patterns_textures": "Subtle backgrounds, dividers, 3D environment maps."
        }

    def tone_of_voice_guide(self) -> Dict[str, str]:
        return {
            "personality": "Professional yet approachable, confident, crafted, forward-thinking.",
            "do": "Clear, concise, benefit-focused, human, precise language.",
            "dont": "Jargon, hype, overly casual, passive voice, generic claims.",
            "examples": "Headline style, microcopy, error messages, CTAs, long-form."
        }

    def website_brand_application(self) -> list:
        return [
            "Hero & navigation: Brand expression at highest level",
            "Typography & color application in components",
            "3D/animation: How brand lives in motion and depth",
            "Content hierarchy aligned with brand voice",
            "Mobile: Brand consistency under thumb-first constraints",
            "Error/empty/loading states: On-brand micro-experiences"
        ]

    def deliverables_checklist(self) -> list:
        return [
            "Brand strategy document (positioning, archetype, values)",
            "Visual identity guidelines (PDF + Figma library)",
            "Tone of voice & writing guide",
            "Logo files + usage rules",
            "Color & type tokens (for devs)",
            "Imagery & 3D asset guidelines",
            "Component brand examples for website-builder",
            "Presentation deck for client sign-off"
        ]

    # GOD-TIER DEEP METHODS
    def god_tier_create_brand_strategy(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: 10x brand architecture with trade-offs, crypto/web3 specifics, full team handoffs, measurable positioning."""
        log.info(f"BrandStrategist (GOD TIER): God-like brand strategy for: {task[:60]}")
        base = self.create_brand_strategy(task, context)
        god = {
            **base,
            "god_tier_additions": {
                "10x_positioning": "Position for category leadership or defensible niche (e.g. 'the institutional-grade Hacash experience' or 'the most delightful 3D web3 onboarding').",
                "crypto_hacash_branding": "For blockchain projects: balance trust/scarcity (diamonds, pegs) with accessibility. Avoid 'crypto bro' tropes. Use precision, heritage, future-proof language.",
                "measurement": "Brand health metrics tied to analytics-specialist (awareness lift, consideration via on-site behavior, NPS).",
                "trade_offs": "Strong differentiation vs broad appeal. Premium feel vs load speed (3D assets). Global vs jurisdiction-specific voice.",
                "handoffs": "To designer.god_tier: visual system + 3D guidelines. To content_strategist.god_tier: voice in every microcopy. To website_builder.god_tier: brand application in 3D/React. To programmer: brand tokens in design system. To PM: brand sign-off as gate 1 deliverable.",
                "god_tier_level": "The brand system must survive 10x growth, regulatory scrutiny, and competitive attacks. Every touchpoint (including on-chain explorers or payment flows) must feel unmistakably 'on-brand'."
            }
        }
        print("🏷️ BrandStrategist (GOD TIER): God-like brand strategy delivered.")
        return god

    def god_tier_brand_for_crypto_and_hacash(self, requirements: str) -> Dict[str, Any]:
        """ULTRA for blockchain projects: specific positioning, trust signals, community vs institutional balance."""
        return {
            "positioning": "Heritage + precision + future (scarcity of HACD, soundness of L1, speed of L2).",
            "visual_trust": "Subtle gold/cyan accents for value, clean mono for technical credibility, 3D diamonds as hero without gimmick.",
            "voice": "Confident, transparent, never hype. 'We build the rails' not 'to the moon'.",
            "deliverables": "Brand book tailored for node operators, pool UIs, dapp frontends, explorer dashboards.",
            "handoff": "To all website + designer god-tier + hacash specialists for on-brand data viz."
        }

# Register
brand_strategist = BrandStrategist()
print("🏷️ BrandStrategist (GOD TIER) registered. Ready for sub_type='brand'. 10x brand systems for serious (incl. web3/Hacash) client work.")