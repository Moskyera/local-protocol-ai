"""
Advanced Supervisor v2.2 - Hierarchical + Programmer/Website Specialists
Enhanced live version with explicit support for sub_type="programmer" and sub_type="website".
Delegates implementation work to programmer_expert and website_builder (the specialists you requested).
Includes HandoffTool and integrates with safe wrappers + persistent memory.
"""

from logger import log
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


def _supervisor_llm(system_prompt: str, user_prompt: str,
                    temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Safe LLM call for real supervisor planning/synthesis.

    Returns '' on any failure so the legacy template fallbacks still work and
    orchestration never crashes because the backend is down.
    """
    try:
        from llm_client import chat, is_usable
        out = (chat(user_prompt, temperature=temperature,
                    max_tokens=max_tokens, system_prompt=system_prompt) or "").strip()
        # chat() RETURNS failure strings, it does not raise. Catching only
        # exceptions meant "(LLM error - check llama-server logs)" was published
        # under a "## 🎯 Execution plan" header, and as the final synthesis of a
        # "CYCLE COMPLETED" report — discarding the genuine template summary that
        # this function's own docstring promises as the fallback.
        if not is_usable(out):
            log.warning(f"[Supervisor] LLM returned a sentinel, using fallback: "
                        f"{out[:80]}")
            return ""
        return out
    except Exception as e:  # backend down / not wired
        log.warning(f"[Supervisor] LLM synthesis unavailable: {e}")
        return ""

# Import the new specialists (graceful fallback)
try:
    from openhands_skills.programmer_expert import programmer_expert
except Exception:
    programmer_expert = None

try:
    from openhands_skills.website_builder import website_builder
except Exception:
    website_builder = None

try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None

try:
    from openhands_skills.designer import designer
except Exception:
    designer = None

try:
    from openhands_skills.threejs_expert import threejs_expert
except Exception:
    threejs_expert = None

try:
    from openhands_skills.react_specialist import react_specialist
except Exception:
    react_specialist = None

try:
    from openhands_skills.mobile_responsive_expert import mobile_responsive_expert
except Exception:
    mobile_responsive_expert = None

try:
    from openhands_skills.seo_expert import seo_expert
except Exception:
    seo_expert = None

try:
    from openhands_skills.qa_engineer import qa_engineer
except Exception:
    qa_engineer = None

try:
    from openhands_skills.backend_specialist import backend_specialist
except Exception:
    backend_specialist = None

try:
    from openhands_skills.devops_engineer import devops_engineer
except Exception:
    devops_engineer = None

try:
    from openhands_skills.accessibility_expert import accessibility_expert
except Exception:
    accessibility_expert = None

try:
    from openhands_skills.content_strategist import content_strategist
except Exception:
    content_strategist = None

try:
    from openhands_skills.brand_strategist import brand_strategist
except Exception:
    brand_strategist = None

try:
    from openhands_skills.project_manager import project_manager
except Exception:
    project_manager = None

try:
    from openhands_skills.analytics_specialist import analytics_specialist
except Exception:
    analytics_specialist = None

try:
    from openhands_skills.legal_compliance_expert import legal_compliance_expert
except Exception:
    legal_compliance_expert = None

try:
    from openhands_skills.illustration_3d_asset_specialist import illustration_3d_asset_specialist
except Exception:
    illustration_3d_asset_specialist = None

try:
    from openhands_skills.maintenance_support_specialist import maintenance_support_specialist
except Exception:
    maintenance_support_specialist = None

try:
    from openhands_skills.security_auditor import security_auditor
except Exception:
    security_auditor = None

try:
    from openhands_skills.ecommerce_specialist import ecommerce_specialist
except Exception:
    ecommerce_specialist = None

try:
    from openhands_skills.typescript_expert import typescript_expert
except Exception:
    typescript_expert = None

try:
    from openhands_skills.python_expert import python_expert
except Exception:
    python_expert = None

try:
    from openhands_skills.cpp_expert import cpp_expert
except Exception:
    cpp_expert = None

try:
    from openhands_skills.crypto_payments_expert import crypto_payments_expert
except Exception:
    crypto_payments_expert = None

try:
    from openhands_skills.hacash_mining_expert import hacash_mining_expert
except Exception:
    hacash_mining_expert = None

try:
    from openhands_skills.hacash_fullnode_expert import hacash_fullnode_expert
except Exception:
    hacash_fullnode_expert = None

try:
    from openhands_skills.hacash_hvm_expert import hacash_hvm_expert
except Exception:
    hacash_hvm_expert = None

try:
    from openhands_skills.hacash_l1_expert import hacash_l1_expert
except Exception:
    hacash_l1_expert = None

try:
    from openhands_skills.hacash_l2_expert import hacash_l2_expert
except Exception:
    hacash_l2_expert = None

try:
    from openhands_skills.hacash_l3_expert import hacash_l3_expert
except Exception:
    hacash_l3_expert = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None

try:
    from safe_research_wrapper import safe_research_and_evolve, force_compact_summary
except Exception:
    safe_research_and_evolve = None
    force_compact_summary = None


class HandoffTool:
    """Explicit handoff for clean specialist-to-specialist communication (programmer ↔ website etc.)."""
    def __init__(self):
        self.handoff_log = []

    def handoff(self, from_agent: str, to_agent: str, task: str, context: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
        record = {
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "task": task,
            "context_keys": list(context.keys()) if context else [],
            "reason": reason
        }
        self.handoff_log.append(record)
        log.info(f"[HandoffTool] {from_agent} → {to_agent}: {task}")
        return {
            "status": "handed_off",
            "to_agent": to_agent,
            "task": task,
            "context": context,
            "handoff_id": len(self.handoff_log),
            "instructions_for_receiver": f"Continue '{task}'. Context provided. Reason: {reason}"
        }

    def get_recent_handoffs(self, limit: int = 5):
        return self.handoff_log[-limit:]


class AdvancedSupervisor:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mem_dir = os.path.join(base_dir, "memory")
        os.makedirs(mem_dir, exist_ok=True)
        self.memory_file = os.path.join(mem_dir, "supervisor_memory.json")
        self.load_memory()
        self.handoff_tool = HandoffTool()
        self.sub_supervisors = {}

    def load_memory(self):
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
        except:
            self.memory = {"past_tasks": [], "lessons": [], "hierarchical_plans": []}

    def save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False)

    def plan_and_orchestrate(self, user_task: str):
        log.info(f"Advanced Supervisor (hierarchical + specialists) planning: {user_task}")

        is_new = len(self.memory.get("past_tasks", [])) == 0
        greeting = "🆕 **New session** — initializing with empty memory.\n\n" if is_new else ""

        plan = f"""{greeting}🧠 Advanced Supervisor v2.3 (COMPLETE INTELLIGENT PROFESSIONAL WEBSITE TEAM)
Task: {user_task}

This is a **GOD-LIKE PROFESSIONAL TEAM** for real client work / business projects / serious blockchain dev (e.g. Hacash). Every specialist operates at god-tier/senior+ expert level (10x thinking, comprehensive, production-ready, with deep research/integration). The team is designed to be ready for ANY case: websites, full SDLC, Hacash mining/fullnode/HVM/L1/L2/L3, crypto payments, high-perf (C++/WASM), etc. No shortcuts - full professionalism, validation, gates, client-ready deliverables.

Top-level delegates to (full orchestration):
- ResearchSupervisor (safe bounded research + code-researcher for fresh 2026 tech)
- BrandStrategist (sub_type="brand") → Full brand identity, visual system, tone of voice, positioning
- Designer (sub_type="designer") → UI/UX, design systems, mobile-first aesthetics
- ContentStrategist (sub_type="content") → UX writing, messaging, SEO content, user journeys
- ThreeJSExpert (sub_type="threejs") → Deep 3D/WebGL, optimization, advanced scenes
- ReactSpecialist (sub_type="react") → Advanced React patterns, performance, architecture
- MobileResponsiveExpert (sub_type="mobile") → Phone/tablet rendering, touch, responsive strategies, mobile performance
- SEOExpert (sub_type="seo") → Technical SEO, meta, structured data, search optimization
- AccessibilityExpert (sub_type="a11y") → WCAG, ARIA, inclusive design, screen reader support
- BackendSpecialist (sub_type="backend") → APIs, DB, auth, server logic, data integration
- QAEngineer (sub_type="qa") → Testing, cross-browser/device QA, bug prevention, quality gates
- DevOpsEngineer (sub_type="devops") → CI/CD, deployment, monitoring, infrastructure, security hardening
- AnalyticsSpecialist (sub_type="analytics") → DEEPER tracking (server-side, privacy, AI CRO, 3D events, attribution, LTV/ROI, custom dashboards)
- LegalComplianceExpert (sub_type="legal") → GDPR, privacy, terms, cookie consent, data protection, e-commerce law, IP
- Illustration3DAssetSpecialist (sub_type="illustration") → Professional 3D models, illustrations, textures, and asset optimization (performance-first)
- MaintenanceSupportSpecialist (sub_type="maintenance") → Post-launch monitoring, updates, security patches, client training, and ongoing support
- SecurityAuditor (sub_type="security") → OWASP, secure coding audits, vulnerability assessment, hardening for production
- EcommerceSpecialist (sub_type="ecommerce") → SPECIFIC GATEWAYS: Stripe (Elements/Intents/webhooks/Radar detailed + React+3D snippet), PayPal, Apple/Google Pay, local; full PCI, fraud, React/3D integration, conversion
- CryptoPaymentsExpert (sub_type="crypto") → SPECIFIC: Stripe Crypto, Coinbase, custom web3; React+3D snippets + explicit cpp-expert for heavy on-chain pricing/risk/WASM; KYC/AML, security
- HacashMiningExpert (sub_type="hacash_mining") → X16RS PoW mining for HAC/HACD diamonds, GPU/CPU, pools, PoWorker, ASIC resistance, diamond mining
- HacashFullnodeExpert (sub_type="hacash_fullnode") → Rust full node (7-layer arch: X16RS/Core/Chain/Mint/Node/Server/Miner), RPC, running, layer integration
- HacashHVMExpert (sub_type="hacash_hvm") → Hacash Virtual Machine for smart contracts, multi-lang, account abstraction, state opt, DeFi/BTCFi, contract dev
- HacashL1Expert (sub_type="hacash_l1") → L1 money system, HAC/HACD/BTC peg, settlement, readable contracts, privacy, equity accounts
- HacashL2Expert (sub_type="hacash_l2") → L2 channel chain payments, CSP, large-scale instant HAC/BTC settlement network
- HacashL3Expert (sub_type="hacash_l3") → L3 apps/Rollups/multi-chain scaling, DApp ecosystem on L1/L2
- TypescriptExpert (sub_type="typescript") → Advanced TypeScript, type safety, modern frontend (React/Next) performance & patterns
- PythonExpert (sub_type="python") → Professional Python (FastAPI, backend, data, AI integrations, high-quality code)
- CppExpert (sub_type="cpp") → High-performance C++ (3D engines, WASM, low-level optimizations, compute-heavy components)
- ProjectManager (sub_type="project") → Full project orchestration: planning, task assignment, timelines, reviews, risk management, client-ready handoff, validation
- ProgrammerSupervisor → programmer_expert (code + modern visuals via add_modern_visuals)
- WebsiteBuilderSupervisor → website_builder (ANY modern website with rich 3D/animations/fonts/particles — theme independent!)
- QualitySupervisor + critics (final review, guarded proposals for any system change)

HandoffTool + debate + persistent memory + validation enabled at every step.
Every deliverable must be client-ready, tested, documented, performant, accessible, SEO-optimized, brand-aligned, and measurable.

The team treats every project as real business work — no shortcuts, full professionalism.
GOD-LIKE team: includes god-tier general programmer (god_tier_* methods for arch/review/optimize/SDLC), deepened specialists (deeper analytics, specific gateways, full ethers+Stripe+WASM + cpp), and Hacash domain experts (mining/fullnode/HVM/L1/L2/L3 with god_tier production systems). Ensures projects are legally sound, visually rich, e-commerce/crypto ready, high-perf in TS/Python/C++/Rust, and supported long after launch. Full template explicitly orchestrates with strict gates + 10x thinking. Ready for god-like professional output on any case.
"""
        # Real, task-specific execution plan via the model (the roster above is
        # now used as *context*, not as the answer).
        real_plan = _supervisor_llm(
            "You are a senior engineering lead. Produce a concise, concrete, "
            "step-by-step execution plan for the given task. For each step name "
            "the responsible specialist (coder, tester, reviewer, security, "
            "debugger, market_analyst). Include key risks and a clear "
            "definition-of-done. Be specific to THIS task — no generic filler.",
            f"Task:\n{user_task}\n\nAvailable specialists / context:\n{plan[:1600]}",
        )
        if real_plan:
            plan = (
                f"## 🎯 Execution plan — {user_task}\n{real_plan}\n\n"
                f"<details><summary>Full specialist roster</summary>\n\n{plan}\n</details>"
            )

        self.memory["past_tasks"].append({"timestamp": datetime.now().isoformat(), "task": user_task, "mode": "hierarchical+specialists"})
        self.save_memory()
        return plan

    def delegate_to_sub_supervisor(self, sub_task: str, sub_type: str = "orchestration", context: Optional[Dict] = None):
        """Hierarchical delegation for a COMPLETE INTELLIGENT PROFESSIONAL WEBSITE TEAM.
        Supported sub_types include all the above plus:
        - 'brand': Brand strategy, identity, guidelines, positioning (professional client work)
        - 'project': Project management, planning, coordination, reviews, risk management, client handoff
        - 'analytics': Analytics setup, A/B testing, conversion optimization, data insights, ROI
        - 'legal': GDPR, privacy, terms, cookie consent, data protection, IP, e-commerce law
        - 'illustration': Custom 3D assets, illustrations, textures, and optimization (performance-first)
        - 'maintenance': Post-launch monitoring, updates, security, client training, ongoing support
        - 'security': OWASP audits, secure coding, vulnerability assessment, hardening
        - 'ecommerce': Payments, carts, checkout, PCI, taxes, e-commerce conversion (SPECIFIC gateways with React+3D)
        - 'crypto': Crypto payments (Stripe Crypto, Coinbase, custom web3; React+3D snippets + cpp-expert for heavy computation; KYC/AML)
        - 'hacash_mining': Hacash X16RS PoW mining, pools, GPU/CPU, diamonds
        - 'hacash_fullnode': Hacash Rust full node, 7-layer arch, RPC, layers
        - 'hacash_hvm': Hacash HVM smart contracts, VM, multi-lang, account abstraction
        - 'hacash_l1': Hacash L1 money/settlement/peg/contracts
        - 'hacash_l2': Hacash L2 channel chain payments/CSP
        - 'hacash_l3': Hacash L3 apps/Rollups/scaling
        - 'typescript': Advanced TS, type safety, modern React/Next frontend
        - 'python': Professional Python backend, FastAPI, data, AI integrations
        - 'cpp': High-performance C++, WASM, 3D engines, low-level optimizations (explicit for payment heavy math)
        This team is built for serious, real-world business projects — every specialist is senior-level, every step includes validation, testing, documentation, and client-readiness. Hacash specialists enable deep work on the Hacash Rust codebase, HVM contracts, mining, layered architecture for building nodes, tools, contracts, explorers, websites etc.
        'code_researcher' feeds fresh GitHub + modern web tech (3D, framer, fonts, particles...) to the coders.
        'programmer' and 'website' get direct access to the experts (and can request research).
        """
        context = context or {}

        if sub_type == "programmer" and programmer_expert:
            log.info("[Hierarchical] Delegating to PROGRAMMER_EXPERT")
            try:
                result = programmer_expert.implement_feature(sub_task, files_context=str(context)[:2000])
                # Record
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "programmer", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "programmer_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"programmer_expert delegation failed: {e}")

        if sub_type == "website" and website_builder:
            log.info("[Hierarchical] Delegating to WEBSITE_BUILDER")
            try:
                result = website_builder.build_pulsechain_explorer(sub_task) if "pulse" in sub_task.lower() or "explorer" in sub_task.lower() else website_builder.build_modern_website(sub_task)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "website", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "website_builder", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"website_builder delegation failed: {e}")

        if sub_type == "code_researcher" and code_researcher:
            log.info("[Hierarchical] Delegating to CODE_RESEARCHER (fresh GitHub + modern visuals)")
            try:
                result = code_researcher.research_modern_web_techniques(sub_task) if "web" in sub_task.lower() or "visual" in sub_task.lower() or "animation" in sub_task.lower() else code_researcher.get_github_code_ideas(sub_task)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "code_researcher", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "code_researcher", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"code_researcher delegation failed: {e}")

        if sub_type == "designer" and designer:
            log.info("[Hierarchical] Delegating to DESIGNER (UI/UX, aesthetics, mobile-first)")
            try:
                result = designer.design_website(task=sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "designer", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "designer", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"designer delegation failed: {e}")

        if sub_type == "threejs" and threejs_expert:
            log.info("[Hierarchical] Delegating to THREEJS_EXPERT (deep 3D/WebGL)")
            try:
                result = threejs_expert.create_threejs_scene(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "threejs", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "threejs_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"threejs_expert delegation failed: {e}")

        if sub_type == "react" and react_specialist:
            log.info("[Hierarchical] Delegating to REACT_SPECIALIST (advanced patterns & architecture)")
            try:
                result = react_specialist.build_react_architecture(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "react", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "react_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"react_specialist delegation failed: {e}")

        if sub_type == "mobile" and mobile_responsive_expert:
            log.info("[Hierarchical] Delegating to MOBILE_RESPONSIVE_EXPERT (phone/tablet rendering & UX)")
            try:
                result = mobile_responsive_expert.make_responsive(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "mobile", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "mobile_responsive_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"mobile_responsive_expert delegation failed: {e}")

        if sub_type == "seo" and seo_expert:
            log.info("[Hierarchical] Delegating to SEO_EXPERT (technical SEO & search optimization)")
            try:
                result = seo_expert.optimize_for_search(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "seo", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "seo_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"seo_expert delegation failed: {e}")

        if sub_type == "qa" and qa_engineer:
            log.info("[Hierarchical] Delegating to QA_ENGINEER (testing & quality assurance)")
            try:
                result = qa_engineer.run_quality_assurance(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "qa", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "qa_engineer", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"qa_engineer delegation failed: {e}")

        if sub_type == "backend" and backend_specialist:
            log.info("[Hierarchical] Delegating to BACKEND_SPECIALIST (APIs, data, auth)")
            try:
                result = backend_specialist.build_backend(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "backend", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "backend_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"backend_specialist delegation failed: {e}")

        if sub_type == "devops" and devops_engineer:
            log.info("[Hierarchical] Delegating to DEVOPS_ENGINEER (deployment, CI/CD, monitoring)")
            try:
                result = devops_engineer.handle_deployment(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "devops", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "devops_engineer", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"devops_engineer delegation failed: {e}")

        if sub_type == "a11y" and accessibility_expert:
            log.info("[Hierarchical] Delegating to ACCESSIBILITY_EXPERT (WCAG, inclusive design)")
            try:
                result = accessibility_expert.ensure_accessibility(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "a11y", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "accessibility_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"accessibility_expert delegation failed: {e}")

        if sub_type == "content" and content_strategist:
            log.info("[Hierarchical] Delegating to CONTENT_STRATEGIST (copy, UX writing, messaging)")
            try:
                result = content_strategist.create_content_strategy(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "content", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "content_strategist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"content_strategist delegation failed: {e}")

        if sub_type == "brand" and brand_strategist:
            log.info("[Hierarchical] Delegating to BRAND_STRATEGIST (identity, guidelines, positioning)")
            try:
                result = brand_strategist.create_brand_strategy(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "brand", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "brand_strategist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"brand_strategist delegation failed: {e}")

        if sub_type == "project" and project_manager:
            log.info("[Hierarchical] Delegating to PROJECT_MANAGER (full orchestration, planning, reviews, client handoff)")
            try:
                result = project_manager.plan_and_coordinate(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "project", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "project_manager", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"project_manager delegation failed: {e}")

        if sub_type == "analytics" and analytics_specialist:
            log.info("[Hierarchical] Delegating to ANALYTICS_SPECIALIST (tracking, A/B, conversion, ROI)")
            try:
                result = analytics_specialist.setup_analytics_and_optimization(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "analytics", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "analytics_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"analytics_specialist delegation failed: {e}")

        if sub_type == "legal" and legal_compliance_expert:
            log.info("[Hierarchical] Delegating to LEGAL_COMPLIANCE_EXPERT (GDPR, privacy, terms, IP)")
            try:
                result = legal_compliance_expert.audit_and_implement_compliance(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "legal", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "legal_compliance_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"legal_compliance_expert delegation failed: {e}")

        if sub_type == "illustration" and illustration_3d_asset_specialist:
            log.info("[Hierarchical] Delegating to ILLUSTRATION_3D_ASSET_SPECIALIST (custom 3D models & illustrations)")
            try:
                result = illustration_3d_asset_specialist.create_asset_pipeline(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "illustration", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "illustration_3d_asset_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"illustration_3d_asset_specialist delegation failed: {e}")

        if sub_type == "maintenance" and maintenance_support_specialist:
            log.info("[Hierarchical] Delegating to MAINTENANCE_SUPPORT_SPECIALIST (post-launch care & support)")
            try:
                result = maintenance_support_specialist.create_maintenance_and_support_plan(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "maintenance", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "maintenance_support_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"maintenance_support_specialist delegation failed: {e}")

        if sub_type == "security" and security_auditor:
            log.info("[Hierarchical] Delegating to SECURITY_AUDITOR (OWASP, hardening, vulnerability assessment)")
            try:
                result = security_auditor.audit_security(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "security", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "security_auditor", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"security_auditor delegation failed: {e}")

        if sub_type == "ecommerce" and ecommerce_specialist:
            log.info("[Hierarchical] Delegating to ECOMMERCE_SPECIALIST (payments, carts, PCI, conversion)")
            try:
                result = ecommerce_specialist.build_ecommerce_platform(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "ecommerce", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "ecommerce_specialist", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"ecommerce_specialist delegation failed: {e}")

        if sub_type == "typescript" and typescript_expert:
            log.info("[Hierarchical] Delegating to TYPESCRIPT_EXPERT (advanced TS, type safety, modern frontend)")
            try:
                result = typescript_expert.build_typescript_architecture(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "typescript", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "typescript_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"typescript_expert delegation failed: {e}")

        if sub_type == "python" and python_expert:
            log.info("[Hierarchical] Delegating to PYTHON_EXPERT (professional Python backend, AI, data)")
            try:
                result = python_expert.build_python_backend(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "python", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "python_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"python_expert delegation failed: {e}")

        if sub_type == "cpp" and cpp_expert:
            log.info("[Hierarchical] Delegating to CPP_EXPERT (high-performance C++, WASM, 3D engines)")
            try:
                result = cpp_expert.build_high_performance_components(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "cpp", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "cpp_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"cpp_expert delegation failed: {e}")

        if sub_type == "crypto" and crypto_payments_expert:
            log.info("[Hierarchical] Delegating to CRYPTO_PAYMENTS_EXPERT (specific gateways + React+3D + cpp integration)")
            try:
                result = crypto_payments_expert.build_crypto_payment_flow(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "crypto", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "crypto_payments_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"crypto_payments_expert delegation failed: {e}")

        if sub_type == "hacash_mining" and hacash_mining_expert:
            log.info("[Hierarchical] Delegating to HACASH_MINING_EXPERT (X16RS PoW, pools, GPU/CPU mining)")
            try:
                result = hacash_mining_expert.implement_mining_features(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_mining", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_mining_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_mining_expert delegation failed: {e}")

        if sub_type == "hacash_fullnode" and hacash_fullnode_expert:
            log.info("[Hierarchical] Delegating to HACASH_FULLNODE_EXPERT (Rust full node, RPC, layers)")
            try:
                result = hacash_fullnode_expert.implement_fullnode_features(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_fullnode", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_fullnode_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_fullnode_expert delegation failed: {e}")

        if sub_type == "hacash_hvm" and hacash_hvm_expert:
            log.info("[Hierarchical] Delegating to HACASH_HVM_EXPERT (HVM smart contracts, VM, multi-lang)")
            try:
                result = hacash_hvm_expert.implement_hvm_contracts(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_hvm", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_hvm_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_hvm_expert delegation failed: {e}")

        if sub_type == "hacash_l1" and hacash_l1_expert:
            log.info("[Hierarchical] Delegating to HACASH_L1_EXPERT (L1 money, peg, settlement)")
            try:
                result = hacash_l1_expert.implement_l1_features(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_l1", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_l1_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_l1_expert delegation failed: {e}")

        if sub_type == "hacash_l2" and hacash_l2_expert:
            log.info("[Hierarchical] Delegating to HACASH_L2_EXPERT (L2 channel chains, CSP)")
            try:
                result = hacash_l2_expert.implement_l2_features(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_l2", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_l2_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_l2_expert delegation failed: {e}")

        if sub_type == "hacash_l3" and hacash_l3_expert:
            log.info("[Hierarchical] Delegating to HACASH_L3_EXPERT (L3 Rollups, apps, scaling)")
            try:
                result = hacash_l3_expert.implement_l3_features(sub_task, context=context)
                self.memory.setdefault("hierarchical_plans", []).append({
                    "parent_task": sub_task, "sub_type": "hacash_l3", "timestamp": datetime.now().isoformat()
                })
                self.save_memory()
                return {"delegated_to": "hacash_l3_expert", "result": result, "handoff_ready": True}
            except Exception as e:
                log.warning(f"hacash_l3_expert delegation failed: {e}")

        # Fallback / other sub types → lightweight sub supervisor
        if sub_type not in self.sub_supervisors:
            self.sub_supervisors[sub_type] = AdvancedSupervisor()

        sub = self.sub_supervisors[sub_type]
        sub_plan = sub.plan_and_orchestrate(sub_task)

        self.memory.setdefault("hierarchical_plans", []).append({
            "parent_task": sub_task, "sub_type": sub_type, "timestamp": datetime.now().isoformat()
        })
        self.save_memory()

        return {"delegated_to": sub_type, "sub_plan": sub_plan, "handoff_ready": True}

    def handoff(self, from_agent: str, to_agent: str, task: str, context: Dict[str, Any], reason: str = "hierarchical delegation"):
        return self.handoff_tool.handoff(from_agent, to_agent, task, context, reason)

    def coordinate(self, results: Dict[str, Any]):
        log.info("Advanced Supervisor coordinating (with specialists + handoffs)")
        if "needs_handoff" in str(results).lower():
            h = self.handoff("primary", "specialist", "complex sub-task", results, "complexity")
            results["handoff_executed"] = h

        # Real synthesis of the actual sub-results (code / tests / review /
        # security / market / reflection) instead of just listing key names.
        synthesis = _supervisor_llm(
            "You are the lead engineer integrating a multi-agent run. Given the "
            "sub-results, produce a clear final report: (1) what was built, "
            "(2) the review + security findings that MUST be fixed — quote the "
            "concrete ones, (3) test status, (4) prioritised next steps. Use ONLY "
            "the information in the sub-results; do not invent anything.",
            "Sub-results:\n" + json.dumps(
                {k: self._clip(v, self._budget_for(k, 3000))
                 for k, v in results.items()},
                ensure_ascii=False, indent=2,
            ),
            max_tokens=4096,
        )
        if synthesis:
            return synthesis

        # Fallback (backend unavailable): keep the legacy summary so nothing breaks.
        summary = f"""🎯 Hierarchical + Specialists Coordination Complete
Sub-results: {list(results.keys())}
Handoffs: {len(self.handoff_tool.handoff_log)}
Lessons: {len(self.memory.get('lessons', []))}

(LLM synthesis unavailable — showing structural summary only.)
"""
        return summary

    #: Sub-results whose conclusion lives at the END. A security report states
    #: its verdict after the scan; a review lists its blockers after the
    #: walkthrough. Head-truncation removes exactly the part that matters.
    _VERDICT_KEYS = ("secur", "review", "audit", "test", "risk", "verdict")

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        """Keep the beginning AND the end, and say what was dropped.

        `str(v)[:3000]` kept the first 3000 characters and silently discarded
        the rest. Measured: security.audit returns 3778 characters and puts its
        verdict last, so the synthesis prompt — which asks the model to "quote
        the concrete security findings" — was handed the scan and not the
        conclusion, with nothing in the text to say so.
        """
        text = str(text)
        if len(text) <= limit:
            return text
        head = int(limit * 0.55)
        tail = limit - head
        dropped = len(text) - limit
        return (text[:head]
                + f"\n\n[... {dropped} characters omitted from the middle "
                  f"of this sub-result ...]\n\n"
                + text[-tail:])

    @classmethod
    def _budget_for(cls, key: str, base: int) -> int:
        """A verdict-bearing result gets more room than a narrative one."""
        return base * 2 if any(k in str(key).lower() for k in cls._VERDICT_KEYS) else base

    def debate_evolution(self, topic: str, max_results: int = 3):
        """#3 Multi-agent debate using sub-supervisors + handoff (researcher + critic)."""
        log.info(f"[Supervisor] debate_evolution for: {topic}")

        researcher = self.delegate_to_sub_supervisor(f"Research {topic} (bounded)", sub_type="research")
        critic = self.delegate_to_sub_supervisor(f"Critique proposal for {topic}", sub_type="critic")

        h = self.handoff("Researcher", "Critic", f"Review proposal: {topic}", {"research": researcher}, "debate for quality")

        refined = {
            "topic": topic,
            "researcher": researcher,
            "critic": critic,
            "handoff": h,
            "note": "Use safe_research_and_evolve for the final guarded version."
        }
        if persistent_memory:
            try:
                persistent_memory.store_learning(f"debate:{topic}", str(refined)[:1800])
            except Exception:
                pass
        return refined


# Register
advanced_supervisor = AdvancedSupervisor()
handoff_tool = advanced_supervisor.handoff_tool

def delegate_hierarchically(sub_task: str, sub_type: str = "orchestration"):
    return advanced_supervisor.delegate_to_sub_supervisor(sub_task, sub_type)

def perform_handoff(from_agent: str, to_agent: str, task: str, context: dict, reason: str = ""):
    return advanced_supervisor.handoff(from_agent, to_agent, task, context, reason)