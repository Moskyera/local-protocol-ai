"""
Programmer Expert Skill for OpenHands
Dedicated professional programmer agent for writing, refactoring, debugging, and implementing code across languages.
Works with the hierarchical supervisor (sub_type="programmer"), guarded evolution, persistent memory, and all our standards.
Integrates with solidity_expert / pulsechain_expert when EVM/PulseChain code is involved.
"""

from logger import log
import re
from typing import Dict, Any, Optional, List

# Safe imports for composition
try:
    from openhands_skills.solidity_expert import solidity_expert
except Exception:
    solidity_expert = None

try:
    from openhands_skills.pulsechain_expert import pulsechain_expert
except Exception:
    pulsechain_expert = None

try:
    from persistent_memory import persistent_memory
except Exception:
    persistent_memory = None

# Code researcher for fresh modern frontend visuals / libs
try:
    from openhands_skills.code_researcher import code_researcher
except Exception:
    code_researcher = None


from openhands_skills.expert_base import ExpertSkill


class ProgrammerExpert(ExpertSkill):
    """
    Specialist programmer.
    Always follows project conventions:
    - Full task_tracker "plan" with complete task_list array (never missing)
    - Guarded evolution: write pending_proposals/*.json for any system change
    - Use safe_research_wrapper tools when doing meta work
    - Retrieve past learnings via persistent_memory
    - Prefer additive changes, no breaking existing behavior
    - High quality, documented, tested code
    """

    def __init__(self):
        self.supported_languages = ["python", "solidity", "javascript", "typescript", "bash", "powershell", "json", "markdown"]
        self.standards_note = """
PROJECT STANDARDS (MANDATORY):
- Use task_tracker with FULL task_list array: [{"id":1,"description":"...","status":"in_progress"}, ...]
- For any evolution of the agent/system: create guarded proposal JSON in pending_proposals/
- Always retrieve relevant past context: persistent_memory.retrieve_relevant_evolution(...)
- Prefer safe_research_and_evolve / force_compact_summary for research/meta tasks
- Never break existing features. Additive only unless explicitly asked.
- Use the HandoffTool when collaborating with other specialists.
"""

    def write_code(self, language: str, task: str, constraints: str = "", context: str = "") -> str:
        """Write clean, professional code for the given task and language."""
        lang = (language or "python").lower().strip()
        log.info(f"Programmer Expert: Writing {lang} code for: {task[:80]}")

        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(task, max_results=2) or ""
            except Exception:
                pass

        if lang in ("solidity", "evm"):
            if solidity_expert:
                return solidity_expert.write_solidity_contract(task, target_chain="pulsechain" if "pulse" in task.lower() else "ethereum")
            return self._solidity_stub(task)

        if lang in ("pulsechain", "pls"):
            if pulsechain_expert:
                return pulsechain_expert.generate_pulsechain_contract(task)
            return self._solidity_stub(task, chain="pulsechain")

        # Generic languages: real LLM code generation (was: static stubs).
        prior = f"\n\nRelevant past learnings:\n{past}" if past else ""
        cons = f"\n\nConstraints: {constraints}" if constraints else ""
        ctx = f"\n\nContext:\n{context}" if context else ""
        code = self.consult(
            f"Write complete, production-quality {lang} code for this task. Return "
            f"the code in a single fenced block, then a brief note on key "
            f"decisions.{cons}{ctx}{prior}\n\nTask: {task}",
            extra_system="You are a senior polyglot software engineer.",
            max_tokens=6000,
        )
        # If the backend is unavailable, fall back to the old deterministic stub
        # so callers still get something structured rather than an error string.
        if code.startswith("(expert '") or code.startswith("(LLM"):
            if lang in ("js", "javascript", "ts", "typescript", "react", "vite"):
                return self._web_code_stub(task, lang)
            if lang in ("bash", "powershell", "shell", "ps1"):
                return self._script_stub(task, lang)
            return self._python_code(task, constraints, past, context)
        return code

    def refactor_code(self, code: str, goals: str, language: str = "python") -> str:
        """Refactor existing code according to goals while preserving behavior."""
        log.info(f"Programmer Expert: Refactoring ({goals[:60]})")
        header = f"# REFACTORED by ProgrammerExpert\n# Goals: {goals}\n# Language: {language}\n\n"
        # In real use the agent would do precise str_replace; here we return improved version guidance + original
        return header + code + f"\n\n# TODO (programmer): Apply precise edits for: {goals}\n# Remember to use task_tracker + guarded proposal if this touches core system."

    def implement_feature(self, feature_desc: str, files_context: str = "", language: str = "python") -> Dict[str, Any]:
        """High-level feature implementation. Returns plan + suggested files."""
        log.info(f"Programmer Expert: Implementing feature: {feature_desc[:70]}")

        plan = {
            "feature": feature_desc,
            "steps": [
                "1. Retrieve relevant past learnings and proposals",
                "2. Write full task_tracker plan with array",
                "3. Implement core logic (additive)",
                "4. Add/update tests or validation",
                "5. If system change: emit guarded proposal JSON",
                "6. Handoff to tester/reviewer if needed"
            ],
            "language": language,
            "context_used": bool(files_context),
        }

        main_code = self.write_code(language, feature_desc, context=files_context)

        result = {
            "plan": plan,
            "main_implementation": main_code[:4000],  # bounded
            "notes": self.standards_note,
            "next": "Use task_tracker now. If this evolves the agent, write pending_proposals/xxx.json then call safe_research_and_evolve."
        }
        print("🧑‍💻 Programmer Expert: Feature implementation scaffold ready.")
        return result

    def god_tier_design_architecture(self, system_desc: str, constraints: str = "", language: str = "python") -> Dict[str, Any]:
        """GOD-LIKE: Senior+ architect level system design with trade-offs, patterns, scalability, security, performance."""
        log.info(f"Programmer Expert (GOD TIER): Designing architecture for: {system_desc[:60]}")
        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(system_desc, max_results=3) or ""
            except Exception:
                pass
        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(system_desc + " architecture patterns 2026", "god tier system design patterns scalability security")
            except Exception:
                pass
        arch = {
            "system": system_desc,
            "high_level_design": f"Layered/clean/hexagonal + event-driven where appropriate. For {language}: use domain-driven design, dependency injection.",
            "key_patterns": ["CQRS for complex domains", "Event Sourcing for auditability", "Circuit Breaker for resilience", "Saga for distributed tx"],
            "scalability": "Horizontal scaling via stateless services, caching (Redis), async queues (Celery/Rabbit), database sharding/read replicas.",
            "security": "Zero-trust, input sanitization everywhere, rate limiting, secrets via vaults, OWASP top 10 mitigation, formal verification for critical paths.",
            "performance": "Profiling-first (cProfile/py-spy), async I/O, connection pools, CDN for static, lazy loading, WASM for hot paths (coordinate with cpp-expert).",
            "trade_offs": "Consistency vs availability (CP in CAP for money systems), simplicity vs flexibility (start simple, evolve).",
            "hacash_specific": "For Hacash: extend fullnode layers (X16RS mining, HVM contracts, L1/L2/L3 integration), use Rust for perf-critical (fullnode), HVM for financial contracts with AA.",
            "past_learnings": past[:500],
            "research_insights": research[:800] if research else "Modern patterns from 2026 (e.g. actor models, CRDTs for distributed).",
            "deliverables": "Architecture diagram (mermaid), ADR docs, tech stack recs, POC code skeleton, risk matrix, migration plan.",
            "god_tier_notes": "Think 10x: anticipate 10x scale, security theater vs real, observability from day 1 (OpenTelemetry), cost optimization (FinOps). Always additive, testable, documented."
        }
        print("🧠 Programmer Expert (GOD TIER): God-like architecture design delivered.")
        return arch

    def god_tier_code_review(self, code: str, focus: str = "all",
                             language: str = "python") -> dict:
        """A review of THE CODE YOU PASSED.

        The worst offender in the stack. It returned a fixed dict for any input,
        and that dict did not merely omit an opinion — it INVENTED one:
        `overall_score: "9/10 - excellent structure"`, plus named bugs ("Nonce
        overflow edge in mining? Test with high difficulty.", "Channel state
        race in L2 CSP.") and Hacash-specific findings. Measured: a three-line
        divide-by-zero and a raw SQL concatenation got byte-identical reviews —
        both scored 9/10, both credited with excellent structure, both warned
        about mining nonces neither contains.

        The score is gone. Nothing here can honestly produce one.
        """
        log.info(f"Programmer Expert: reviewing {len(code or '')} chars, focus={focus}")
        if not (code or "").strip():
            return {"answered": False,
                    "error": "No code was passed, so nothing was reviewed."}
        out = self.analyse(
            "Review this code. Report only what you can actually see in it: "
            "correctness bugs with the input that triggers them, security "
            "problems with the attack that exploits them, and anything genuinely "
            "unclear. Quote the line you mean. Do NOT give a numeric score. Do "
            "NOT mention blockchain, mining or Hacash unless this code contains "
            "them. If the code is fine, say it is fine.",
            {"language": language, "focus": focus, "code": code},
            reference=self._god_tier_code_review_reference(),
            max_tokens=2400,
        )
        out.pop("overall_score_reference", None)
        out["scored"] = False
        out["note"] = ("No numeric score: a score implies a whole-codebase "
                       "judgement this call cannot make from one snippet.")
        return out

    def _god_tier_code_review_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE: Comprehensive senior review - security, perf, maintainability, bugs, tests, style, Hacash-specific."""
        review = {
            "overall_score": "9/10 - excellent structure but room for perf in hot paths.",
            "security_issues": ["Potential reentrancy if HVM contract calls; use checks-effects-interactions.", "Missing rate limits on RPC; add middleware."],
            "performance_issues": ["N+1 queries in fullnode layer; batch. Use WASM for X16RS hot paths via cpp-expert."],
            "maintainability": "Good modularity (7 layers in fullnode). Add more docs, type hints (mypy strict).",
            "bugs": ["Nonce overflow edge in mining? Test with high difficulty.", "Channel state race in L2 CSP."],
            "test_coverage": "Add property-based (Hypothesis) for X16RS, integration tests for L1 peg + HVM.",
            "style": "Follow Rust/Hacash conventions (from fullnode repo). Black/ruff for Python.",
            "hacash_specific": "Align with L1 readable contracts, HVM AA, X16RS fairness. Coordinate with hacash_* experts.",
            "god_tier_recommendations": "Add formal specs (TLA+ for consensus), chaos engineering, continuous profiling. Make it 10x: anticipate adversarial environments, multi-layer security (L1 PoW + HVM + channels).",
            "refactored_suggestions": "Extract mining logic to separate crate. Use result types everywhere."
        }
        print("🔍 Programmer Expert (GOD TIER): God-like code review delivered.")
        return review

    def god_tier_optimize_and_secure(self, code: str, targets: list = None,
                                     language: str = "python") -> dict:
        """Optimisation and hardening for THIS code.

        Took `code` and never read it: the same profiling advice, the same
        X16RS/WASM suggestions and the same benchmark targets came back for a
        billion-iteration busy loop and for an unclosed file read.
        """
        targets = targets or ["perf", "security", "scalability"]
        log.info(f"Programmer Expert: optimize/secure targets={targets}")
        if not (code or "").strip():
            return {"answered": False, "targets": targets,
                    "error": "No code was passed, so nothing was analysed."}
        out = self.analyse(
            "For this specific code and these targets: name the actual hot path "
            "or hazard you can see in it, say how you would MEASURE that before "
            "changing anything, then give the change. Skip any advice that does "
            "not apply to what is in front of you.",
            {"language": language, "targets": ", ".join(map(str, targets)), "code": code},
            reference=self._god_tier_optimize_and_secure_reference(),
            max_tokens=2400,
        )
        out["targets"] = targets
        return out

    def _god_tier_optimize_and_secure_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE: End-to-end optimization + security hardening + benchmarking plan."""
        targets = ["perf", "security", "scalability"]
        opt = {
            "targets": targets,
            "perf_optimizations": "Profile first (py-spy). For Hacash X16RS: vectorize in C++/WASM (cpp-expert). Async everywhere. Cache L1 state. Use connection pools.",
            "security_hardening": "Add fuzzing (cargo-fuzz for Rust, hypothesis for Py). Constant-time crypto where needed. Input validation at every layer. Integrate security-auditor.",
            "benchmarks": "Add criterion (Rust) or pytest-benchmark. Target: <1ms per X16RS hash on CPU, sub-ms WASM. Track in CI.",
            "hacash_tips": "For fullnode: optimize Chain layer with better indexes. HVM: state opt per design. L2 channels: batch settlements. Mining: GPU kernels via cuda (coordinate illustration assets if needed).",
            "god_tier_level": "Think like Torvalds + Knuth + modern (e.g., 2026 zero-knowledge for privacy in L1). Make it bulletproof: adversarial testing, formal methods, 10x scale simulation.",
            "output": "Optimized code diffs, benchmark results template, security checklist (OWASP + Hacash-specific), deployment with monitoring."
        }
        print("⚡ Programmer Expert (GOD TIER): God-like optimize+secure delivered.")
        return opt

    def god_tier_full_sdlc_implementation(self, project_desc: str, language: str = "python", include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: End-to-end SDLC for complex project - planning to production, with all gates, for general or Hacash-specific."""
        log.info(f"Programmer Expert (GOD TIER): Full SDLC for: {project_desc[:50]}")
        sdlc = {
            "project": project_desc,
            "phases": [
                "Discovery: requirements, threat model, research (code_researcher), past lessons.",
                "Architecture: god_tier_design_architecture + diagrams + ADRs.",
                "Implementation: implement_feature per component, with reviews (god_tier_code_review).",
                "Testing: unit/integration/property/fuzz/chaos + benchmarks.",
                "Security: god_tier_optimize_and_secure + audit (security-auditor).",
                "Hacash integration: Integrate hacash_* experts (mining for X16RS/pools, fullnode 7-layer Rust, HVM contracts/AA, L1 peg+privacy, L2 CSP channels, L3 rollups). Extend Miner layer, use fullnode RPC, HVM deploy for financial logic.",
                "Optimization & Hardening: as above.",
                "Docs & Training: full guides, API specs (OpenAPI), client handoff.",
                "Deployment: via devops, with monitoring (analytics), maintenance plan.",
                "Review Gates: 0 (brief) -> 1 (arch) -> 2 (beta) -> 3 (UAT) -> 4 (pre-launch) -> 5 (live + 30d support). All client-approved, guarded proposals for changes."
            ],
            "god_tier_standards": "10x thinking: anticipate adversarial, 10x load, regulatory (legal), business (analytics/ROI). Additive, observable, evolvable. Use task_tracker religiously. Emit proposals for any core change.",
            "deliverables": "Repo with CI, tests (80%+ cov), benchmarks, docs, diagrams, runbooks, presentation deck.",
            "hacash_integration": "If Hacash: fullnode as base (extend 7 layers), HVM contracts for logic, X16RS mining integration, L1 peg + L2 channels + L3 Rollups. Coordinate all hacash experts + language (Rust primary, C++ for perf, Python for backend tools)."
        }
        print("🚀 Programmer Expert (GOD TIER): God-like full SDLC delivered.")
        return sdlc

    def generate_tests(self, code_or_module: str, framework: str = "pytest", language: str = "python") -> str:
        log.info("Programmer Expert: Generating tests")
        if language == "solidity" or "contract" in code_or_module.lower():
            if solidity_expert:
                return solidity_expert.write_tests(code_or_module)
            return "// TODO: Foundry/Hardhat tests for the contract"
        return f"""# Tests generated by ProgrammerExpert ({framework})
import pytest
# TODO: import the module under test
# def test_{re.sub(r'[^a-z0-9_]', '_', code_or_module[:20].lower() or 'feature')}():
#     assert True
print("Add real assertions here. Follow project test patterns.")
"""

    def debug_and_fix(self, error_log: str, code_snippet: str = "", language: str = "python") -> str:
        log.info("Programmer Expert: Debugging")
        return f"""# DEBUG REPORT by ProgrammerExpert
Error: {error_log[:500]}
Language: {language}

Suggested fix approach:
1. Reproduce locally with minimal case.
2. Add defensive checks / logging.
3. Use task_tracker for the fix session.
4. If root cause is in our agent skills: create guarded proposal.

Code context provided: {'yes' if code_snippet else 'no'}
"""

    def follow_our_standards(self, task: str) -> str:
        """Returns the mandatory standards reminder + how to start a proper coding session."""
        return f"""PROGRAMMER EXPERT STANDARDS FOR: {task}

{self.standards_note}

RECOMMENDED SESSION START (do this first):
Use the task_tracker tool with command="plan" and a COMPLETE task_list array, e.g.:

invoke tool task_tracker with command is plan task_list is [{"id":1,"description":"Understand requirements + retrieve memory","status":"in_progress"},{"id":2,"description":"Design additive implementation","status":"pending"},...]

Then implement step by step. For any change to core (skills, supervisor, loader, dashboard etc.) emit a pending_proposals/*.json guarded proposal.

Handoff to website-builder when the deliverable is a web UI / explorer / dashboard.
"""

    def add_modern_visuals(self, language: str = "typescript", task: str = "", visuals: List[str] = None) -> str:
        """
        Generates high-quality, copy-paste ready modern visual code.
        Supports 3D, Framer Motion, glassmorphism, particles, variable fonts, scroll animations.
        Automatically pulls from Code Researcher when available.
        """
        visuals = visuals or ["framer-motion", "three-js", "glassmorphism", "scroll-animations", "variable-fonts", "particles"]
        log.info(f"Programmer Expert: Adding modern visuals ({visuals}) for {task[:50]}")

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task or "modern visuals", str(visuals))
            except Exception:
                pass

        lang = language.lower()
        if "react" in lang or "ts" in lang or "tsx" in lang or "typescript" in lang:
            three_import = "import { Canvas } from '@react-three/fiber';\nimport { OrbitControls } from '@react-three/drei';" if 'three' in str(visuals) else ""
            three_comp = """export function Hero3D() {
  return (
    <Canvas camera={{ position: [0,0,7], fov: 45 }} style={{ background: 'transparent' }}>
      <ambientLight intensity={0.6} />
      <pointLight position={[10,10,10]} />
      <mesh>
        <torusGeometry args={[1.3, 0.4, 16, 64]} />
        <meshStandardMaterial color="#67e8f9" metalness={0.7} roughness={0.25} />
      </mesh>
      {/* Add <Stars /> from drei for extra polish */}
    </Canvas>
  )
}""" if 'three' in str(visuals) else ""

            return f"""// Modern visuals by ProgrammerExpert (fed by CodeResearcher)
