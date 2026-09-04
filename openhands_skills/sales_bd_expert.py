"""
Sales & Business Development Expert Skill for OpenHands - ULTRA GOD-LIKE
Institutional-grade BD/sales specialist for serious client acquisition, partnerships, and revenue in web3, crypto, websites, and Hacash projects.
Focus: B2B/institutional pitching, god-tier proposals, pipeline, negotiation, ecosystem partnerships. Extreme professionalism - no hype, data-driven, relationship-first.
Critical for business side: Must align with legal (compliance in pitches), finance (deal economics), PM (delivery handoff), marketing (positioning).
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


class SalesBdExpert:
    """
    ULTRA GOD-LIKE Sales & Business Development Specialist.
    Closes the loop on god-like deliverables. Institutional standards for web3/crypto sales.
    10x: Relationship-driven, value-first, compliant, measurable pipeline, long-term ecosystem building.
    Never oversell. Always under-promise + over-deliver. Data + proof over hype.
    """

    def __init__(self):
        self.focus = "Turning exceptional god-like work into sustainable, high-quality client relationships and revenue. Especially in complex crypto/Hacash/web3 sales."

    def god_tier_bd_strategy_and_pipeline(self, project_or_firm: str, target_segments: List[str] = None, include_crypto: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Full BD strategy, ICP, pipeline architecture, outreach system. Institutional web3 sales playbook."""
        log.info(f"SalesBdExpert (ULTRA GOD TIER): BD strategy for: {project_or_firm[:60]}")
        target_segments = target_segments or ["institutional", "protocols", "enterprises", "high-net-worth projects"]

        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(project_or_firm + " sales bd", max_results=2) or ""
            except Exception:
                pass

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(project_or_firm + " web3 bd 2026", "institutional crypto business development best practices DeFi partnerships 2026")
            except Exception:
                pass

        god = {
            "project_or_firm": project_or_firm,
            "god_tier_strategy": {
                "icp": "Ideal Customer Profile: Decision-makers at protocols/DAOs with treasury >$5M, enterprises exploring blockchain, high-quality web3 projects needing god-like delivery (website + on-chain). Pain: unreliable vendors, hype without substance, compliance risks.",
                "positioning": "The institutional-grade partner who delivers flawless execution + measurable results. 'We build what others promise, with legal/finance rigor built in.'",
                "target_segments": target_segments,
                "crypto_hacash_focus": "If include_crypto: Target protocols needing treasury tools, explorers, payment rails, or fullnode/HVM integrations. Emphasize Hacash unique value (sound money + L2 speed + diamonds). Always lead with compliance + conservative economics.",
                "pipeline_architecture": "Stages: Awareness (content/thought leadership) → Qualification (ICP fit + budget) → Discovery (deep needs + god-tier demo) → Proposal (custom god-like package with legal/finance) → Negotiation/Close → Onboarding (handoff to PM + team). Metrics: Conversion rates, CAC, LTV, pipeline velocity.",
                "outreach_system": "Multi-channel: Warm intros > LinkedIn personalized > Twitter/Telegram value-first > Events/conferences. Always research (on-chain activity, recent news, team backgrounds). No spam. Value first (free audit snippet, treasury checklist, case study).",
                "god_tier_playbook": "Every pitch includes: Problem quantification, our god-like solution with proof (past deliverables, metrics), risk mitigation (legal, finance, security), commercial model (transparent, aligned incentives), timeline with gates, team bios + relevant experience."
            },
            "god_tier_notes": "Think like top enterprise BD at a16z portfolio or Tier-1 protocol. Long sales cycles in web3 (3-9 months). Focus on trust + proof. Institutional buyers care about risk, compliance, delivery reliability more than 'moon' narratives. Build relationships, not transactions.",
            "deliverables": "Full BD strategy doc, ICP + persona cards, pipeline CRM template (or spec for analytics), outreach sequences (email/LinkedIn/TG), pitch deck template (god-like, customizable), qualification scorecard, close playbook.",
            "handoffs": "To project-manager.god_tier (delivery excellence in proposals). To legal_compliance_expert.god_tier (compliance language in pitches). To finance_treasury_expert.god_tier (deal economics, treasury implications for client). To brand_strategist.god_tier + content_strategist.god_tier (positioning in materials). To analytics-specialist (pipeline tracking + ROI). To supervisor (god-mode for major BD decisions).",
            "past_learnings_research": (past + " " + (research[:700] if research else ""))[:900]
        }
        print("🤝 SalesBdExpert (ULTRA GOD TIER): God-like BD strategy + pipeline delivered.")
        return god

    def god_tier_proposal_and_negotiation(self, opportunity: str, client_type: str = "web3_protocol") -> Dict[str, Any]:
        """GOD-LIKE: Custom proposal creation, negotiation frameworks, term sheets, close mechanics. Data-driven, compliant, value-aligned."""
        return {
            "opportunity": opportunity,
            "god_tier_proposal_structure": "Executive summary (1 page), Problem/Opportunity (quantified), Our Solution (god-like deliverables with proof), Team & Track Record, Commercial Model (transparent pricing, milestones, success metrics), Timeline & Gates, Risk Mitigation (legal/finance/security), Next Steps.",
            "negotiation_framework": "Anchor on value + risk reduction. Use data (past results, benchmarks). Flexible on scope/timeline, firm on quality/legal/compliance. Win-win: align incentives (e.g., success fees tied to client KPIs). Always involve legal/finance early on material terms.",
            "crypto_specific": "For web3: Emphasize on-chain deliverables, treasury safety, regulatory posture. Token or stable pricing options with clear FX/risk handling. Governance participation if relevant. Never promise token performance.",
            "god_tier_standards": "Proposals are god-like artifacts themselves - professional, precise, beautiful, backed by data. Every claim verifiable. Negotiation protects both parties and sets up successful delivery.",
            "deliverables": "Proposal template + examples, negotiation script + objection handlers, term sheet template, close checklist, post-close onboarding spec (handoff to PM).",
            "handoffs": "project-manager (execution). legal (contract review). finance (pricing model). marketing/brand (consistent messaging). supervisor (approval on large deals)."
        }

    def god_tier_ecosystem_partnerships(self) -> Dict[str, Any]:
        """GOD-LIKE: Strategic partnerships for leverage (exchanges, custodians, infra providers, other protocols)."""
        return {
            "approach": "Value-first partnerships. Identify mutual upside (e.g., Hacash integration with payment rails, 3D website tools for other protocols). Co-marketing, revenue share, technical integration.",
            "god_tier_playbook": "Research target (on-chain activity, recent news, pain points). Warm intro preferred. Joint proposal with clear roles, success metrics, legal framework. Pilot before full commitment.",
            "crypto_hacash_angle": "Partnerships that enhance treasury (yield partners), liquidity (DEX/CEX), compliance (KYC providers), or user experience (wallets, explorers).",
            "caution": "Partnerships are long-term. Vet thoroughly (legal, security, financial stability of partner). Document everything. Re-evaluate quarterly.",
            "handoffs": "To legal (agreements). To finance (economics). To programmer (integration work). To PM (project-izing the partnership)."
        }

    def god_tier_team_sales_handoff_manifest(self, project: str) -> Dict[str, Any]:
        """GOD-LIKE: Manifest for PM/supervisor to integrate sales into the full god-like team."""
        return {
            "project": project,
            "mandatory": "Sales/BD involved from early positioning through proposal to close + handoff. Never sell what the team can't god-like deliver.",
            "calls": "god_tier_bd_strategy_and_pipeline early. god_tier_proposal_and_negotiation per opportunity. god_tier_ecosystem_partnerships for leverage.",
            "integration": "With project-manager (delivery promises), legal (compliance in sales), finance (deal structuring), marketing (positioning), supervisor (god-mode on major opportunities). Pipeline metrics feed analytics.",
            "god_tier_caution": "Business development is where reputation is won or lost. Be ultra professional, data-driven, and conservative in promises. Finance/business side demands perfection."
        }

# Register
sales_bd_expert = SalesBdExpert()
print("🤝 SalesBdExpert (ULTRA GOD TIER) registered. Ready for sub_type='sales'. Institutional web3/crypto BD - trust, data, long-term value.")