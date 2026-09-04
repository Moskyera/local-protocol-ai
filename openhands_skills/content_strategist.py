"""
Content Strategist Skill for OpenHands
Professional Content Strategist & UX Copywriter.
Focus: User-centered messaging, SEO content, microcopy, information architecture, brand voice, conversion-focused writing.
"""

from logger import log
from typing import Dict, Any

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class ContentStrategist(ExpertSkill):
    """
    Senior Content Strategist and Copywriter for websites.
    Crafts words that guide users, build trust, and drive action.
    """

    def __init__(self):
        self.focus = "Content that makes beautiful websites actually convert and resonate."

    def create_content_strategy(self, task: str, context: Dict = None) -> Dict[str, Any]:
        log.info(f"ContentStrategist: Creating strategy for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " content strategy 2026", "UX writing best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "content_audit_framework": self.content_audit_framework(),
            "hero_and_messaging": self.hero_messaging_examples(task),
            "microcopy_guidelines": self.microcopy_guidelines(),
            "seo_content_structure": self.seo_content_structure(),
            "user_journey_mapping": "Awareness → Consideration → Decision → Retention",
            "research": research[:1000] if research else "Modern UX writing + voice & tone systems."
        }

        print("✍️ ContentStrategist: Professional content strategy delivered.")
        result["expert_analysis"] = self.consult(
            task, context,
            extra_system="You are a senior content strategist and UX copywriter focused on conversion and clarity.")
        self.mark_analysis(result)
        return result

    def content_audit_framework(self) -> list:
        return [
            "Clarity: Can a 12-year-old understand the main message?",
            "Scannability: Short paragraphs, bullets, bold key phrases",
            "Action-oriented: Every section has a clear next step",
            "Brand voice consistency across all touchpoints",
            "SEO: Target keywords naturally in H1/H2, first 100 words"
        ]

    def hero_messaging_examples(self, project: str) -> str:
        return f"""Hero examples for {project}:
- Headline: "Stunning 3D experiences, built for humans."
- Sub: "Professional modern websites that look incredible on every device."
- CTA: "See the work" or "Start your project"
"""

    def microcopy_guidelines(self) -> list:
        return [
            "Buttons: Action + benefit (\"Download free guide\" not \"Submit\")",
            "Error messages: Helpful + empathetic (\"We couldn't find that. Try again?\")",
            "Loading states: Reassuring (\"Preparing your 3D scene...\")",
            "Empty states: Encouraging + guiding"
        ]

    def seo_content_structure(self) -> str:
        return """Recommended page structure:
H1: Primary keyword + benefit
Intro: Hook + value prop
H2s: Problem, Solution, Features, Social proof, FAQ
Conclusion + strong CTA
"""

    # GOD-TIER DEEP METHODS
    def god_tier_create_content_strategy(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """GOD-LIKE: 10x content architecture — conversion, SEO, legal-safe, brand-aligned, measurable, crypto/Hacash aware."""
        log.info(f"ContentStrategist (GOD TIER): God-like content strategy for: {task[:60]}")
        base = self.create_content_strategy(task, context)
        god = {
            **base,
            "god_tier_additions": {
                "conversion_god": "Every piece of copy has a clear job: inform, build trust, reduce friction, drive action. A/B test plan tied to analytics-specialist.",
                "legal_safe_copy": "All claims defensible. No over-promising on returns, 'decentralized', security. Coordinate with legal_compliance_expert.god_tier.",
                "hacash_crypto_specific": "For explorers/pools/dapps: precise language on finality, peg mechanics, channel risks, diamond scarcity. Narratives that match tx_narrator style.",
                "3d_ui_copy": "Loading states, empty states, error messages, tooltips must guide users through complex 3D or on-chain flows without overwhelming.",
                "measurement": "Content contributes to LTV/ROI models. Track scroll depth, time-to-value, conversion per section via god-tier analytics.",
                "handoffs": "To brand_strategist.god_tier (voice consistency), website_builder.god_tier (implementation in React/3D), seo_expert (technical optimization), legal (compliance review), programmer (any dynamic copy logic).",
                "god_tier_level": "Content is not decoration. It is the interface between the product and the user's money, time, and trust. 10x teams treat it with the same rigor as code or architecture."
            }
        }
        print("✍️ ContentStrategist (GOD TIER): God-like content strategy delivered.")
        return god

    def god_tier_marketing_content_system(self, requirements: str) -> Dict[str, Any]:
        """ULTRA for full marketing: content as growth engine integrated with brand, seo, analytics, payments funnels."""
        return {
            "system": "Hero messaging → educational content (on-chain basics, Hacash advantages) → conversion content (case studies, ROI calculators) → retention (newsletters, on-chain activity narratives).",
            "funnels": "Tie directly to ecommerce_specialist and crypto_payments god-tier flows.",
            "god_tier": "Every asset is reusable across website, social, ads, Telegram (if used), explorers. Versioned, measurable, legally reviewed."
        }

# Register
content_strategist = ContentStrategist()
print("✍️ ContentStrategist (GOD TIER) registered. Ready for sub_type='content'. 10x content systems for conversion, trust and growth (incl. web3).")