// Task: {task}
// Requested: {visuals}

import {{ motion }} from 'framer-motion';
{three_import}

// Production-ready glass + spring card
export const GlassCard = ({{ children, className = '' }}: {{ children: React.ReactNode; className?: string }}) => (
  <motion.div 
    whileHover={{ y: -6, scale: 1.003 }}
    transition={{ type: 'spring', stiffness: 260, damping: 24 }}
    className={{`glass p-8 rounded-3xl border border-white/10 bg-white/5 backdrop-blur-2xl ${{className}}`}}
  >
    {{children}}
  </motion.div>
);

{three_comp}

// Research / implementation notes from Code Researcher:
// {research[:750] or 'Use with WebsiteBuilder for full pages. Respect reduced-motion media query.'}
"""
        # Fallback clean HTML/JS version
        return f"""<!-- Modern visuals (vanilla) generated by ProgrammerExpert -->
<style>
  .glass {{ background: rgba(255,255,255,.06); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,.12); }}
  .modern-font {{ font-family: 'Space Grotesk', Inter, system-ui; font-feature-settings: "ss01"; }}
</style>

<div class="glass p-9 rounded-3xl">Beautiful modern component — extend with framer or three.js</div>

<script>
  // Lightweight magnetic / tilt effect (no deps)
  // For real 3D/particles use the React version or WebsiteBuilder output
