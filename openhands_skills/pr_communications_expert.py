"""
PR & Communications Expert Skill for OpenHands - ULTRA GOD-LIKE
Institutional-grade Public Relations and Communications specialist for crypto, web3, websites, and Hacash projects.
Focus: Earned media, thought leadership, founder/brand narrative, crisis comms, conference strategy. Professional, compliant, relationship-driven. No hype, verifiable stories.
Critical for business: Must align with legal (no over-claims), marketing/brand (consistent voice), finance (credible economics narrative).
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


class PrCommunicationsExpert:
    """
    ULTRA GOD-LIKE PR & Communications Specialist.
    Builds credible, long-term reputation in crypto/web3 where trust is everything.
    10x: Media relationships (Tier-1 + crypto native), founder thought leadership, earned coverage, crisis preparedness, narrative that matches god-like delivery.
    Never hype. Always substance + proof. Coordinate with legal on every claim.
    """

    def __init__(self):
        self.focus = "Earning and protecting reputation through professional, transparent, high-signal communications - especially vital in crypto/Hacash."

    def god_tier_pr_strategy_and_narrative(self, project: str, include_crypto: bool = False, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Full PR strategy, narrative architecture, media plan, thought leadership calendar. Institutional crypto comms."""
        log.info(f"PrCommunicationsExpert (ULTRA GOD TIER): PR strategy for: {project[:60]}")

        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(project + " pr communications", max_results=2) or ""
            except Exception:
                pass

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(project + " crypto pr 2026", "best crypto web3 PR agencies strategies earned media 2026")
            except Exception:
                pass

        god = {
            "project": project,
            "god_tier_strategy": {
                "narrative_core": "Substance over hype. 'We deliver god-like professional results in complex domains (websites, payments, blockchain).' Proof: past work, metrics, client outcomes. Transparent about risks and conservative assumptions.",
                "positioning": "The quiet professionals who build what others promise. Credible, precise, future-proof.",
                "crypto_hacash_angle": "If include_hacash/crypto: Narrative around sound money + practical scaling (L2 channels), scarcity (diamonds), institutional readiness. Emphasize finality, compliance posture, real utility over speculation. Avoid 'next Ethereum' language.",
                "media_targets": "Crypto-native (CoinDesk, The Block, Decrypt, Blockworks) + mainstream finance (Bloomberg, Forbes, WSJ, FT). Developer/tech outlets for technical depth. Podcasts for founder voice.",
                "thought_leadership": "Founder/lead content calendar: deep technical posts, economic analysis, post-mortems (lessons learned), industry commentary. Data-backed, not opinion-only.",
                "earned_vs_paid": "Focus 80%+ on earned media through real relationships and newsworthy substance (launches with proof, research/reports, major integrations, transparent updates). Paid only for amplification of earned wins."
            },
            "god_tier_notes": "Crypto PR is relationship + credibility business. Journalists are skeptical after years of hype. Deliver proof, be responsive, never spin. Long-term reputation > short-term coverage. Crisis comms plan is non-negotiable.",
            "deliverables": "Full PR strategy + narrative bible, media list + relationships map, thought leadership calendar, press kit (bio, assets, one-pagers), crisis playbook, measurement framework (coverage quality, sentiment, inbound leads).",
            "handoffs": "To brand_strategist.god_tier + content_strategist.god_tier (voice/narrative consistency). To legal_compliance_expert.god_tier (every claim reviewed). To sales_bd_expert (PR supports pipeline). To finance (credible economics in stories). To project-manager (launch timing + proof points). To supervisor (god-mode on major announcements or crises).",
            "past_learnings_research": (past + " " + (research[:700] if research else ""))[:900]
        }
        print("📰 PrCommunicationsExpert (ULTRA GOD TIER): God-like PR strategy + narrative delivered.")
        return god

    def god_tier_media_outreach_and_launches(self, announcement: str) -> Dict[str, Any]:
        """GOD-LIKE: Pitch frameworks, launch playbooks, relationship nurturing. Professional crypto media engagement."""
        return {
            "announcement": announcement,
            "god_tier_pitch_framework": "Hook (newsworthy fact + proof), Context (why now, market gap), Our angle (god-like delivery + specifics), Proof (data, quotes, assets), Call to action (interview, exclusive). Personalized, short, value-first. Follow up once, then move on.",
            "launch_playbook": "Pre-launch: embargo list, briefing materials, founder prep. Launch day: coordinated drops, live support. Post: measurement, follow-up stories, community amplification.",
            "crisis_comms": "Preparation > reaction. Pre-drafted holding statements for common scenarios (hack, regulatory, delay, market crash). Single spokesperson. Legal + finance sign-off before any statement. Speed + transparency + action plan.",
            "god_tier_standards": "Every interaction builds long-term relationships. No spinning. Journalists remember accuracy and responsiveness. Coverage quality > quantity.",
            "handoffs": "To legal (review). To marketing (amplification). To PM (timing with delivery)."
        }

    def god_tier_team_pr_handoff_manifest(self, project: str) -> Dict[str, Any]:
        """GOD-LIKE: Manifest for PR integration."""
        return {
            "project": project,
            "mandatory": "PR involved early for narrative alignment. Major announcements gated by legal + PM + finance.",
            "calls": "god_tier_pr_strategy_and_narrative at positioning stage. god_tier_media_outreach... per launch or milestone.",
            "integration": "With brand/content (voice), legal (claims), sales (support), finance (numbers), PM (timing), supervisor (approvals).",
            "god_tier_caution": "Reputation is fragile in crypto. One over-claim or bad crisis response can undo years of god-like work. Ultra professional, substance-first, legally vetted."
        }

# Register
pr_communications_expert = PrCommunicationsExpert()
print("📰 PrCommunicationsExpert (ULTRA GOD TIER) registered. Ready for sub_type='pr'. Professional crypto/web3 PR - credibility, relationships, substance.")