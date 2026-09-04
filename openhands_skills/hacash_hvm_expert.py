"""
Hacash HVM Expert Skill for OpenHands
Professional specialist for Hacash Virtual Machine (HVM) and smart contracts.
Focus: HVM architecture (security-first, multi-language contracts, account abstraction, state-efficient storage), contract development, deployment on testnet/mainnet, integration with L1/L2/L3, DeFi/BTCFi/PayFi/stablecoin use cases, compilation, testing, comparison to EVM/other VMs.
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


class HacashHVMExpert(ExpertSkill):
    """
    Senior Hacash HVM (Virtual Machine) Specialist.
    Expert in the Hacash Contract Virtual Machine for secure financial smart contracts. Multi-lang support, powerful account abstraction, state optimization. Ideal for building on Hacash L1/L2 for DeFi, BTCFi etc.
    Works with fullnode, L1/L2/L3, mining, Rust/C++/Python/TS specialists, website-builder for explorers/tools.
    """

    def __init__(self):
        self.focus = "Professional development and extension of Hacash HVM smart contracts and VM for secure, scalable financial applications on the Hacash network."

    def implement_hvm_contracts(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: HVM contract implementation, VM features, deployment, integration, analysis for Hacash projects."""
        log.info(f"HacashHVMExpert: Implementing HVM for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " hacash hvm 2026", "hacash hvm virtual machine smart contracts best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "hvm_overview": self.hvm_overview(),
            "vm_features": self.vm_features(),
            "contract_development": self.contract_development(),
            "deployment_testnet": self.deployment_testnet(),
            "integration_with_layers_fullnode": self.integration_with_layers_fullnode(),
            "code_examples": self.code_examples(),
            "comparison_security": self.comparison_security(),
            "research": research[:1200] if research else "hacash/hvm repo, hacash.com/hvm, doc/HIP, fullnode HVM testnet docs, whitepaper L1 programmability."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("hacash:hvm", f"{task} | professional Hacash HVM contract/VM dev for client/work")
            except Exception:
                pass

        print("🖥️ HacashHVMExpert: Professional Hacash HVM implementation delivered (VM, contracts, deployment, integration).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a master of the Hacash Virtual Machine, account abstraction and financial smart contracts.")
        self.mark_analysis(result)
        return result

    def hvm_overview(self) -> Dict[str, str]:
        return {
            "description": "Hacash Virtual Machine (HVM) is a VM tailored for secure financial applications. Powerful account abstraction and state optimization. Ideal for DeFi, BTCFi, PayFi, stablecoins on Hacash.",
            "key_innovations": "Security-first design, multi-language contracts (not just EVM bytecode), state-efficient storage (better than typical account or UTXO models for finance).",
            "positioning": "Enhances L1 programmability (readable contracts per whitepaper) while avoiding EVM weaknesses (complexity, security issues, stack-based limits). Supports L2/L3 scaling.",
            "status": "Testnet launched. hvm/readme.md in archives has code guidelines, test code, howtos for compiling/running testnet full nodes and deploying contracts. PRs submitted to main Hacash GitHub."
        }

    def vm_features(self) -> Dict[str, str]:
        return {
            "account_abstraction": "Powerful AA for flexible accounts, better UX/security in financial apps (beyond EOA or basic AA in other VMs).",
            "state_optimization": "Efficient storage for financial state (balances, contracts, DeFi positions). Reduces bloat vs EVM.",
            "multi_language": "Support for multiple contract languages (details in HVM docs/repo). Compiles to HVM bytecode.",
            "security": "Designed from ground up for secure finance (no common EVM pitfalls like reentrancy in same way, better isolation?).",
            "comparison": "Vs EVM: simpler, more secure for finance, state efficient, multi-lang. Vs others: tailored for Hacash's 3-coin, 3-layer money + payments system."
        }

    def contract_development(self) -> Dict[str, str]:
        return {
            "languages": "Per HVM docs (check hvm repo/readme for supported: likely includes Rust-like, or others for finance). Write contracts, compile to HVM.",
            "tools": "HVM compiler, test framework (in hvm/readme). Full node with HVM for local/testnet deployment.",
            "features_for_finance": "Account abstraction for complex DeFi (lending, stablecoins, BTCFi bridges?), state opt for large scale positions, readable/secure contracts.",
            "best_practices": "Follow security-first design. Test thoroughly on HVM testnet. Use L1 primitives (HAC settlement, HACD assets). Integrate with L2 channels for payments in contracts.",
            "deployment": "Compile, deploy via full node RPC or tools. See HVM testnet launch docs."
        }

    def deployment_testnet(self) -> str:
        return """HVM Testnet deployment:
- Run Hacash full node with HVM enabled (per hvm/readme.md in archive: compile/run testnet full nodes).
- Use provided test code and howbooks for contracts.
- Deploy smart contracts to testnet.
- Tools: Check hacash/hvm GitHub, hacash.com/hvm, doc/HIP for HIPs related to HVM.
- Full node API extensions for HVM (contract calls, state queries).
Handoff to fullnode expert for node setup, to L1/L2 for settlement integration.
"""

    def integration_with_layers_fullnode(self) -> str:
        return """Integration:
- Fullnode: HVM runs on/extends full nodes (testnet nodes per docs). RPC for contract deploy/call, state. Mining secures the chain HVM settles on.
- L1: HVM enhances L1 with advanced contracts (beyond basic readable contracts in whitepaper). Use L1 money (HAC for fees/settlement, HACD as assets, BTC peg).
- L2: Contracts can use L2 channel payments for instant settlement inside DeFi logic. CSP integration.
- L3: HVM as base for L3 apps/Rollups (multi-lang contracts on scaled layers).
- Mining: HVM contracts can interact with mining rewards, diamonds (HACD in DeFi).
- Example: HVM contract for BTCFi (BTC bridged to Hacash L1 used in HVM DeFi, settled via L2 channels).
Handoffs: "hacash_fullnode_expert + hacash_hvm_expert: extend full node for HVM contract state exposure". "hacash_l1_expert: integrate HVM with L1 BTC peg and settlement".
"""

    def code_examples(self) -> str:
        return """// HVM contract example (pseudocode - see hvm/readme.md and repo for actual syntax, compilation, deployment)
// Multi-lang support; example in a finance-friendly language or Rust-like for HVM.

contract StablecoinBridge {
    // Account abstraction: flexible ownership, recovery etc.
    account owner;
    mapping(address => uint) balances; // State-efficient storage

    function mint(address to, uint amount) onlyOwner {
        // Use L1 HAC or bridged BTC logic
        balances[to] += amount;
        emit Mint(to, amount);
    }

    function transfer(address to, uint amount) {
        // Secure transfer, integrate with L2 channels for instant payments?
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }

    // DeFi/BTCFi features: lending, stablecoin logic, on L1 settlement
}

// Compile per HVM tools, deploy to testnet full node.
// Call from Rust fullnode or custom client. Integrate with 3D explorer or website via RPC.
"""

    def comparison_security(self) -> Dict[str, str]:
        return {
            "vs_evm": "HVM: security-first from design, multi-lang (avoid EVM bytecode complexity), state-efficient (better for finance scale), account abstraction powerful for DeFi. Avoids common EVM reentrancy, gas, stack issues.",
            "vs_others": "Tailored for Hacash's unique 3-coin 3-layer (money + payments + apps). Readable contracts on L1 + HVM on top for advanced logic. Better for BTCFi (BTC peg + HVM DeFi).",
            "security_notes": "Follow HVM security design principles. Audit contracts (use with security-auditor). Testnet first. State opt reduces attack surface vs bloated storage.",
            "best_for": "Secure financial apps: DeFi protocols, stablecoins, BTC bridges on Hacash L1/L2, PayFi, institutional on-chain finance."
        }

    def god_tier_implement_production_ready_hvm_system(self, requirements: str, include_l1_l2_l3: bool = True) -> Dict[str, Any]:
        """GOD-LIKE: End-to-end production HVM + contracts system for Hacash - VM, multi-lang contracts, deployment, perf, security, full L1/L2/L3 integration. God-tier for financial DApps."""
        log.info(f"HacashHVMExpert (GOD TIER): God-like HVM system for: {requirements[:50]}")
        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(requirements, max_results=3) or ""
            except Exception:
                pass
        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(requirements + " hacash hvm 2026 god tier", "advanced smart contract VMs account abstraction state optimization DeFi")
            except Exception:
                pass
        god = {
            "requirements": requirements,
            "god_tier_architecture": {
                "hvm_core": "Security-first VM (per design): multi-lang (compile to HVM bytecode), powerful AA (flex accounts, recovery, sessions), state-efficient storage (optimized for financial state vs EVM bloat).",
                "contracts": "DeFi/BTCFi/PayFi/stablecoin primitives. Use L1 (HAC fees/settlement, HACD assets, BTC peg). L2 channels for instant inside contracts. L3 for scaled execution.",
                "deployment": "Testnet full nodes (per hvm/readme). Mainnet via fullnode extensions. Tools for compile/deploy/call. RPC from fullnode.",
                "hacash_integration": "L1 base (money primitives + readable contracts + HVM). L2 (payments in DeFi). L3 (Rollups with HVM). Fullnode (HVM state exposure). Mining (rewards in contracts).",
            },
            "production_code_scaffolds": {
                "hvm_contract": "// Example multi-lang finance contract (see hvm/readme for syntax). Use AA for complex DeFi logic. State opt for scale.",
                "fullnode_extension": "// Extend fullnode Server/Node for HVM RPC (deploy, call, state queries). Coordinate with hacash_fullnode_expert.",
                "integration": "L2 channel calls from HVM. L1 peg in contracts. Analytics for contract events.",
            },
            "perf_security_god": "State opt per HVM design (less bloat = better perf/attacks). AA for secure UX. Audit all (security-auditor). Testnet chaos. Formal for critical (e.g., stablecoin invariants).",
            "god_tier_level": "10x: design for institutional finance (compliance via legal, scale via L3, security via design + audits). Anticipate adversarial contracts, MEV on L2, regulatory. Make HVM the gold standard for on-chain finance. Full docs, examples, benchmarks.",
            "deliverables": "HVM contract templates (DeFi/BTCFi), fullnode patches for HVM, deployment scripts (testnet/main), security checklist, integration guides (L1-3, mining, analytics), client deck (HVM as DeFi foundation).",
            "past_research": (past + " " + research)[:800],
            "handoffs": "hacash_fullnode_expert for node HVM. hacash_l1/l2/l3 for layer primitives/payments/scaling. security-auditor for audits. analytics for contract metrics. website-builder for HVM explorer/DApp UI. cpp for any heavy in contracts if WASM."
        }
        print("🖥️ HacashHVMExpert (GOD TIER): God-like production HVM system delivered.")
        return god

    def god_tier_hvm_account_abstraction_and_state(self) -> Dict[str, Any]:
        """ULTRA DEEP on native AA + state model vs EVM. This is why HVM is superior for serious finance."""
        return {
            "aa_model": "Every account has code, storage, nonce, and can have multiple 'keys' (session, recovery, paymaster). No EOA vs contract split like Ethereum.",
            "state_efficiency": "Designed for financial workloads: compact storage, rent or explicit delete, no unbounded growth like EVM SSTORE spam. Enables real institutional scale.",
            "multi_lang": "Write in Rust/Go-like or higher-level that compiles to HVM bytecode. Better auditability than EVM bytecode.",
            "integration": "HVM txs are first-class L1 citizens. Gas paid in HAC. Can directly control pegged BTC or HACD. L2 channels can call HVM for complex settlement logic.",
            "formal": "Model AA state transitions + gas in TLA+/Alloy. Prove no reentrancy under the AA rules, no storage exhaustion.",
            "god_tier": "HVM + L1 money + L2 instant = the stack for serious on-chain finance that institutions can actually use without 5 layers of L2 hacks.",
            "handoffs": "hacash_fullnode_expert (host), hacash_l1_expert (money primitives), hacash_l2_expert (channel <-> HVM), security-auditor + legal for compliance features."
        }

    def god_tier_hvm_contract_production(self, contract_type: str = "defi") -> Dict[str, Any]:
        return {
            "scaffold": "Use official HVM examples + fullnode testnet. Deploy via extended RPC. Call with AA sessions.",
            "security": "checks-effects-interactions still applies. Add HVM-specific: gas metering + rent, session key expiry, paymaster allowlists.",
            "testing": "Fullnode testnet + property tests on state machine + chaos (reorg during contract call).",
            "god": "Every HVM contract that touches real HAC/HACD/BTC must have god_tier_threat_model from programmer + this + audit before mainnet."
        }

# Register
hacash_hvm_expert = HacashHVMExpert()
print("🖥️ HacashHVMExpert (GOD TIER) registered. Ready for sub_type='hacash_hvm'. Native AA, state-efficient, multi-lang financial VM master.")