</script>
"""

    def build_modern_frontend_component(self, component_name: str, visuals: List[str] = None) -> str:
        """High level helper — returns a complete ready component with rich modern visuals."""
        return self.add_modern_visuals("typescript", component_name, visuals)

    # --- internal helpers ---
    def _python_code(self, task: str, constraints: str, past: str, context: str) -> str:
        return f'''"""
{task}
Generated by ProgrammerExpert (Python specialist)
"""
# Standards applied: full task_tracker, guarded proposals for system changes, persistent memory, safe wrappers.
# Past context retrieved: {"yes - see below" if past else "none relevant"}
# Constraints: {constraints or "none"}

def main():
    print("Implement the feature for: {task}")
    # TODO: real implementation here
    # 1. Load config / memory if needed
    # 2. Core logic
    # 3. Output or side effects (write files, call MCP, etc.)
    # 4. Always finish with clear user-facing summary + any new proposals created

if __name__ == "__main__":
    main()

# Remember:
# - Create pending_proposals/ for evolution of the system
# - After changes: test end-to-end
# - Use handoff when you need website-builder or other specialists
'''

    def _solidity_stub(self, task: str, chain: str = "ethereum") -> str:
        return f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// ProgrammerExpert + solidity_expert stub for: {task}
// Target: {chain}
// TODO: Replace with full implementation from solidity_expert.write_solidity_contract(...)
contract Placeholder {{
    // Add real logic
}}
"""

    def _web_code_stub(self, task: str, lang: str) -> str:
        is_ts = "ts" in lang or "react" in lang or "vite" in lang
        ext = "tsx" if is_ts else "jsx" if "react" in lang else "js"
        return f"""// {task}
// ProgrammerExpert + modern visuals (call add_modern_visuals or handoff to website-builder)
// Recommended: use website-builder.build_modern_website() for full rich sites (3D, framer, glass, particles, variable fonts)
export function {re.sub(r'[^A-Za-z0-9]', '', task[:20] or 'Feature')}() {{
  // TODO: React component or module
  return "UI for {task}";
}}
// Tip: this.expert.add_modern_visuals("typescript", task, ["framer-motion", "three-js", "glassmorphism"])
"""

    def _script_stub(self, task: str, lang: str) -> str:
        if "ps" in lang:
            return f"""# {task}
# PowerShell script by ProgrammerExpert
Write-Host "Implement: {task}"
# TODO: full logic, error handling, logging
"""
        return f"""#!/bin/bash
# {task} - generated by ProgrammerExpert
set -euo pipefail
echo "Implement: {task}"
# TODO
"""

    # =====================================================================
    # GOD-TIER DEEP METHODS - 10x / institutional senior+ level
    # Every complex task must go through one or more of these.
    # All return rich actionable dicts with exact commands, checklists, ADRs,
    # handoff manifests, and force task_tracker + persistent_memory + guarded proposals.
    # =====================================================================

    def god_tier_threat_model_and_risk_register(self, system_desc: str, assets: List[str] = None, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Exhaustive STRIDE + custom threat model, attack trees, mitigations, residual risk. For money/L1 systems this is non-negotiable."""
        assets = assets or ["user_funds", "consensus", "state", "keys", "rpc"]
        log.info(f"Programmer Expert (GOD TIER): Threat modeling for {system_desc[:60]}")
        model = {
            "system": system_desc,
            "assets": assets,
            "stride": {
                "Spoofing": "Strong auth (ed25519/secp for Hacash), mTLS for node comms, HVM account abstraction with session keys.",
                "Tampering": "Immutable L1 history + Merkle proofs. Signed tx only. For L2: multi-sig CSP + L1 settlement finality.",
                "Repudiation": "Full event sourcing + on-chain logs + HVM receipts. Non-repudiatable via PoW anchors.",
                "Information Disclosure": "Optional privacy on L1 (mixing/stealth where supported). Never log privkeys. Rate limit RPC.",
                "Denial of Service": "Difficulty adjustment + Beacon Tower (Hacash). Resource limits on HVM gas. Connection backpressure.",
                "Elevation of Privilege": "Least privilege at every layer. No root in containers. Capability-based in HVM if extended."
            },
            "hacash_specific_threats": [
                "51% / eclipse on X16RS PoW: mitigate via honest majority assumption + checkpoints + L2 finality preference.",
                "BTC peg theft / replay: one-way peg design + specific redeem scripts + legal/compliance on off-ramp.",
                "HACD diamond MEV / front-running: L2 channels first, then L1; fair ordering via CSP.",
                "HVM contract reentrancy / state bloat: checks-effects-interactions + storage rent + AA paymasters.",
                "Pool centralization: P2P relay trees, no single operator control, open source PoWorker."
            ] if include_hacash else [],
            "attack_trees": "Root: Steal funds -> leaves: compromise node, exploit HVM, social engineer keys, 51% + reorg + double spend.",
            "mitigations_checklist": [
                "Formal model critical paths (TLA+ for consensus/peg, Alloy for HVM state machine).",
                "Fuzz + property tests (cargo-fuzz, hypothesis, echidna for contracts).",
                "Chaos: kill nodes mid-mining, partition L2 channels, inject bad PoW shares.",
                "External audit (security-auditor) + bug bounty scope.",
                "Observability: Prometheus + Grafana + on-chain metrics + PagerDuty."
            ],
            "residual_risk": "51% theoretical (economic cost high on Hacash). Smart contract bugs in HVM (mitigate with formal + audits).",
            "god_tier_note": "Produce this before any implementation. Store in persistent_memory. Emit guarded proposal for any new asset class or L1 change.",
            "next_actions": "1. task_tracker full plan 2. Call god_tier_generate_adrs 3. Handoff to security-auditor + relevant hacash_* expert"
        }
        return model

    def god_tier_generate_adrs(self, decisions: List[str], context: str = "", include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Produce Architecture Decision Records (MADR or custom format) for every significant trade-off. Versioned, searchable."""
        log.info("Programmer Expert (GOD TIER): Generating ADRs")
        adrs = []
        for i, d in enumerate(decisions[:8]):
            adr = {
                "id": f"ADR-{100+i}",
                "title": d,
                "status": "Accepted",
                "context": context or "High-stakes production system (Hacash L1/L2 or complex dApp).",
                "decision": f"Adopt {d} as primary pattern.",
                "consequences": "Positive: scalability, auditability. Negative: complexity (mitigated by god-tier docs + tests).",
                "alternatives_considered": ["Monolith", "EVM-only (rejected: no native AA + diamond economics)", "Pure L2 (rejected: settlement security on L1)"],
                "hacash_notes": "For Hacash: prefer Rust in fullnode 7 layers (X16RS/Core/Chain/Mint/Node/Server/Miner), HVM for AA contracts, L2 channels for payments before L1 settlement." if include_hacash else None
            }
            adrs.append(adr)
        return {
            "adrs": adrs,
            "format": "MADR + mermaid diagrams recommended. Store in /docs/adr/ as .md",
            "god_tier_requirement": "Every non-trivial feature touching money, consensus, state or cross-layer must have >=1 ADR before code.",
            "handoff": "Feed to project_manager for client presentation + to persistent_memory."
        }

    def god_tier_chaos_formal_and_property_testing_plan(self, components: List[str], include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: Full chaos engineering + formal methods + property-based + fuzz plan. This is what separates toy from institutional."""
        log.info("Programmer Expert (GOD TIER): Chaos + Formal plan")
        plan = {
            "components": components,
            "formal_methods": {
                "TLA+": "Model X16RS difficulty, L1 fork choice, peg redeem, HVM storage rent, CSP channel close. Use TLC model checker.",
                "Alloy": "State machine for L2 channel (open, update, close, dispute) + HVM account abstraction invariants.",
                "expected": "Prove no double-spend under honest majority + no stuck funds on channel close."
            },
            "property_based": "Hypothesis (Python) or proptest (Rust). Generate 10k+ adversarial tx sequences, channel states, diamond claims.",
            "fuzzing": "cargo-fuzz for Rust fullnode/mempool; echidna/hardhat for HVM contracts; custom X16RS differential fuzzer (CPU vs GPU vs WASM).",
            "chaos_experiments": [
                "Kill 30% of miners mid-block, verify chain continuity + difficulty retarget.",
                "Partition L2 CSP nodes for 5min, force mass channel close to L1, check fairness + no loss.",
                "Inject invalid shares into pool, verify no reward inflation + detection.",
                "State bloat attack on HVM: 10M accounts, verify rent + pruning works.",
                "51% simulation (private testnet): reorg depth 6, check L2 settlement + BTC peg safety."
            ] if include_hacash else ["Node kill, network partition, resource exhaustion, bad input floods."],
            "ci_integration": "Nightly chaos job + property suite. Fail build on regression. Grafana dashboards for 'time to recover'.",
            "god_tier_level": "Anticipate every realistic failure mode before mainnet. 10x teams ship formal + chaos as first-class deliverables.",
            "deliverables": "TLA+ specs + TLC results, property test suites, chaos runbooks, Grafana + PagerDuty integration, post-mortem template."
        }
        return plan

    def god_tier_benchmark_and_perf_model(self, hot_paths: List[str], targets: Dict[str, str] = None, language: str = "rust") -> Dict[str, Any]:
        """GOD-LIKE: Rigorous performance model, targets, measurement harness, regression gates. Never guess - always measure + prove."""
        targets = targets or {"x16rs_hash": "< 800us CPU single core (mid 2026)", "hvm_tx": "< 2ms per simple transfer", "channel_update": "< 50us p2p", "fullnode_sync": "full archival < 4h on NVMe"}
        log.info(f"Programmer Expert (GOD TIER): Perf model for {hot_paths}")
        return {
            "hot_paths": hot_paths,
            "language": language,
            "targets": targets,
            "measurement": {
                "rust": "cargo bench + criterion + iai (cachegrind). Use perf + flamegraph. For X16RS: count cycles per 16-hash round.",
                "python": "py-spy, pytest-benchmark, line_profiler. For backend: locust for RPC load.",
                "wasm": "wasm-opt -O3, wasm-bench, browser devtools + custom timer for 3D+pricing WASM path (cpp-expert).",
                "gpu": "nsight / rocprof, occupancy, memory bandwidth. Target > 90% for X16RS kernels."
            },
            "hacash_perf_notes": "X16RS is 16 serial hashes - optimize each (SIMD, AES-NI where applicable). Separate HAC vs HACD difficulty. Miner layer in fullnode must not block Chain/Mint. HVM storage must be O(1) or rent-backed.",
            "regression_gates": "CI fails if >5% regression on key bench without ADR+review. Track p99 latency + throughput in production analytics.",
            "god_tier_note": "10x = you know the exact cycle count and cache misses for the 1% hot path before writing the PR."
        }

    def god_tier_production_ops_and_deployment(self, system: str,
                                              include_hacash: bool = False) -> dict:
        """An ops plan for THIS system.

        Took `system` and ignored it — a Django monolith and a Rust
        microservice received the same deployment, monitoring and rollback plan,
        byte for byte. Found by execution; the static pass had ranked this one
        low-priority.
        """
        if not (system or "").strip():
            return {"answered": False,
                    "error": "No system was described, so no ops plan was made."}
        out = self.analyse(
            "Plan production operations for THIS system specifically: how it is "
            "built and shipped, what its real failure modes are, the few signals "
            "worth alerting on, and how a bad release is rolled back. Name the "
            "concrete tooling that fits this stack, not a generic checklist.",
            {"system": system, "hacash_in_scope": "yes" if include_hacash else "no"},
            reference=self._god_tier_production_ops_and_deployment_reference(),
            max_tokens=2000,
        )
        out["system"] = system
        return out

    def _god_tier_production_ops_and_deployment_reference(self) -> Dict[str, Any]:
        """Fixed reference material. Takes no arguments, because the
        original took them and used none of them."""
        """GOD-LIKE: Complete prod checklist - Docker, systemd, k8s (optional), CI/CD, secrets, monitoring, runbooks, on-call, rollback."""
        log.info("Programmer Expert (GOD TIER): Production ops plan")
        return {
            "docker": "Multi-stage. Non-root. Distroless or alpine. Healthcheck on RPC + mining status. Resource limits (cpu 2, mem 4G for fullnode).",
            "exact_build": "For Rust fullnode: cargo build --release -p hacash --features=fullnode. Strip. For WASM payment: emcc payment_pricing.cpp -O3 -s WASM=1 -s EXPORTED_FUNCTIONS='[\"_calc_price_risk\"]' -o pricing.wasm",
            "systemd_units": "hacash-fullnode.service (Type=notify, Restart=always, MemoryMax=4G, Nice=-5). pool.service. exporter.service (Prometheus).",
            "ci_cd": ".github/workflows: test (unit+prop+fuzz 30min), bench, chaos-nightly, build-release, docker-publish, deploy-staging. Required reviews on main.",
            "secrets": "Never in git. Use age or sops + git-crypt or Vault. For nodes: separate operator keys vs hot wallet (min amount).",
            "observability": "OpenTelemetry + Prometheus + Grafana (hashrate, difficulty, channel states, HVM gas, peg volume, error budget). Alert on 51% hashrate share >33%, channel dispute rate spike.",
            "runbooks": "1. Node desync -> reindex or snapshot restore. 2. Mass channel close -> monitor L1 settlement queue + manual dispute if needed. 3. Pool share flood -> ban + fairness recalc.",
            "hacash_ops": "Run multiple independent fullnodes for redundancy. Use official bootstrap + your own. Diamond (HACD) separate index. BTC peg watchtower process (off-chain + on-chain proofs).",
            "rollback": "Blue/green or canary. Feature flags (even for consensus extensions via HVM). 30s RTO target for critical services.",
            "god_tier_standard": "You ship the runbook, the dashboard, the alert, the rollback script, and the 3am on-call doc together with the feature."
        }

    def god_tier_full_team_handoff_manifest(self, project: str, include_hacash: bool = False) -> Dict[str, Any]:
        """GOD-LIKE: The exact manifest ProjectManager + supervisor use to orchestrate the full god-like team. Concrete calls + expected outputs."""
        manifest = {
            "project": project,
            "mandatory_first_steps": [
                "task_tracker plan with 15-30 item task_list array (complete, no missing)",
                "persistent_memory.retrieve_relevant_evolution(project)",
                "programmer_expert.god_tier_threat_model_and_risk_register(...) + god_tier_generate_adrs(...)"
            ],
            "programmer_god_tier_sequence": [
                "god_tier_design_architecture(...) -> diagrams + tradeoffs",
                "god_tier_full_sdlc_implementation(...) -> phases + gates",
                "god_tier_code_review on every PR/component",
                "god_tier_optimize_and_secure + god_tier_benchmark_and_perf_model",
                "god_tier_chaos_formal_and_property_testing_plan",
                "god_tier_production_ops_and_deployment"
            ],
            "hacash_god_tier_if_applicable": {
                "mining": "hacash_mining_expert.god_tier_implement_production_ready_mining_system + god_tier_x16rs_optimization (new)",
                "fullnode": "hacash_fullnode_expert.god_tier_implement_production_ready_fullnode_system (7 layers explicit)",
                "hvm": "hacash_hvm_expert.god_tier_implement... (AA, multi-lang, state rent)",
                "l1_l2_l3": "respective god_tier for peg, CSP channels, rollups + cross layer invariants"
            } if include_hacash else "N/A - use for pure web3 or when adding Hacash settlement",
            "cross_expert_handoffs": [
                "-> security-auditor.audit_security after god_tier_optimize",
                "-> qa-engineer + devops after benchmarks + chaos plan",
                "-> website-builder + analytics-specialist for any explorer/dashboard (use fullnode RPC + HVM events)",
                "-> legal-compliance-expert for peg/KYC/AML on ramps",
                "Always emit guarded proposal for any change that touches consensus, money, or shared state."
            ],
            "client_deliverables_from_god_tier": "ADR deck, threat model + mitigations, formal+chaos report, benchmark numbers vs targets, prod runbooks, 30-day support matrix, on-chain verification scripts.",
            "god_level": "10x: the handoff manifest itself becomes part of the living project docs and is executed by the supervisor automatically."
        }
        return manifest

# Register
programmer_expert = ProgrammerExpert()
print("🧑‍💻 Programmer Expert (GOD TIER) registered. Ready for sub_type='programmer'. God-like senior+ engineering across languages, with deep Hacash integration.")