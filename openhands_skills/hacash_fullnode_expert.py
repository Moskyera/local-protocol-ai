"""
Hacash Fullnode Expert Skill for OpenHands
Professional specialist for Hacash full node code and operations.
Focus: Rust full node (architecture: X16RS -> Core -> Chain -> Mint -> Node -> Server -> Miner), RPC API, running/synchronizing nodes, layer integration (L1/L2/L3), mining interfaces, PoWorker, configuration, compilation, explorer tools.
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


class HacashFullnodeExpert(ExpertSkill):
    """
    Senior Hacash Fullnode Specialist.
    Expert in the official Rust Hacash full node implementation, its 7-layer architecture, RPC services, node operation, and integration with mining, HVM, and the 3 layers.
    Works with mining expert, HVM, L1/L2/L3 experts, Rust/C++/Python specialists.
    """

    def __init__(self):
        self.focus = "Building, running, extending, and integrating professional Hacash full nodes based on the official Rust implementation and architecture for L1/L2/L3 and HVM."

    def implement_fullnode_features(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Main professional entry: Full node feature implementation, setup, API usage, layer integration, custom extensions for Hacash projects."""
        log.info(f"HacashFullnodeExpert: Implementing fullnode for: {task[:60]}")
        context = context or {}

        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(task + " hacash fullnode rust 2026", "hacash rust fullnode architecture rpc layers best practices")
            except Exception:
                pass

        result = {
            "task": task,
            "architecture_overview": self.architecture_overview(),
            "running_and_setup": self.running_and_setup(),
            "rpc_api": self.rpc_api(),
            "layer_integration": self.layer_integration(),
            "code_examples": self.code_examples(),
            "custom_extensions": self.custom_extensions(),
            "hvm_mining_integration": self.hvm_mining_integration(),
            "research": research[:1200] if research else "Official fullnode repo (hacash/fullnode, hacash/rust), doc repo (build, config, API, HACD), whitepaper, x16rs, HVM repos."
        }

        if persistent_memory:
            try:
                persistent_memory.store_learning("hacash:fullnode", f"{task} | professional Hacash full node implementation and ops for client/work dev")
            except Exception:
                pass

        print("🖥️ HacashFullnodeExpert: Professional Hacash full node implementation delivered (Rust arch, RPC, layers, integration).")
        result["expert_analysis"] = self.consult(
            task, context, extra_system="You are a senior Rust engineer and master of the Hacash 7-layer full-node architecture.")
        self.mark_analysis(result)
        return result

    def architecture_overview(self) -> Dict[str, str]:
        return {
            "layers": "7 levels bottom-up: 1. X16RS (base PoW alg, HAC/HACD mining), 2. Core (basic structs?), 3. Chain (blockchain logic), 4. Mint (coin creation, HAC/HACD issuance), 5. Node (core node logic), 6. Server (RPC, P2P, APIs), 7. Miner (block construction, tx mempool, pool server/worker, diamond mining).",
            "design": "Each layer independent, lower unknown to upper, upper calls lower. Clean separation for modularity (per rust repo README).",
            "fullnode_role": "Syncs all blocks, provides RPC for miners/pools/explorers, serves as base for L1/L2/L3/HVM. Releases for easy run, source for compile/custom.",
            "related": "PoWorker for external mining, relay nodes for pool scaling, full node API for HVM testnet etc."
        }

    def running_and_setup(self) -> Dict[str, str]:
        return {
            "fastest": "Download from https://github.com/hacash/fullnode/releases (OS specific zip with exe + hacash.config.ini). Unzip, edit config, run. Syncs blocks automatically.",
            "compile": "From source (Rust). See doc/build/build_compilation.md. For verification or custom builds.",
            "config": "hacash.config.ini: RPC enable, miner interfaces, P2P, data dir, etc. See doc/build/config_description.md and fullnode_api_doc.md.",
            "run_full_node": "Two steps per hacash.org: download + run. Monitor sync, enable RPC for tools/miners.",
            "notes": "Full node is base for everything (mining interfaces, HVM testnet nodes, L2 CSPs, explorers). Use for development/testing."
        }

    def rpc_api(self) -> Dict[str, str]:
        return {
            "enable": "In config: enable RPC server. See doc/server/fullnode_api_doc.md for full list.",
            "mining": "Interfaces for PoWorker: get work (template, target, nonce range), submit solution. Also for pools (HTTP).",
            "general": "Block queries, tx, chain state, HACD/diamond info, mempool. Useful for custom explorers, wallets, L2/L3 tools.",
            "HVM": "Testnet full nodes have HVM specific APIs (see hvm/readme.md in archives).",
            "examples": "PoWorker connects via HTTP/TCP. Mining pool software uses these. Extend for custom services."
        }

    def layer_integration(self) -> str:
        return """L1/L2/L3/HVM integration:
- L1: Full node is the L1 base (money creation via Mint layer, settlement, BTC peg handling, readable contracts on L1).
- L2: Channel chain / CSP uses full node for on-chain settlement/anchoring. CSP nodes connect to fullnode for L1 state.
- L3: Apps/Rollups use full node for L1/L2 data, state proofs, final settlement. Multi-chain via full node APIs.
- HVM: HVM testnet/full nodes extend the node for contract execution, state (account abstraction, efficient storage). Deploy/run contracts via full node.
- Mining: Miner layer in fullnode for block/diamond construction; external via PoWorker/relay to fullnode.
- Rust: All in one codebase (hacash/fullnode or rust). Extend specific layers (e.g., add HVM to Node/Server).
Handoffs: "hacash-hvm-expert: add HVM contract deployment to full node RPC" or "hacash-l2-expert: implement CSP node using fullnode APIs".
"""

    def code_examples(self) -> str:
        return """// Rust full node usage (from official repos)
// Run: cargo run or use release binary + config
// RPC example (HTTP, see fullnode_api_doc.md)
use reqwest; // or hyper for client

async fn get_block_height(fullnode_url: &str) -> Result<u64, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let res = client.post(fullnode_url)
        .json(&serde_json::json!({"method": "getblockheight", "params": []}))
        .send().await?;
    let json: serde_json::Value = res.json().await?;
    Ok(json["result"].as_u64().unwrap())
}

// Mining pool / PoWorker integration
// Get work from fullnode/relay, compute X16RS (via x16rs crate or GPU), submit
// Extend in fullnode source: modify Miner or Server layer for custom logic.
"""

    def custom_extensions(self) -> list:
        return [
            "Extend Rust layers: add custom RPC in Server, new mint logic in Mint, enhanced mempool in Node.",
            "HVM integration: follow hvm/readme.md for compiling/running testnet nodes with contracts. Extend fullnode for HVM state.",
            "Tools: Build custom explorer using RPC (blocks, tx, diamonds, HVM contracts). Integrate with website-builder for Hacash explorer sites.",
            "L2/L3: CSP or Rollup nodes query fullnode for L1 anchors/state. Use for channel service or app chains.",
            "Mining: Custom pool extensions, GPU miner bindings (C++/CUDA calling x16rs), relay improvements.",
            "Performance: Profile Rust node, optimize specific layers (e.g., Chain for faster sync). Coordinate with cpp-expert for hot paths in WASM if exposing compute."
        ]

    def hvm_mining_integration(self) -> str:
        return """HVM + Mining + Fullnode:
- Fullnode provides base for HVM testnet (run full node with HVM enabled per hvm docs).
- Mining secures the L1 that HVM contracts settle on (HAC fees, HACD assets usable in HVM?).
- Contracts on HVM can reference mining data or rewards via L1 primitives (coordinate with hacash_hvm_expert and hacash_l1_expert).
- Example: HVM contract for decentralized mining pool or diamond-based DeFi, settled on L1 via full node.
- Code: See hvm/readme.md for contract examples, fullnode for exposing HVM state via RPC.
Handoff: "hacash-hvm-expert + hacash_fullnode_expert: extend full node RPC for HVM contract queries and mining data".
"""

    def security_fairness(self) -> list:
        return [
            "Run your own full node for trustless operation (don't rely on public nodes for critical work).",
            "Mining fairness: follow X16RS and pool docs to avoid centralization. Monitor hashrate.",
            "Node security: secure config (RPC auth if exposed), keep synced, backup data. Coordinate with security-auditor for custom extensions.",
            "HVM: Follow security-first design (per HVM docs). Audits for contracts (use hacash_hvm_expert + security-auditor).",
            "L2/L3: Channel credit/default risks (per whitepaper), Rollup security assumptions. Use full node for on-chain verification.",
            "General: 51% resistance features (Beacon Tower?), optional privacy on L1. Testnet for safe dev."
        ]

    def god_tier_implement_production_ready_fullnode_system(self, requirements: str, include_hvm: bool = True, include_layers: bool = True) -> Dict[str, Any]:
        """GOD-LIKE: End-to-end production full node system for Hacash - arch, code, deployment, perf, security, full layer/HVM/mining integration. God-tier engineering."""
        log.info(f"HacashFullnodeExpert (GOD TIER): God-like fullnode system for: {requirements[:50]}")
        past = ""
        if persistent_memory:
            try:
                past = persistent_memory.retrieve_relevant_evolution(requirements, max_results=3) or ""
            except Exception:
                pass
        research = ""
        if code_researcher:
            try:
                research = code_researcher.feed_programmer_and_website(requirements + " hacash rust fullnode 2026 god tier", "advanced full node systems RPC layer integration performance")
            except Exception:
                pass
        god = {
            "requirements": requirements,
            "god_tier_architecture": {
                "exact_7_layers_from_official": "1. x16rs (PoW core - 16 serial hashes), 2. core (primitives, tx, block header), 3. chain (chainstate, fork choice, reorg), 4. mint (HAC block reward + HACD diamond generation + BTC one-way peg), 5. node (p2p protocol, sync, mempool), 6. server (JSON-RPC, REST, websocket for templates), 7. miner (block template construction + submit validation + mining coordination). You extend, never fork the layering.",
                "base": "Official 7-layer Rust (X16RS -> Miner). Extend cleanly: add HVM to Node/Server, L2 CSP hooks to Server, L3 anchors to Chain/Mint. Stateless where possible for scaling.",
                "production": "P2P mesh + RPC (auth, rate limit, TLS). Mempool with priority (fees + fairness). Difficulty adjustment per whitepaper. Backup/restore, pruning options.",
                "hacash_layers_hvm": "L1: Mint/Chain for HAC/HACD/BTC peg. L2: Server hooks for CSP settlement. L3: Anchors/proofs from Rollups. HVM: Extend for contract state (AA, efficient storage) - per HVM design.",
                "mining": "Miner layer + PoWorker/relay. External pools via HTTP. Integrate with hacash_mining_expert.",
            },
            "production_code_scaffolds": {
                "rust_extension": "// Extend Server for custom RPC (HVM calls, L3 anchors). See official fullnode_api_doc.md. Use async (tokio).",
                "config_hardening": "Secure .ini (RPC creds, P2P limits). Docker + systemd. Monitoring (Prometheus for blocks, mempool, hashrate).",
                "deployment": "Compile for target (see build_compilation.md). Releases for quick. Testnet for HVM/L3 dev.",
            },
            "perf_security_god": "Profile hot paths (Chain sync, X16RS). Use cpp-expert WASM for compute offload if exposing. Security: auth on RPC, input validation, no trust in peers (51% resistance via Beacon). Integrate security-auditor. Fairness in mining interfaces.",
            "god_tier_level": "10x: anticipate 51% , eclipse attacks, state bloat (HVM opt helps), regulatory (legal). Full observability, chaos (forks), formal (TLA+ for consensus if extending). Make node the trusted base for L1-3/HVM. Additive to official.",
            "deliverables": "Extended Rust crate/patch, Docker, monitoring stack, API extensions (HVM/L2/L3), docs, benchmarks (sync time, RPC latency), integration guides (with mining/HVM/layers), client deck (node as foundation for ecosystem).",
            "past_research": (past + " " + research)[:800],
            "handoffs": "hacash_mining_expert for Miner/PoWorker. hacash_hvm_expert for HVM node extensions. hacash_l1/l2/l3 for layer features. website-builder for node explorer/UI. devops for prod deploy. analytics for node metrics."
        }
        print("🖥️ HacashFullnodeExpert (GOD TIER): God-like production fullnode system delivered.")
        return god

    def god_tier_extend_7layer_with_hvm_l2(self, focus: str = "hvm+l2") -> Dict[str, Any]:
        """ULTRA: Exact extension points in the 7 layers for HVM (account abstraction, multi-lang contracts) and L2 CSP (channel state machine + settlement)."""
        return {
            "layers_to_touch": {
                "3_chain": "Add HVM state root + receipts root to block header. Extend chainstate with HVM account db (keyed by 20/32 byte addr).",
                "4_mint": "HVM gas fees + diamond contract interaction. Peg logic stays here but HVM can observe peg events.",
                "5_node": "Propagate HVM tx type + L2 channel update messages. Mempool priority for settlement tx.",
                "6_server": "New RPCs: hvm_call, hvm_estimate, csp_open_channel, csp_submit_update, csp_force_close. WebSocket for channel events.",
                "7_miner": "Template must include HVM state root + recent L2 settlement batch hash."
            },
            "exact_rust_extension_pattern": "In server/mod.rs: pub async fn hvm_call(&self, req: HvmCall) -> Result<HvmReceipt>. In chain/hvm.rs: pub fn apply_tx(&mut self, tx: &HvmTx) -> Result<Receipt> { self.state.apply_aa(tx)?; ... }",
            "hvm_aa_notes": "Native AA means every 'account' is a code+storage+nonce bundle. Paymasters, session keys, social recovery live in HVM not as EVM precompiles.",
            "l2_csp_notes": "Channels are off-chain multi-sig state machines. On-chain only on open, update disputes, and close. Ordered by CSP. Settlement to L1 is the finality.",
            "god_tier": "The fullnode is the single source of truth. Every extension must preserve the 7-layer separation and the PoW security of L1. Test reorgs with HVM tx + open channels.",
            "handoffs": "hacash_hvm_expert, hacash_l2_expert, hacash_mining_expert (for template changes), security-auditor."
        }

    def god_tier_production_fullnode_ops(self) -> Dict[str, Any]:
        """Production ops for a real Hacash full node used by pools, explorers, L2 operators."""
        return {
            "build": "cargo build --release --features fullnode  (or the exact crate from hacash repo).",
            "run": "hacash --config node.toml --data-dir /data/hacash  (set rpc bind, mining enable=false for pure fullnode, p2p bootstrap).",
            "docker": "FROM rust:1.80 as builder ... COPY . . ; cargo build --release ; FROM debian:bookworm-slim ; COPY --from=builder /target/release/hacash /usr/local/bin/ ; USER 1000",
            "monitoring": "Prometheus exporter on /metrics (height, hashrate_est, peer_count, mempool_size, hvm_gas_used, channel_settlements).",
            "backup": "Regular snapshot of chaindata + leveldb. Never delete without re-sync plan. Test restore quarterly.",
            "god_tier": "A production fullnode is 24/7 infrastructure. You ship the node, the exporter, the runbook, the chaos test that proves it survives partitions and reorgs, and the alert rules."
        }

# Register
hacash_fullnode_expert = HacashFullnodeExpert()
print("🖥️ HacashFullnodeExpert (GOD TIER) registered. Ready for sub_type='hacash_fullnode'. 7-layer Rust master, HVM/L2 extensions, production node ops.")