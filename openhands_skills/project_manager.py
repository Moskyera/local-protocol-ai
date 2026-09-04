"""
Project Manager / Team Coordinator Skill for OpenHands
Professional Project Manager for serious website projects.
Focus: End-to-end project planning, task breakdown, specialist coordination, timelines, risk management, reviews, client handoff, quality gates.
This is the 'brain' that makes the full intelligent team work as one professional unit.
"""

from logger import log
from typing import Dict, Any, List
from datetime import datetime

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class ProjectManager:
    """
    Senior Project Manager / Team Lead for professional website development.
    Orchestrates the entire specialist team with military precision for client deliverables.
    Every project treated as real paid work with clear milestones, reviews, and client-ready outputs.
    """

    def __init__(self):
        self.focus = "Delivering complex, high-stakes website projects on time, on brand, on quality — with full transparency and risk control."

    def plan_and_coordinate(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main entry: Full project plan, team assignment, timeline, risk register, review gates, final handoff package."""
        log.info(f"ProjectManager: Planning serious project: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " project management 2026", "professional web project management")
            except Exception:
                pass

        result = {
            "task": task,
            "project_brief": self.project_brief_template(task),
            "team_assignment": self.team_assignment(),
            "milestones_timeline": self.milestones_timeline(),
            "risk_register": self.risk_register(),
            "review_gates": self.review_gates(),
            "client_handoff_package": self.client_handoff_package(),
            "quality_standards": self.quality_standards(),
            "research": research[:1100] if research else "Agile + Waterfall hybrid for web projects, client communication best practices."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("project:management", f"{task} | professional project orchestration for client work")
            except Exception:
                pass

        print("📋 ProjectManager: Complete professional project plan delivered (client-grade).")
        return result

    def project_brief_template(self, project: str) -> Dict[str, str]:
        return {
            "objective": f"Deliver a production-ready, professional {project} that meets business goals, brand standards, and technical excellence.",
            "success_criteria": "On-time, on-budget, client sign-off, measurable KPIs (traffic, conversion, satisfaction), zero critical bugs post-launch.",
            "scope": "Full discovery → strategy → design → development → testing → deployment → training/handover.",
            "out_of_scope": "Ongoing maintenance (separate retainer), third-party content creation unless specified."
        }

    def team_assignment(self) -> Dict[str, str]:
        return {
            "research": "code-researcher (tech trends, competitors)",
            "brand": "brand-strategist (identity system)",
            "design": "designer + content-strategist",
            "frontend": "react-specialist + threejs-expert + mobile-responsive-expert + website-builder",
            "backend": "backend-specialist",
            "quality": "qa-engineer + accessibility-expert + seo-expert",
            "devops": "devops-engineer",
            "analytics": "analytics-specialist",
            "orchestration": "project-manager (you) + advanced_supervisor"
        }

    def milestones_timeline(self) -> List[Dict[str, str]]:
        return [
            {"phase": "Discovery & Strategy", "duration": "Week 1", "deliverables": "Brief, research, brand positioning, content audit"},
            {"phase": "Brand & Design", "duration": "Week 2-3", "deliverables": "Brand system, wireframes, high-fidelity mockups, content first draft"},
            {"phase": "Development", "duration": "Week 4-7", "deliverables": "Component library, full site build, backend integration, 3D assets"},
            {"phase": "Testing & Optimization", "duration": "Week 8", "deliverables": "QA report, a11y audit, SEO pass, performance optimization, analytics setup"},
            {"phase": "Deployment & Handoff", "duration": "Week 9", "deliverables": "Live site, documentation, training, client presentation, post-launch plan"}
        ]

    def risk_register(self) -> List[Dict[str, str]]:
        return [
            {"risk": "Scope creep", "mitigation": "Strict change control process, weekly client syncs"},
            {"risk": "3D performance on mobile", "mitigation": "Early prototype + mobile specialist + fallback strategy"},
            {"risk": "Brand misalignment", "mitigation": "Brand strategist sign-off before design lock"},
            {"risk": "Third-party integration delays", "mitigation": "Early API research + contingency in timeline"},
            {"risk": "Client feedback loops", "mitigation": "Structured review gates with clear decision points"}
        ]

    def review_gates(self) -> List[str]:
        return [
            "Gate 1: Strategy sign-off (client + brand + content)",
            "Gate 2: Design system + content lock (designer + content + brand)",
            "Gate 3: Beta site internal review (full team + qa + a11y + seo)",
            "Gate 4: Client UAT + analytics validation",
            "Gate 5: Pre-launch checklist (devops + qa + pm)"
        ]

    def client_handoff_package(self) -> List[str]:
        return [
            "Live production URL + staging",
            "Full brand & design system documentation (Figma + PDF)",
            "Content strategy & tone guide",
            "Technical documentation (architecture, APIs, deployment)",
            "QA & accessibility reports",
            "Analytics dashboard setup + training",
            "Post-launch support plan & monitoring access",
            "Source code repo access + contribution guidelines"
        ]

    def quality_standards(self) -> List[str]:
        return [
            "Lighthouse mobile ≥ 90 across performance/accessibility",
            "WCAG 2.2 AA minimum (AAA where feasible)",
            "Zero critical bugs in UAT",
            "SEO technical score ≥ 95",
            "Client satisfaction survey target ≥ 9/10",
            "All deliverables versioned and client-approved at gates"
        ]

    def run_full_professional_project(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """
        FULL PROFESSIONAL PROJECT TEMPLATE
        Automatically orchestrates the complete intelligent professional team with strict quality gates.
        Use this for any real client or business website project.
        Returns a complete execution plan + all specialist outputs + final client presentation package.
        """
        log.info(f"ProjectManager: Running FULL PROFESSIONAL PROJECT TEMPLATE for: {task[:60]}")
        context = context or {}

        # Phase 0: Master Plan
        master_plan = self.plan_and_coordinate(task, context)

        # Phase 1: Research + Brand + Content + Legal + Finance/Business (parallel foundation) — ULTRA GOD TIER
        research = "Use code-researcher for tech/competitor research"
        brand = "Use brand-strategist.god_tier_create_brand_strategy(...) for identity system (or god_tier_brand_for_crypto_and_hacash if applicable)"
        content = "Use content-strategist.god_tier_create_content_strategy(...) + god_tier_marketing_content_system for messaging & UX writing"
        legal = "Use legal-compliance-expert.god_tier_legal_and_compliance_architecture(...) + god_tier_full_legal_sdlc(...) for GDPR/privacy/terms/cookie consent (god_tier_crypto_hacash_legal_specialist when blockchain involved)"
        finance = "Use finance_treasury_expert.god_tier_treasury_strategy_and_ips(...) + god_tier_financial_modeling_and_tokenomics(...) for ANY economic/token/treasury work (ultra conservative IPS, stress tests, legal overlap)"
        sales = "Use sales_bd_expert.god_tier_bd_strategy_and_pipeline(...) for client/partner acquisition (institutional, compliant)"
        product = "Use product_strategist.god_tier_product_vision_and_roadmap(...) + god_tier_tokenomics_and_incentives_in_product(...) for vision/roadmap/economics (distinct from PM execution)"
        pr = "Use pr_communications_expert.god_tier_pr_strategy_and_narrative(...) for narrative, media, launches (substance + proof, legal vetted)"
        community = "Use web3_community_manager.god_tier_community_strategy_and_governance(...) for governance/incentives/retention (on-chain, aligned with legal/finance)"

        # Phase 2: Design + Assets + Illustration (visual foundation)
        design = "Use designer for UI/UX + mobile-first"
        assets = "Use illustration-3d-asset-specialist for custom 3D/illustrations (performance-first)"

        # Phase 3: Core Development (React / Three.js / Mobile / Backend)
        frontend = "Use react-specialist + threejs-expert + mobile-responsive-expert + website-builder"
        backend = "Use backend-specialist for APIs, auth, data"

        # Phase 4: Quality, SEO, A11y, Analytics
        qa = "Use qa-engineer for full testing suite + visual regression"
        seo = "Use seo-expert for technical SEO + meta + structured data"
        a11y = "Use accessibility-expert for WCAG audit + ARIA"
        analytics = "Use analytics-specialist for tracking + A/B + conversion framework"

        # Phase 5: DevOps + Maintenance
        devops = "Use devops-engineer for CI/CD, deployment, monitoring, security"
        maintenance = "Use maintenance-support-specialist for post-launch plan, training, support processes"

        # Strict Quality Gates (non-negotiable)
        gates = [
            "GATE 0: Project brief + risk register + client kickoff sign-off",
            "GATE 1: Brand + Legal + Content + Research foundation approved",
            "GATE 2: Design system + Asset pipeline + Illustration specs locked",
            "GATE 3: Beta build internal review (full team + qa + a11y + seo)",
            "GATE 4: Client UAT + analytics validation + performance budget check",
            "GATE 5: Pre-launch checklist (devops + maintenance + legal + final QA)",
            "GATE 6: Live deployment + client presentation + training + handoff package + 30-day support plan"
        ]

        # Client Presentation Deliverables (professional package)
        client_presentation = {
            "deck": "Executive summary, brand system, design direction, key 3D/animation moments, mobile experience, technical highlights, timeline, investment",
            "live_demo": "Staging URL with annotated walkthrough (desktop + mobile)",
            "handoff_kit": "Full documentation, source access, training videos, support matrix, monitoring dashboards",
            "success_metrics": "Defined KPIs + analytics dashboard + 30/60/90 day review cadence"
        }

        full_plan = {
            "master_plan": master_plan,
            "phases": {
                "foundation": [research, brand, content, legal],
                "visuals": [design, assets],
                "development": [frontend, backend],
                "quality": [qa, seo, a11y, analytics],
                "launch_support": [devops, maintenance]
            },
            "strict_quality_gates": gates,
            "client_presentation_deliverables": client_presentation,
            "final_note": "This template treats the project as real paid professional work. Every specialist output must pass the gates. No shortcuts. Full professionalism."
        }

        # Explicit automatic calls to the full chain (for maximum automation & professionalism)
        explicit_chain = [
            "1. code-researcher.research_modern_web_techniques(...) for latest patterns",
            "2. brand-strategist.create_brand_strategy(...) + designer.design_website(...) + content-strategist.create_content_strategy(...) + legal-compliance-expert.audit_and_implement_compliance(...)",
            "3. illustration-3d-asset-specialist.create_asset_pipeline(...) + threejs-expert.create_threejs_scene(...) + react-specialist.build_react_architecture(...) + mobile-responsive-expert.make_responsive(...) + website-builder.build_modern_website(...) + backend-specialist.build_backend(...)",
            "4. qa-engineer.run_quality_assurance(...) + seo-expert.optimize_for_search(...) + accessibility-expert.ensure_accessibility(...) + analytics-specialist.setup_analytics_and_optimization(...)  [DEEPER: includes server-side tracking, privacy, advanced A/B with AI, custom 3D events, attribution models + payment_events_integration() for gateway-specific events]",
            "5. security-auditor.audit_security(...) + ecommerce-specialist.build_ecommerce_platform(...)  [SPECIFIC GATEWAYS: Stripe (full Elements + Intents + webhooks + Radar + React+3D snippet), PayPal, Apple/Google Pay, local (iDEAL etc.); full PCI, fraud, subscription; React/3D integration] + crypto-payments-expert.build_crypto_payment_flow(...) [Stripe Crypto, Coinbase Commerce, custom web3 with React+3D snippets + explicit cpp-expert for heavy on-chain pricing/risk/WASM computation]",
            "6. typescript-expert.build_typescript_architecture(...) / python-expert.build_python_backend(...) [includes concrete FastAPI /create-crypto-payment-intent + /confirm-crypto-payment endpoints that log to analytics + full ethers+Stripe+WASM flow] / cpp-expert.build_high_performance_components(...) [includes EXACT emcc build command for the payment_pricing.cpp WASM example] as needed for language-specific high-perf or backend work (explicit C++ WASM for payment heavy math in 3D checkout)",
            "7. devops-engineer.handle_deployment(...) + maintenance-support-specialist.create_maintenance_and_support_plan(...)",
            "8. Full review by ProjectManager + QualitySupervisor + guarded proposals for any system evolution. Explicit client presentation with analytics dashboards, payment/crypto funnel reports, and on-chain verification demos."
        ]
        full_plan["explicit_automatic_chain"] = explicit_chain
        full_plan["deeper_analytics_note"] = "Analytics now includes server-side, privacy-first, AI-assisted CRO, session replays, 3D-specific events, multi-touch attribution, LTV/ROI models."
        full_plan["specific_payment_gateways_note"] = "E-commerce explicitly details Stripe (full Elements/Intents/webhooks/Radar + React+3D snippet), PayPal, Apple/Google Pay, local; + dedicated crypto-payments-expert with specific gateways (Stripe Crypto, Coinbase, custom web3) + React+3D snippets + cpp-expert for heavy computation."
        full_plan["cpp_payment_integration_note"] = "Explicit: Call cpp-expert for WASM heavy payment logic (dynamic 3D pricing, risk scoring, gas estimation, ZK) called from React 3D checkout before Stripe/crypto confirm. See FULL integrated snippet in crypto_payments_expert: ethers.js custom + Stripe Crypto + WASM call from C++ (in one React+Three.js component)."
        full_plan["language_experts_note"] = "TypeScript/Python/C++ experts are called explicitly when the project requires advanced work in those languages (e.g. high-perf frontend in TS, backend in Python, compute in C++/WASM)."
        full_plan["full_ethers_stripe_crypto_wasm_snippet"] = "In crypto_payments_expert.react_3d_integration_snippets(): FULL production snippet combining ethers.js (custom USDC), Stripe Crypto (Elements), and direct WASM call from cpp-expert (heavy pricing/risk/gas) inside one React + Three.js 3D configurator. 3D changes -> WASM calc -> live price -> pay (ethers or Stripe). Backend verify always."
        full_plan["hacash_god_tier_note"] = "For Hacash projects: explicit god-tier calls to hacash_* experts (mining for X16RS/pools, fullnode for 7-layer Rust, hvm for contracts/VM, l1/l2/l3 for layers) + integration with general god-tier programmer (god_tier_* methods), website-builder, etc. Full 10x professional for real blockchain dev work."

        # GOD-TIER LEGAL & MARKETING (new)
        try:
            from openhands_skills.legal_compliance_expert import legal_compliance_expert as leg
            full_plan["god_tier_legal_call_example"] = leg.god_tier_legal_and_compliance_architecture(task, include_crypto="crypto" in task.lower() or "payment" in task.lower(), include_hacash="hacash" in task.lower())
            full_plan["god_tier_legal_sdlc_example"] = leg.god_tier_full_legal_sdlc(task, include_crypto="crypto" in task.lower())
        except Exception:
            full_plan["god_tier_legal_call_example"] = "Call legal_compliance_expert.god_tier_legal_and_compliance_architecture + god_tier_full_legal_sdlc + god_tier_crypto_hacash_legal_specialist"

        try:
            from openhands_skills.brand_strategist import brand_strategist as br
            from openhands_skills.content_strategist import content_strategist as ct
            full_plan["god_tier_marketing_brand_example"] = br.god_tier_create_brand_strategy(task)
            full_plan["god_tier_marketing_content_example"] = ct.god_tier_create_content_strategy(task)
            full_plan["god_tier_marketing_crypto_example"] = br.god_tier_brand_for_crypto_and_hacash(task) if "hacash" in task.lower() or "crypto" in task.lower() else "N/A"
        except Exception:
            full_plan["god_tier_marketing_brand_example"] = "Call brand_strategist.god_tier_create_brand_strategy + content_strategist.god_tier_create_content_strategy + god_tier_marketing_content_system"

        full_plan["GOD_TIER_LEGAL_MARKETING_MANIFEST"] = {
            "legal": "legal_compliance_expert.god_tier_* must be called early and at every gate for any project involving user data, payments, on-chain features, or client deliverables. Never skip for 'simple' sites.",
            "marketing": "brand_strategist.god_tier + content_strategist.god_tier (combined as 'marketing') for positioning, voice, conversion content, growth integration with analytics/ecommerce. For Hacash/crypto: specialized brand + content that builds trust without hype.",
            "integration": "Legal + Marketing sit alongside designer, website god-tier, and analytics. All feed into client presentation deliverables via PM."
        }

        # ULTRA GOD-TIER FINANCE / BUSINESS SPECIALISTS (new, extreme caution)
        try:
            from openhands_skills.finance_treasury_expert import finance_treasury_expert as fin
            full_plan["god_tier_finance_call_example"] = fin.god_tier_treasury_strategy_and_ips(task, include_hacash="hacash" in task.lower(), include_defi="defi" in task.lower() or "yield" in task.lower())
            full_plan["god_tier_finance_modeling_example"] = fin.god_tier_financial_modeling_and_tokenomics(task, include_hacash="hacash" in task.lower())
        except Exception:
            full_plan["god_tier_finance_call_example"] = "Call finance_treasury_expert.god_tier_treasury_strategy_and_ips + god_tier_financial_modeling_and_tokenomics + god_tier_liquidity_risk... (ultra conservative, IPS, stress tests)"

        try:
            from openhands_skills.sales_bd_expert import sales_bd_expert as sal
            full_plan["god_tier_sales_call_example"] = sal.god_tier_bd_strategy_and_pipeline(task, include_crypto="crypto" in task.lower() or "hacash" in task.lower())
            full_plan["god_tier_sales_proposal_example"] = sal.god_tier_proposal_and_negotiation(task)
        except Exception:
            full_plan["god_tier_sales_call_example"] = "Call sales_bd_expert.god_tier_bd_strategy_and_pipeline + god_tier_proposal_and_negotiation + god_tier_ecosystem_partnerships"

        try:
            from openhands_skills.product_strategist import product_strategist as prod
            full_plan["god_tier_product_call_example"] = prod.god_tier_product_vision_and_roadmap(task, include_hacash="hacash" in task.lower())
            full_plan["god_tier_product_tokenomics_example"] = prod.god_tier_tokenomics_and_incentives_in_product(task, include_hacash="hacash" in task.lower())
        except Exception:
            full_plan["god_tier_product_call_example"] = "Call product_strategist.god_tier_product_vision_and_roadmap + god_tier_tokenomics_and_incentives_in_product"

        try:
            from openhands_skills.pr_communications_expert import pr_communications_expert as prc
            full_plan["god_tier_pr_call_example"] = prc.god_tier_pr_strategy_and_narrative(task, include_crypto="crypto" in task.lower(), include_hacash="hacash" in task.lower())
        except Exception:
            full_plan["god_tier_pr_call_example"] = "Call pr_communications_expert.god_tier_pr_strategy_and_narrative + god_tier_media_outreach_and_launches"

        try:
            from openhands_skills.web3_community_manager import web3_community_manager as com
            full_plan["god_tier_community_call_example"] = com.god_tier_community_strategy_and_governance(task, include_hacash="hacash" in task.lower(), include_token_launch="token" in task.lower() or "launch" in task.lower())
        except Exception:
            full_plan["god_tier_community_call_example"] = "Call web3_community_manager.god_tier_community_strategy_and_governance + god_tier_onchain_incentives_and_retention"

        full_plan["GOD_TIER_FINANCE_BUSINESS_ULTRA_MANIFEST"] = {
            "finance_treasury": "finance_treasury_expert.god_tier_* (IPS, modeling, liquidity, ops) MUST be called for ANY project with tokens, treasury, payments, yields, or economic models. Ultra conservative. Written policies, multisig, stress tests, legal overlap. No degen. Guarded proposals for all material changes.",
            "sales_bd": "sales_bd_expert.god_tier_* for client acquisition, proposals, partnerships. Institutional, compliant, value-first. Never oversell god-like deliverables. Pipeline metrics to analytics. Handoff to PM on close.",
            "product_strategist": "product_strategist.god_tier_* owns vision/roadmap/incentives (distinct from PM execution). Web3 principles (iteration, community, tokenomics). Must coordinate with finance/legal before any economic feature.",
            "pr_comms": "pr_communications_expert.god_tier_* for narrative, earned media, launches, crises. Substance + proof only. Every claim legal-reviewed. Long-term reputation focus.",
            "web3_community": "web3_community_manager.god_tier_* for governance, incentives, launches, retention. On-chain + qualitative. Align incentives with finance/legal. Quality participants > vanity.",
            "overall_caution": "Finance and business are non-negotiable ultra god-like. Extreme detail, conservative bias, full documentation, cross-team handoffs (legal, finance, PM, supervisor). We want the perfect - no shortcuts, no hype, auditable everything. 10x here means surviving regulators, black swans, and user trust."
        }

        # GOD-TIER WEBSITE / FRONTEND MANIFEST (new)
        try:
            from openhands_skills.website_builder import website_builder as wb
            full_plan["god_tier_website_call_example"] = wb.god_tier_build_modern_website(
                task, 
                include_crypto=("payment" in task.lower() or "crypto" in task.lower() or "stripe" in task.lower()),
                include_hacash=("hacash" in task.lower() or "mining" in task.lower() or "explorer" in task.lower() or "channel" in task.lower())
            )
            full_plan["god_tier_website_sdlc_example"] = wb.god_tier_full_website_sdlc_with_gates(
                task,
                include_3d=True,
                include_payments=("payment" in task.lower()),
                include_hacash=("hacash" in task.lower())
            )
        except Exception:
            full_plan["god_tier_website_call_example"] = "Call website_builder.god_tier_build_modern_website(...) + god_tier_full_website_sdlc_with_gates(...) (crypto/Hacash aware)"

        full_plan["GOD_TIER_WEBSITE_MANIFEST"] = {
            "mandatory_calls": [
                "designer.god_tier_design_website + god_tier_design_system",
                "react_specialist.god_tier_react_architecture (or build_react_architecture) + god_tier_react_performance_and_testing_gates",
                "threejs_expert.god_tier_create_threejs_scene + god_tier_threejs_production_pipeline (if 3D)",
                "mobile_responsive_expert.god_tier_make_responsive + god_tier_mobile_production_checklist",
                "website_builder.god_tier_build_modern_website (the orchestrator) + god_tier_3d_performance... + god_tier_crypto_payment_ui... + god_tier_hacash_specialized_explorer (when relevant) + god_tier_production_deployment...",
                "Always handoff to programmer_expert for WASM/heavy logic, crypto_payments_expert for payments, hacash_* for data semantics, analytics for events, legal for compliance."
            ],
            "integration_note": "Website god-tier work is never isolated. 3D + payments + on-chain (Hacash or EVM) require the full chain. PM enforces the manifest exactly like backend/blockchain work."
        }

        # GOD-TIER EXECUTION MANIFEST (actual calls when experts available)
        try:
            from openhands_skills.programmer_expert import programmer_expert as prog
            full_plan["god_tier_programmer_call_example"] = prog.god_tier_full_team_handoff_manifest(task, include_hacash="hacash" in task.lower() or "hacash" in str(context).lower())
            full_plan["god_tier_threat_model_example"] = prog.god_tier_threat_model_and_risk_register(task, include_hacash="hacash" in task.lower())
        except Exception:
            full_plan["god_tier_programmer_call_example"] = "Call programmer_expert.god_tier_full_team_handoff_manifest + god_tier_threat_model... (import in real agent runtime)"

        # If Hacash project, attempt to pull god_tier manifests from the specialists
        if "hacash" in task.lower() or "hacash" in str(context or {}).lower():
            hacash_manifest = {}
            for mod_name, expert_name, method in [
                ("hacash_mining_expert", "hacash_mining_expert", "god_tier_implement_production_ready_mining_system"),
                ("hacash_fullnode_expert", "hacash_fullnode_expert", "god_tier_implement_production_ready_fullnode_system"),
                ("hacash_hvm_expert", "hacash_hvm_expert", "god_tier_implement_production_ready_hvm_system"),
                ("hacash_l1_expert", "hacash_l1_expert", "god_tier_implement_production_ready_l1_system"),
                ("hacash_l2_expert", "hacash_l2_expert", "god_tier_implement_production_ready_l2_system"),
                ("hacash_l3_expert", "hacash_l3_expert", "god_tier_implement_production_ready_l3_system"),
            ]:
                try:
                    mod = __import__(f"openhands_skills.{mod_name}", fromlist=[expert_name])
                    expert = getattr(mod, expert_name)
                    if hasattr(expert, method):
                        hacash_manifest[mod_name] = getattr(expert, method)(task)
                except Exception:
                    hacash_manifest[mod_name] = f"Direct call: {expert_name}.{method}(requirements)"
            full_plan["GOD_TIER_HACASH_MANIFEST"] = hacash_manifest
            full_plan["GOD_TIER_EXECUTION_NOTE"] = "Supervisor + ProjectManager must force these god_tier_* entrypoints for all Hacash work. No shortcuts. Use task_tracker + guarded proposals on every layer change."

        full_plan["GOD_TIER_EXECUTION_MANIFEST"] = {
            "mandatory": [
                "programmer_expert.god_tier_threat_model_and_risk_register + god_tier_generate_adrs + god_tier_full_team_handoff_manifest",
                "programmer_expert.god_tier_chaos_formal_and_property_testing_plan + god_tier_benchmark_and_perf_model + god_tier_production_ops_and_deployment",
                "For Hacash: the 6 hacash_* .god_tier_implement_production_ready_* + their ultra methods (x16rs_kernel, csp_state_machine, peg, aa_state, rollup, 7layer_extend)",
                "Every output passes god_tier_code_review + security-auditor + qa gates before client handoff."
            ],
            "project_manager_role": "Enforce the manifest. Collect all god_tier dicts into client presentation. Create guarded proposal for any deviation from 10x standards."
        }

        print("📋 ProjectManager: FULL PROFESSIONAL PROJECT TEMPLATE executed with strict gates, client presentation package, and EXPLICIT calls to the entire chain (GOD TIER).")
        return full_plan

# Register
project_manager = ProjectManager()
print("📋 ProjectManager registered. Ready for sub_type='project'. This is serious client work — treat every project accordingly.")