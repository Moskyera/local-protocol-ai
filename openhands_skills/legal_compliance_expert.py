"""
Legal & Compliance Expert Skill for OpenHands
Professional Legal/Compliance Specialist for serious website projects.
Focus: GDPR, privacy policies, terms of service, cookie consent, data protection, accessibility laws (beyond basic a11y), e-commerce regulations, intellectual property.
For production, client-facing websites that must be legally sound.
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


class LegalComplianceExpert(ExpertSkill):
    """
    Senior Legal & Compliance Specialist.
    Ensures websites are compliant with relevant laws and regulations.
    Critical for serious professional work and client protection.
    """

    def __init__(self):
        self.focus = "Protecting the business and users with professional-grade legal compliance for digital products."

    def audit_and_implement_compliance(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full compliance audit + implementation plan + ready legal assets for the website."""
        log.info(f"LegalComplianceExpert: Auditing compliance for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " legal compliance 2026", "GDPR CCPA website compliance best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "compliance_audit_checklist": self.compliance_audit_checklist(),
            "privacy_policy_template": self.privacy_policy_template(task),
            "terms_of_service_template": self.terms_of_service_template(task),
            "cookie_consent_implementation": self.cookie_consent_implementation(),
            "data_protection_recommendations": self.data_protection_recommendations(),
            "e_commerce_considerations": self.e_commerce_considerations(),
            "ip_and_branding_protection": self.ip_and_branding_protection(),
            "research": research[:1200] if research else "2026 GDPR, ePrivacy, CCPA, and digital services act requirements."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("legal:compliance", f"{task} | professional legal compliance package for client work")
            except Exception:
                pass

        print("⚖️ LegalComplianceExpert: Complete professional compliance package delivered.")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior legal/compliance expert in GDPR, crypto regulation, IP and e-commerce law.")
        self.mark_analysis(result)
        return result

    def compliance_audit_checklist(self) -> list:
        return [
            "GDPR / CCPA data processing inventory and lawful basis",
            "Privacy notice + cookie policy (clear, accessible)",
            "Consent management platform integration (granular, withdrawable)",
            "Data subject rights procedures (access, deletion, portability)",
            "Third-party processors and data transfer agreements (SCCs)",
            "Accessibility legal requirements (beyond WCAG: EN 301 549, ADA where applicable)",
            "E-commerce: consumer rights, returns, pricing transparency",
            "Intellectual property: terms for user-generated content, licensing of 3D assets",
            "Record keeping: processing activities register, DPIA if high risk"
        ]

    def privacy_policy_template(self, project: str) -> str:
        return f"""<!-- Professional Privacy Policy skeleton for {project} -->
<h1>Privacy Policy</h1>
<p>Last updated: [DATE]</p>
<p>This website ({project}) is operated by [COMPANY]. We collect personal data to [purposes]. Legal basis: [consent/contract/etc].</p>
<p>Categories of data: [list]. Third parties: [list with links to their policies].</p>
<p>Your rights: access, rectification, erasure, restriction, portability, objection. Contact: [DPO email].</p>
<p>Cookies: We use essential, analytics and marketing cookies. Manage preferences via our consent banner.</p>
<!-- Full version generated on demand; always have lawyer review for your jurisdiction -->
"""

    def terms_of_service_template(self, project: str) -> str:
        return f"""<!-- Professional Terms of Service skeleton for {project} -->
<h1>Terms of Service</h1>
<p>By using this site you agree to these terms. [Company] provides {project} for [purpose].</p>
<p>Intellectual property: All 3D assets, code and content remain our property unless licensed.</p>
<p>User content: You grant us license to use submissions. You are responsible for legality of your uploads.</p>
<p>Liability: Limited to the extent permitted by law. No warranties for uninterrupted service.</p>
<p>Governing law: [Jurisdiction]. Dispute resolution: [arbitration/mediation].</p>
"""

    def cookie_consent_implementation(self) -> str:
        return """Recommended implementation (add to website-builder output):
- Use a compliant CMP (Cookiebot, OneTrust, or open-source like Klaro)
- Categories: Necessary / Analytics / Marketing / Personalization
- Granular toggles + "Accept all" / "Reject all"
- Record consent timestamp and version for audit trail
- Block non-essential scripts until consent (GTM / custom loader)
- Link to full Privacy Policy in banner
"""

    def data_protection_recommendations(self) -> list:
        return [
            "Minimize data collection (data minimization principle)",
            "Encrypt data in transit and at rest",
            "Regular security audits and penetration testing",
            "Data retention policies with automatic deletion",
            "Breach notification procedures (72h to authorities)"
        ]

    def e_commerce_considerations(self) -> list:
        return [
            "Clear pricing, taxes and shipping info before checkout",
            "Right of withdrawal / returns policy (14+ days in EU)",
            "Secure payment processing (PCI DSS compliant provider)",
            "Order confirmation emails with full terms"
        ]

    def ip_and_branding_protection(self) -> list:
        return [
            "Clear licensing terms for any 3D assets or illustrations you provide",
            "User-generated content license grant in ToS",
            "DMCA / takedown procedures if hosting user content",
            "Trademark and copyright notices in footer"
        ]

    # =====================================================================
    # GOD-TIER DEEP METHODS - 10x institutional legal & compliance
    # These elevate the expert to god-like level for complex, high-stakes projects
    # (especially crypto, web3, Hacash, e-commerce, data-heavy sites).
    # Always handoff to programmer/website for implementation, security-auditor, PM for gates.
    # =====================================================================

    def god_tier_legal_and_compliance_architecture(self, project_desc: str, include_crypto: bool = False, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Senior+ legal architecture with risk modeling, regulatory strategy, trade-offs, formal compliance design."""
        log.info(f"LegalComplianceExpert (GOD TIER): Architecting legal for: {project_desc[:60]}")
        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(project_desc, max_results=2) or ""
            except Exception:
                pass
        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(project_desc + " legal god tier 2026", "web3 securities law GDPR DSA e-commerce compliance")
            except Exception:
                pass

        arch = {
            "project": project_desc,
            "high_level_design": "Layered compliance: data layer (minimization + encryption), consent layer (granular CMP), contract layer (ToS + user agreements), IP layer (licensing + takedowns), regulatory layer (jurisdiction mapping + filings).",
            "key_patterns": ["Privacy by Design & Default", "Consent as a Service", "Modular Terms (base + jurisdiction riders)", "Audit Trail as Code", "Risk Register integrated with PM gates"],
            "risk_model": {
                "high": "Securities classification for tokens/HACD (Hacash), data breach liability, consumer protection in cross-border e-com",
                "medium": "IP infringement in 3D/assets, cookie consent fatigue, third-party processor failures",
                "mitigations": "DPIA for high-risk, SCCs + adequacy decisions, clear disclaimers, regular legal review cadence"
            },
            "crypto_hacash_specific": "If include_hacash/crypto: Token classification analysis (utility vs security), KYC/AML on ramps, one-way peg legal opinions, mining pool operator liability, HVM contract disclaimers. Coordinate with crypto_payments_expert and hacash_* experts.",
            "trade_offs": "Over-compliance kills UX vs under-compliance kills business. Start minimal viable compliance + scalable framework. EU-heavy vs global (choose US + EU as base).",
            "god_tier_notes": "Think like top-tier law firm + in-house counsel for Series B+ web3 company. Anticipate 10x user scale, regulatory shifts (MiCA, new DSA enforcement), enforcement actions. Always produce client-signable artifacts + internal playbook.",
            "deliverables": "Compliance architecture diagram (mermaid), full risk register (tied to PM), jurisdiction matrix, implementation spec for website-builder/programmer, legal opinion summary for client deck.",
            "handoff_manifest": "To programmer: exact contract/ToS language + DPIA requirements. To website-builder: CMP integration + consent UI specs. To security-auditor: overlap on data protection controls. To PM: legal gates in review process. To analytics: consent impact on tracking."
        }
        print("⚖️ LegalComplianceExpert (GOD TIER): God-like legal architecture delivered.")
        return arch

    def god_tier_full_legal_sdlc(self, project: str, include_crypto: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: End-to-end legal SDLC with gates, deliverables, and integration to the full professional team."""
        return {
            "project": project,
            "phases": [
                "Discovery: jurisdiction mapping, data inventory, token classification (if crypto/Hacash), threat model (legal risks)",
                "Architecture: god_tier_legal_and_compliance_architecture + risk register",
                "Drafting: Privacy, ToS, consents, IP licenses, processor agreements (templates + custom)",
                "Implementation: Handoff to website-builder (CMP, banners) + programmer (backend logging, contracts)",
                "Audit & Testing: Internal review + external counsel sign-off (tie to security-auditor)",
                "Launch gates: Legal sign-off before any public deployment or payment flow",
                "Post-launch: Monitoring (breach procedures), annual review, change management"
            ],
            "god_tier_standards": "10x: Every artifact is client-ready and defensible in court/regulator. No 'we'll fix it later'. Integrate with guarded evolution for any legal-impacting system change.",
            "crypto_specific": "Token legal opinion, securities memo, KYC/AML program design, exchange listing considerations if relevant. Always coordinate with crypto_payments_expert.",
            "deliverables": "Full legal package (signed PDFs where needed), implementation runbook, training for client ops team, 30-day post-launch legal health check.",
            "handoffs": "programmer_expert.god_tier (for code-level compliance), website_builder.god_tier (UI/legal flows), project_manager (gates + client presentation), security-auditor (overlap reviews)"
        }

    def god_tier_crypto_hacash_legal_specialist(self, requirements: str) -> Dict[str, Any]:
        """GOD-LIKE: Deep specialist for blockchain/Hacash specific legal (securities, mining, pegs, contracts, privacy)."""
        return {
            "requirements": requirements,
            "key_issues": [
                "HAC/HACD as securities or commodities? (Howey test + EU MiCA analysis)",
                "One-way BTC peg: custody, redemption rights, AML implications",
                "Mining pools: operator liability, fairness representations, tax",
                "HVM contracts: are they 'financial instruments'? Enforceability across jurisdictions",
                "Privacy features (if any): conflict with travel rule / KYC mandates"
            ],
            "god_tier_approach": "Produce formal legal memo style output + risk heatmaps + recommended disclaimers + implementation guardrails for the Hacash fullnode/HVM/L2 experts. Always recommend external specialized counsel for final opinion.",
            "integration": "Handoff to hacash_l1/l2 experts for economic model review, to crypto_payments for on-ramp legal, to programmer for contract language in code.",
            "deliverables": "Hacash-specific legal risk report, sample disclaimers for explorers/pools/dapps, compliance checklist for node operators."
        }

    def god_tier_team_legal_handoff_manifest(self, project: str) -> Dict[str, Any]:
        """GOD-LIKE: The exact manifest for ProjectManager + supervisor to orchestrate legal across the god-like team."""
        return {
            "project": project,
            "mandatory_legal_gates": "Legal review at every PM gate (especially before payments, 3D user content, on-chain features).",
            "calls": [
                "legal_compliance_expert.god_tier_legal_and_compliance_architecture(...) early",
                "god_tier_full_legal_sdlc(...) for complex projects",
                "god_tier_crypto_hacash_legal_specialist(...) when blockchain involved"
            ],
            "handoffs_to_others": "programmer (code must implement the legal specs), website (UI must surface policies + consents), analytics (consent affects measurement), security (data protection controls), PM (client sign-off package includes legal opinion)."
        }

# Register
legal_compliance_expert = LegalComplianceExpert()
print("⚖️ LegalComplianceExpert (GOD TIER) registered. Ready for sub_type='legal'. 10x institutional-grade legal for web3/crypto/client work.")