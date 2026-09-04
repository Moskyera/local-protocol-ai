"""
Product Strategist Expert Skill for OpenHands - ULTRA GOD-LIKE
Institutional-grade Product Manager/Strategist for web3, crypto, websites, and Hacash projects.
Focus: Product vision, roadmap, prioritization, user research, tokenomics-in-product, rapid web3 iteration, community-driven development. Distinct from Project Manager (execution).
Critical for business: Must balance user value, business goals, technical feasibility, legal/compliance, and economic models. Extreme caution in crypto (no over-promising, governance, incentives).
"""

from logger import log
from typing import Dict, Any, List, Optional

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class ProductStrategist:
    """
    ULTRA GOD-LIKE Product Strategist.
    Owns the 'what and why' at the highest level. Web3-native: speed of iteration, community as stakeholder, tokenomics as product, decentralized roadmaps.
    10x: Mission-driven, owner mindset, deep user empathy, craft for quality, bold but responsible.
    Integrates tightly with PM (handoff to execution), legal (compliance), finance (economics), marketing (positioning), all specialists.
    """

    def __init__(self):
        self.focus = "Defining products that users love, businesses sustain, and regulators respect - especially in complex crypto/Hacash environments."

    def god_tier_product_vision_and_roadmap(self, project: str, include_hacash: bool = False, include_web3: bool = True) -> Dict[str, Any]:
        """GOD-LIKE: Full product vision, strategy, prioritized roadmap. Web3 principles applied rigorously."""
        log.info(f"ProductStrategist (ULTRA GOD TIER): Vision/roadmap for: {project[:60]}")

        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(project + " product strategy", max_results=2) or ""
            except Exception:
                pass

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(project + " web3 product management 2026", "web3 product management principles iteration community tokenomics 2026")
            except Exception:
                pass

        god = {
            "project": project,
            "god_tier_vision": {
                "core_principles": "Deep user empathy (on-chain behavior + interviews). Mission driven (real problem in money, ownership, coordination). Craft for quality (god-like UX even in complex flows). Be bold (innovate on Hacash strengths). Act like an owner (long-term, skin in game).",
                "web3_differences": "Speed of iteration beats perfect planning. Community is a core stakeholder (governance, feedback, incentives). Tokenomics is product (incentives, utility, value accrual). Decentralized roadmap (less top-down control, more signaling + coordination).",
                "hacash_specific": "If include_hacash: Leverage L1 soundness + L2 speed + diamond scarcity as product differentiators. Product features around finality, channels, HVM contracts, mining participation, peg UX. Avoid EVM copy-paste; design for Hacash primitives (readable contracts, equity accounts).",
                "positioning": "The product that makes advanced blockchain feel simple, trustworthy, and delightful. 'Professional tools with consumer-grade experience.'"
            },
            "god_tier_roadmap": {
                "framework": "Discovery (user research, on-chain data, competitive) → Prioritization (RICE + strategic fit + risk/compliance) → Phased roadmap (MVP with core value, expansion, platform). Quarterly OKRs tied to business (retention, volume, treasury health).",
                "prioritization_god": "User value + business impact + technical feasibility + legal/compliance risk + economic sustainability. Always model token/user incentives. Kill features that don't move north-star metrics or create unmanageable risk.",
                "iteration": "Rapid prototypes, on-chain experiments (with safeguards), community signaling. 'Ship, measure, learn' - but with god-like quality bar and conservative risk controls in finance features.",
                "metrics": "North star (e.g., active value secured or user LTV). Leading: activation, retention, feature adoption. Lagging: revenue, treasury yield, governance participation. Tie to analytics-specialist."
            },
            "god_tier_notes": "In web3, product is strategy + incentives + UX + economics. 10x PMs own the full picture and protect users from complexity while delivering real ownership/value. Never ship something that could harm users financially without extreme safeguards.",
            "deliverables": "Product vision doc (1-pager + detailed), prioritized roadmap (Notion/Jira + visual), user research synthesis + persona, feature spec templates, OKR framework, community feedback integration process.",
            "handoffs": "To project-manager.god_tier (execution, gates). To programmer/website_builder (detailed specs). To legal_compliance_expert.god_tier (compliance in features). To finance_treasury_expert.god_tier (tokenomics/economics). To sales_bd_expert (market fit validation). To brand/content (messaging alignment). To supervisor (god-mode on major product bets).",
            "past_learnings_research": (past + " " + (research[:700] if research else ""))[:900]
        }
        print("📦 ProductStrategist (ULTRA GOD TIER): God-like vision + roadmap delivered.")
        return god

    def god_tier_tokenomics_and_incentives_in_product(self, requirements: str, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Deep integration of economics/incentives into product design. Ultra careful for crypto."""
        return {
            "requirements": requirements,
            "god_tier_approach": "Tokenomics is not bolted on - it is core product. Design incentives that align users, protocol, and treasury. Model second/third order effects. Conservative assumptions only.",
            "hacash_specific": "HAC for fees/settlement utility. HACD for scarcity/ownership signaling. L2 channels for instant UX. Mining as participation incentive. Peg for trust bridge. Product features that make these intuitive and valuable without over-promising yields or returns.",
            "best_practices": "Clear utility first. Fair launch/distribution where possible. Vesting/cliff for team/treasury. Governance that actually matters (not theater). Incentives that reward long-term behavior. Regular audits of economic assumptions.",
            "caution": "Financial incentives can destroy products if misdesigned. Always model bear cases. Coordinate with finance (modeling) and legal (securities risk). No 'to the moon' language.",
            "deliverables": "Incentive design doc + models, user journey with economic touchpoints, governance proposal templates, monitoring dashboard spec (via analytics).",
            "handoffs": "finance_treasury_expert.god_tier (full modeling). legal (compliance). programmer (on-chain implementation). community_manager (governance rollout)."
        }

    def god_tier_team_product_handoff_manifest(self, project: str) -> Dict[str, Any]:
        """GOD-LIKE: Manifest for integrating product strategy with the full god-like team."""
        return {
            "project": project,
            "mandatory": "Product strategist owns vision/roadmap/prioritization. Hands off to PM + specialists for execution. Revisit on major learnings or market shifts.",
            "calls": "god_tier_product_vision_and_roadmap at start. god_tier_tokenomics... for any economic features. Re-run on pivots.",
            "integration": "With PM (gates), all technical specialists (specs), legal/finance (risk), marketing (positioning), sales (market validation), supervisor (god-mode bets).",
            "god_tier_caution": "Product decisions in business/finance/crypto have real money and user trust at stake. Ultra careful, data + empathy driven, conservative where money is involved."
        }

# Register
product_strategist = ProductStrategist()
print("📦 ProductStrategist (ULTRA GOD TIER) registered. Ready for sub_type='product'. Web3-native product strategy with extreme care on economics and user value.")