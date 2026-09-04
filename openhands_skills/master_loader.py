"""
Master Loader Skill - Φορτώνει ΑΥΤΟΜΑΤΑ όλα τα custom skills με μία εντολή
"""

from logger import log

class MasterLoader:
    def load_all(self):
        """Φορτώνει όλα τα skills αυτόματα"""
        log.info("Master Loader: Loading all custom skills...")

        skills = [
            "self-improving-agent",
            "capability-evolver",
            "tx-narrator",
            "programmer-expert",      # Dedicated programmer agent for writing, refactoring, debugging + modern visuals (3D, animations, fonts...).
            "website-builder",        # Specialist for ANY modern website (unrelated to our theme OK). Rich visuals, animations, 3D, particles, custom fonts, glass etc.
            "code-researcher",        # GitHub + modern web tech researcher. Feeds fresh implementation ideas (libs, patterns) to programmer & website-builder.
            "designer",               # UI/UX + Visual Designer. Design systems, color, typography, aesthetics, mobile-first design, user experience flows.
            "threejs-expert",         # Deep Three.js / WebGL / 3D web specialist. Optimization, advanced scenes, performance, interactions for rich 3D.
            "react-specialist",       # Advanced React specialist. Patterns, performance, architecture, hooks, Next.js, state, component systems.
            "mobile-responsive-expert", # Mobile & Responsive specialist. Phone/tablet rendering, touch interactions, breakpoints, mobile performance, PWA aspects.
            "seo-expert",             # SEO Specialist. Technical SEO, on-page optimization, meta tags, structured data, search performance.
            "qa-engineer",            # QA / Testing Engineer. Automated tests, cross-browser/device testing, bug detection, quality assurance.
            "backend-specialist",     # Backend Specialist. APIs, databases, auth, server logic, data integration.
            "devops-engineer",        # DevOps Engineer. CI/CD, deployment (Vercel/AWS), monitoring, scaling, infrastructure.
            "accessibility-expert",   # Accessibility (A11y) Expert. WCAG compliance, ARIA, screen readers, inclusive design.
            "content-strategist",     # Content Strategist / Copywriter. UX writing, SEO content, messaging, user journeys, brand voice.
            "brand-strategist",       # Brand Strategist. Visual identity, brand guidelines, tone of voice, positioning for professional clients.
            "project-manager",        # Project Manager / Team Coordinator. Planning, task assignment, timelines, reviews, client handoff, risk management.
            "analytics-specialist",   # Analytics & Growth Specialist (DEEPER). Server-side/privacy tracking, advanced A/B + AI CRO, 3D events, attribution, LTV/ROI, custom dashboards.
            "legal-compliance-expert", # Legal & Compliance Specialist (GOD TIER). GDPR, privacy, terms, cookie consent, data protection, e-commerce law, IP. Deep god_tier methods for crypto/Hacash/web3.
            "brand-strategist", # Brand Strategist (GOD TIER). Visual identity, brand guidelines, tone of voice, positioning. god_tier for serious + crypto/Hacash projects.
            "content-strategist", # Content Strategist (GOD TIER). UX writing, SEO content, messaging, user journeys, brand voice. god_tier marketing content systems.
            "finance-treasury-expert", # Finance & Treasury Specialist (ULTRA GOD TIER). IPS, tokenomics modeling, DeFi treasury, liquidity, risk frameworks, on-chain ops. Extreme caution for crypto/Hacash business.
            "sales-bd-expert", # Sales & Business Development Specialist (ULTRA GOD TIER). Institutional BD, proposals, partnerships, pipeline for web3/crypto. Professional, data-driven, compliant.
            "product-strategist", # Product Strategist (ULTRA GOD TIER). Vision, roadmap, tokenomics-in-product, web3 iteration, community-driven. Distinct from PM; critical for economics.
            "pr-communications-expert", # PR & Communications Specialist (ULTRA GOD TIER). Earned media, thought leadership, crisis, narrative for crypto/web3. Substance over hype, legally vetted.
            "web3-community-manager", # Web3 Community Manager (ULTRA GOD TIER). Governance, incentives, token launches, on-chain engagement, retention. Professional, aligned with legal/finance.
            "illustration-3d-asset-specialist", # 3D Asset & Illustration Specialist. Creation, optimization, and web delivery of 3D models and custom illustrations (performance-first).
            "maintenance-support-specialist", # Maintenance & Support Specialist. Post-launch monitoring, updates, security, client training, and ongoing care.
            "security-auditor", # Security Auditor. OWASP, penetration testing mindset, secure coding, auth hardening, vulnerability assessment for production sites.
            "ecommerce-specialist",  # module is ecommerce_specialist.py — "e-commerce" resolved to nothing # E-commerce Specialist (SPECIFIC GATEWAYS). Stripe (detailed Elements/Intents/webhooks/Radar + React+3D), PayPal, Apple/Google Pay, local; + crypto-payments-expert for on-chain.
            "crypto-payments-expert", # Crypto Payments Expert (SPECIFIC). Stripe Crypto, Coinbase, custom web3; React+3D snippets; explicit cpp-expert integration for heavy computation; KYC/AML, security.
            "hacash-mining-expert", # Hacash Mining Expert. X16RS algorithm, PoW for HAC/HACD diamonds, GPU/CPU mining, pools, PoWorker, ASIC resistance.
            "hacash-fullnode-expert", # Hacash Fullnode Expert. Rust full node architecture (X16RS, Core, Chain, Mint, Node, Server, Miner), RPC API, running nodes, layer integration.
            "hacash-hvm-expert", # Hacash HVM Expert. Hacash Virtual Machine for smart contracts, multi-language, account abstraction, state optimization, DeFi/BTCFi on Hacash.
            "hacash-l1-expert", # Hacash L1 Expert. Layer 1 money system, HAC/HACD/BTC one-way peg, settlement, readable contracts, privacy, equity accounts.
            "hacash-l2-expert", # Hacash L2 Expert. Layer 2 channel chain payment settlement network, CSP (Channel Service Provider), large-scale instant HAC/BTC payments.
            "hacash-l3-expert", # Hacash L3 Expert. Layer 3 application ecosystem, Rollups, multi-chain protocols, DApps scaling on L1/L2.
            "typescript-expert", # TypeScript Specialist. Advanced TS patterns, type safety, performance, modern frontend architecture (React/Next).
            "python-expert", # Python Specialist. Backend (FastAPI/Django), scripting, data processing, AI integrations, high-quality Python code.
            "cpp-expert", # C++ Specialist. High-performance computing, 3D engines, WASM, low-level optimizations, performance-critical components.
            "large-codebase-master",
            "pr-review-expert",
            "tool-integration-hub",
            "debugging-expert",
            "machine-learning-pro",
            "security-guardian",
            "prompt-optimizer",
            "docs-onboarding",
            "git-cicd-pro",
            "smart_trigger_system",
            "multi_agent_orchestrator_v2",
            "solidity-expert",
            "pulsechain-expert",
            "chain-analysis-expert",
            "openhands-v2-entry"
        ]

        # This loop used to print "   ✓ Loaded: <name>" for every entry and then
        # "ALL CUSTOM SKILLS ARE NOW ACTIVE AND READY!" — while importing
        # nothing at all. The tick was printed from the list, not from the
        # result of loading, so a missing or broken module reported success just
        # as loudly as a working one.
        # Declared once, never written. They were in the roster above, printing
        # a green tick on every load because the loop printed the name instead
        # of the result of importing it. No module exists for any of them.
        not_implemented = ["safe-research-wrapper", "contract-auditor", "onchain-monitor"]

        print("🔥 Master Loader: importing skills...")

        loaded, failed = [], []
        for skill in skills:
            module = skill.replace("-", "_")
            for candidate in (f"openhands_skills.{module}",
                              f"openhands_multiagent_v2.{module}",
                              module):
                try:
                    __import__(candidate)
                    loaded.append(skill)
                    print(f"   ✓ {skill}")
                    break
                except Exception:
                    continue
            else:
                failed.append(skill)
                print(f"   ✗ {skill}  (no importable module)")

        print(f"\n{len(loaded)} of {len(skills)} skills imported.")
        if failed:
            print(f"FAILED TO IMPORT: {', '.join(failed)}")
            print("Those have a module that did not load. They will not respond to a trigger.")
        if not_implemented:
            print(f"NOT IMPLEMENTED: {', '.join(not_implemented)} "
                  f"(named in the roster, no module was ever written)")

        return {
            "loaded": loaded,
            "failed": failed,
            "not_implemented": not_implemented,
            "all_available": not failed,
            "summary": f"{len(loaded)}/{len(skills)} skills imported",
        }

# Register
master_loader = MasterLoader()