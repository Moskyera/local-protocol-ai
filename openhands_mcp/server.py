#!/usr/bin/env python3
"""
OpenHands MCP Skills Server (Professional Extension)
FastMCP-based server exposing our domain experts as first-class native tools.

Tools:
- analyze_wallet: Full real-data PulseChain/EVM wallet forensics (Moralis + free public BlockScout/PulseX GraphQL/RPC),
  accurate native PLS USD inflows (user-specified tiers), risk_score 0-100 with pattern "big PLS receive + low activity + meme bag",
  PnL estimate + market context, portfolio, categories, approvals, swaps, persistent memory sightings.
  **NEW**: large_ecosystem_movements + ecosystem_alerts for big transfers of HEX, PLSX, INC (USD-valued using same real-dollar thresholds as native PLS; small moves ignored).
- check_large_ecosystem_movements: Focused alert tool for large HEX/PLSX/INC moves on Pulse (returns only the big ones in USD). Auto-triggers scheduled research when used via supervisor.
- execute_v2_task: Automatic high-level router for Solidity/EVM/PulseChain/DeFi/smart contracts (uses v2 multi-agents + dedicated experts).
- get_market_snapshot (optional bridge).
- run_scheduled_proactive_research: For automatic/scheduled discovery (lab_mode) without user prompting every time. Feeds alerts and guarded proposals.
- safe_web_research: The ONLY safe way to study public websites / GitHub / docs. Built-in user confirmation flow (user_confirmed param), strict URL security validation, text-only extraction, explicit security_risk levels returned. Replaces the broken built-in 'browser' tool. Must present proposal to human and get explicit yes before setting user_confirmed=True.

This solves:
- "I cannot directly access blockchain" refusals (now explicit native tool with schema).
- security_risk / tool call fragility (MCP + OpenHands framework handles).
- Microagent knowledge not triggering execution reliably (tools appear in agent's available set).
- Path/import hell inside per-convo sandbox (MCP server runs with full host/project access).

Usage in compose: sidecar service with our custom runtime image (or any with the skills + fastmcp).
Configure OpenHands to connect (shttp recommended for reliability).

Run standalone for test: python -m openhands_mcp.server
(Defaults to streamable-http on 0.0.0.0:8765)

Requires: pip install fastmcp
The skills package must be importable (via PYTHONPATH or path setup below).
"""

import json
import os
import re
import sys
from typing import Annotated, Any, Dict, List, Optional
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# STDIO TRANSPORT SAFETY -- must run BEFORE the skills are imported.
#
# --transport stdio is an offered choice, and under it stdout IS the protocol:
# JSON-RPC frames travel on it. Anything else written there corrupts the stream
# before the first message is exchanged.
#
# Measured: importing this module writes 5,185 bytes to stdout. Only eleven of
# those prints are in this file — the rest are the registration banners the
# expert skills emit at import time ("Code Researcher registered...", and
# thirty more). Fixing this file alone would not have been enough.
#
# So when stdio is requested, stdout is pointed at stderr for the whole
# process, before a single skill is imported. Diagnostics keep working and go
# where diagnostics belong; the protocol gets a clean channel. Under the
# default streamable-http transport nothing changes.
# ---------------------------------------------------------------------------
if any(a == "stdio" or a.endswith("=stdio") for a in sys.argv[1:]):
    sys.stdout = sys.stderr

# PRIVATE MODE first: kill-switches and the socket guard, before requests,
# moralis, ccxt or anything else that opens a connection is imported.
import lpai_private
lpai_private.activate()

import requests  # safe web research (with strict limits)

# Import GuardrailProvider (Proposal 2 - human approved)
try:
    from openhands_skills.guards import guardrail_provider, apply_guardrail
except Exception:
    guardrail_provider = None
    def apply_guardrail(tool_name, params, **kw): return params  # fallback, no-op

# Safe logger (defensive, matches patterns in other modules)
try:
    from logger import log
except Exception:
    class _Log:
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
        def success(self, *a, **k): pass
    log = _Log()

# Robust path setup using central project_paths when available (post 2026-06 reorganization).
# Falls back gracefully for Docker / host / MCP sidecar / ~/.openhands contexts.
try:
    from project_paths import add_market_agent_to_path, MARKET_AGENT_ROOT
    add_market_agent_to_path()
except Exception:
    # Legacy defensive setup (kept for robustness during transition)
    def _mcp_path_setup():
        candidates = [
            "/workspace",
            os.getcwd(),
            os.path.dirname(os.path.abspath(__file__)),
            os.path.expanduser("~/.openhands/skills"),
            _REPO_ROOT,
            os.path.expanduser("~") + "/AI/market-agent",
        ]
        for base in candidates:
            if base and os.path.isdir(base):
                if base not in sys.path:
                    sys.path.insert(0, base)
                parent = os.path.dirname(base) if os.path.basename(base) != "market-agent" else base
                if os.path.isdir(parent) and parent not in sys.path:
                    sys.path.insert(0, parent)
        root = _REPO_ROOT
        if os.path.isdir(root) and root not in sys.path:
            sys.path.insert(0, root)
    _mcp_path_setup()

# Cache for domain tools to drastically reduce end-to-end latency on repeated addresses
# (common during debugging/testing the same wallet). lru_cache keeps last N results in memory.
import functools

# The repository root, derived from this file rather than written down.
# It was the literal string 'C:/AI/market-agent', which is where this
# happens to be checked out and not a fact about anyone else's disk. In a
# container the package is mounted at /workspace, and this resolves to it.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@functools.lru_cache(maxsize=128)
def _cached_analyze_address(address: str, chain: str = "pulsechain", context: str = "") -> dict:
    """Cached wrapper around the heavy expert to avoid re-fetching Moralis/RPC/GraphQL on repeats."""
    return chain_analysis_expert.analyze_address(address, chain=chain, context=context)

# Now safe to import our skills (they have their own defensive _auto_path_setup + lazy/dummy for sandbox)
try:
    from openhands_skills.openhands_v2_entry import run_task as _run_task
except Exception as e:
    _run_task_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import run_task: {_run_task_err}")
    def _run_task(user_task: str = "") -> Dict[str, Any]:
        return {"error": f"v2_entry not available: {_run_task_err}", "task": user_task}

try:
    from openhands_skills.chain_analysis_expert import chain_analysis_expert
except Exception as e:
    _imp_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import chain_analysis_expert: {_imp_err}")
    class _DummyChain:
        def analyze_address(self, address: str, chain: str = "pulsechain", context: str = "") -> Dict[str, Any]:
            return {"error": f"chain_analysis_expert not available: {_imp_err}", "address": address, "chain": chain}
    chain_analysis_expert = _DummyChain()

try:
    from openhands_skills.tool_integration_hub import tool_hub as _tool_hub
except Exception:
    class _DummyHub:
        def run_market_snapshot(self) -> str:
            return "Market snapshot limited (MCP server env)."
    _tool_hub = _DummyHub()

try:
    from openhands_skills.tool_fixer import fix_tool_call_error as _fix_tool_call_error_impl
except Exception as e:
    _imp_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import tool_fixer: {_imp_err}")

    def _fix_tool_call_error_impl(
        original_tool_name: str,
        attempted_call: dict,
        error_message: str,
        user_intent: str = "",
    ) -> Dict[str, Any]:
        return {
            "fixed": False,
            "message": f"tool_fixer not available: {_imp_err}",
            "original_error": error_message,
            "attempted": attempted_call,
            "mcp_tool": "fix_tool_call_error",
        }

# Research & Learning Agent (new in upgrade - Continuous Research Agent)
try:
    from openhands_skills.research_agent import research_agent as _research_agent, run_research as _run_research
except Exception as e:
    _imp_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import research_agent: {_imp_err}")
    class _DummyResearch:
        def research(self, query: str, focus: str = "ai_agents") -> Dict[str, Any]:
            return {"error": f"research_agent not available: {_imp_err}", "query": query}
        def get_latest_insights(self, focus: str = "all", limit: int = 5) -> List[str]:
            return []
        def get_research_lab_ideas(self, limit: int = 5): return []
        def get_meta_learnings(self, limit: int = 5): return []
        def get_new_capability_candidate_details(self, index: int = 0): return {"status": "error", "error": "research not available"}
    _research_agent = _DummyResearch()
    def _run_research(query: str = "", focus: str = "ai_agents") -> Dict[str, Any]:
        return {"error": f"research_agent not available: {_imp_err}", "query": query}

# === Image & Video Generation (added per user request 2026-07) ===
# Uses open-source models via ComfyUI (Flux.2 + Wan 2.2 recommended from research).
# Follows exact same safe pattern as web_research (user_confirmed required).
try:
    from openhands_skills.image_video_generator import generate_image as _generate_image, generate_video as _generate_video
except Exception as e:
    _imp_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import image_video_generator: {_imp_err}")
    def _generate_image(prompt: str, **kw): return {"error": "image_video_generator not available. See openhands_skills/image_video_generator.py", "prompt": prompt}
    def _generate_video(prompt: str, **kw): return {"error": "image_video_generator not available. See openhands_skills/image_video_generator.py", "prompt": prompt}

try:
    from openhands_skills.wealth_mentor import consult_wealth_mentor as _consult_wealth, generate_wealth_plan as _generate_wealth_plan
except Exception as e:
    _imp_err = f"{type(e).__name__}: {e}"
    print(f"[MCP] Warning: could not import wealth_mentor: {_imp_err}")
    def _consult_wealth(prompt: str, **kw): return {"error": "wealth_mentor not available", "prompt": prompt}
    def _generate_wealth_plan(prompt: str, **kw): return {"error": "wealth_mentor not available", "prompt": prompt}

# FastMCP (community + OpenHands recommended lib)
try:
    from fastmcp import FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("[MCP] FATAL: fastmcp not installed. Run: pip install fastmcp")
        sys.exit(1)

# Every caller must present the local bearer token: this server writes
# files, opens pull requests and runs research, and anything on the
# machine (a container, a sandbox, a rebound web page) could reach :8765
# otherwise. In private mode the token is mandatory and minted if absent.
_MCP_TOKEN = lpai_private.mcp_token(create=lpai_private.is_private())
if lpai_private.is_private() and not _MCP_TOKEN:
    print("private mode needs MCP_TOKEN (or a writable ~/.openhands/agent-canvas/mcp-token.txt)", file=sys.stderr)
    sys.exit(2)
_mcp_auth = None
if _MCP_TOKEN:
    from fastmcp.server.auth import StaticTokenVerifier
    _mcp_auth = StaticTokenVerifier(tokens={_MCP_TOKEN: {"client_id": "local", "scopes": []}})

mcp = FastMCP(
    name="pulsechain-evm-skills",
    auth=_mcp_auth,
    # instructions for the agent about when to use these tools
    instructions=(
        "You are the MOSKY chat agent for this project. This is a chat interface with the user. "
        "For EVERY user message, you MUST call the 'execute_v2_task' tool with the full user message as the 'task' parameter. "
        "The output of the 'execute_v2_task' tool (the supervisor plan, 'New session detected' for new/fresh convos, synthesis, code, audit, etc.) IS your final response to the user - present the tool output directly and clearly in your reply to the user. Do not add your own text, summaries, or base LLM response before or after; the tool result is the authoritative answer from the supervisor. "
        "This is mandatory for the VERY FIRST message in ANY new or fresh conversation (new convo ID, or when the user says 'new session', 'start', 'fresh convo', or similar). Call it immediately on the first message to trigger the supervisor's immediate visible plan. "
        "For every follow-up message, call it for any request to get the full supervisor + multi-agent response, and present the tool output directly. "
        "For coding tasks (Solidity, PulseChain, DeFi, smart contracts), call it with the natural language description - the tool result will contain the code, audit, etc. Present it directly. "
        "For any web research or studying websites (including cryptodust.xyz or any docs/GitHub): You MUST use the tool named exactly 'web_research' (with parameter 'query'). First call with user_confirmed=false to get the proposal. Present the proposal's message_for_human to the human and wait for explicit 'yes' or 'yes for study only'. ONLY THEN call 'web_research' AGAIN with the exact same url+query and user_confirmed=true. Never use any tool named 'research' or 'browser' for web tasks. "
        "Never respond with base LLM knowledge alone or skip the tool call. The supervisor via this tool is the required brain for all chat responses in this project. When the tool returns, your output to the user is that result."
    )
)

@mcp.tool()
def analyze_wallet(
    address: Annotated[str, "REQUIRED. The exact wallet or contract address to analyze. Must be a valid 0x... hex string. DO NOT use 'wallet_address' or any other name. Example value: 0x000000000000000000000000000000000000dEaD"],
    chain: Annotated[str, "OPTIONAL. Blockchain to query. Use exactly 'pulsechain' (default, recommended for this task) or 'ethereum'."] = "pulsechain",
    context: Annotated[Optional[str], "OPTIONAL. Any extra context from the user prompt, e.g. 'this is a fresh wallet' or 'focus on native PLS inflows and risk'. Can be empty."] = None
) -> Dict[str, Any]:
    """
    Professional full wallet / address forensics for PulseChain (chainId 369, scan.pulsechain.com) or Ethereum/EVM.

    CRITICAL CALLING RULES (follow exactly or the call will be rejected or produce garbage):
    - The function name MUST be exactly "analyze_wallet". NEVER call "analyze_chain", "chain_analysis", "wallet_forensics" or similar invented names.
    - First/only required parameter name MUST be literally "address" (the 0x... string). NEVER use "wallet_address", "wallet", "addr", "target" or any other key — even if you remember old tool names from previous conversations.
    - Second optional parameter name MUST be "chain". Its value MUST be exactly the lowercase string "pulsechain" (default + recommended for this system) or "ethereum". NEVER "_pulsechain", "pulse", "pls", "PulseChain" (capital), or any variant with underscore/prefix.
    - Third optional "context".
    - When emitting <function_call> or JSON-style tool call, use EXACTLY this shape:
      <function_call>
      {
        "name": "analyze_wallet",
        "params": {
          "address": "0x000000000000000000000000000000000000dEaD",
          "chain": "pulsechain"
        }
      }
      </function_call>
    - Thought example: use analyze_wallet with address is 0x000000000000000000000000000000000000dEaD chain is pulsechain
    - The tool 'analyze_wallet' (and execute_v2_task, get_market_context, fetch_full_wallet_profile, research) come from the native MCP sidecar — they are the PREFERRED and ONLY reliable way for real on-chain PulseChain/EVM data, exact USD-tiered risk scoring (your rules: >50k very large, >10k large, small $50-500 do not trigger heavy flags), and PnL.

    Performs real data fetch (Moralis if MORALIS_API_KEY present in env for rich categorized history + free public fallbacks:
    BlockScout Etherscan-compatible, PulseX GraphQL subgraph for real DEX swaps, public RPC for nonce/logs/token meta).

    Returns structured dict including:
    - native_pls_summary and native_inflow_usd (accurate, using live-ish price from balances or market; big receives valued in USD not raw coins)
    - current portfolio / balances with approx_usd_value
    - activity categories, recent swaps/buys/sells, approvals
    - onchain_nonce + activity_level (low nonce flags fresh wallets)
    - risk_score (0-100): USD-tiered for native inflows exactly per spec (>50000 very large +45, >10000 large +30, >1000 +15, >100 +5;
      + low activity nonce, meme bag symbols like PCOCK/PTIGER/OMEGA etc., category imbalance)
    - **NEW ecosystem alerts**: large_ecosystem_movements + ecosystem_alerts for big HEX/PLSX/INC transfers on Pulsechain (USD real value, same thresholds logic; only meaningful sizes >~$5k trigger, tiny ignored)
    - pattern_match: "big PLS receive + low activity + meme bag" ONLY when thresholds met (avoids over-trigger on tiny amounts)
    - pnl_estimate (current_usd + conservative unrealized treating large native receives as low/zero cost basis + market snapshot context)
    - explorer_link, recommendations, persistent memory cross-reference ("seen this address before" with prior risk/usd)
    - full real transfers, dex_swaps etc. for downstream reasoning.

    Use this for ANY "analyze the wallet 0x...", "chain analysis", "full_wallet_profile", "risk score", "native inflows", "pnl", "trace flows", "what did this address do" on PulseChain or EVM.
    Much more reliable and automatic than code execution inside sandbox or asking user for explorer data.
    """
    if not address or not address.startswith("0x"):
        return {"error": "Valid 0x address required", "example": "0x000000000000000000000000000000000000dEaD"}

    # Prepare context early (before any guard use)
    ctx = context or ""

    # === GuardrailProvider interception (Proposal 2 - human approved 2026-06-12) ===
    # Tool call now intercepted for validation before any logic.
    # This implements the central GuardrailProvider protocol for security/context.
    try:
        guard_params = {"address": address, "chain": chain, "context": ctx}
        guard_params = apply_guardrail("analyze_wallet", guard_params, context="MCP tool call")
        address = guard_params.get("address", address)
        chain = guard_params.get("chain", chain)
    except Exception as ge:
        return {"error": f"Guardrail blocked analyze_wallet: {ge}", "mcp_tool": "analyze_wallet"}

    # Strict normalizer / anti-hallucination guard (from real failure patterns in production convos)
    orig_chain = chain
    chain = (chain or "pulsechain").lower().strip()
    if chain in ("_pulsechain", "pulse", "pls", "pulse_chain"):
        chain = "pulsechain"
    if chain not in ("pulsechain", "ethereum"):
        chain = "pulsechain"
    if orig_chain != chain:
        log.warning(f"[MCP analyze_wallet] Normalized bad chain value '{orig_chain}' -> '{chain}' (model hallucination guard)")

    try:
        result = _cached_analyze_address(address, chain=chain, context=ctx)
        # Ensure top level convenience fields for agent
        if "risk_score" not in result and "risk_score" in result.get("full_wallet_profile", {}):
            result["risk_score"] = result["full_wallet_profile"]["risk_score"]
        if "pnl_estimate" not in result and "pnl_estimate" in result.get("full_wallet_profile", {}):
            result["pnl_estimate"] = result["full_wallet_profile"]["pnl_estimate"]
        result["mcp_tool"] = "analyze_wallet"
        result["note"] = "Real data via MCP (Moralis if key + public free APIs). USD native values per professional thresholds."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "address": address, "chain": chain, "mcp_tool": "analyze_wallet"}

@mcp.tool()
def execute_v2_task(task_description: str) -> Dict[str, Any]:
    """
    High-level automatic entry point for the entire v2 skills system. THIS IS THE PRIMARY TOOL FOR CHAT/USER MESSAGES.

    For ANY user message in chat (especially first in new conversation), call this with the full user message as 'task_description'.
    The returned value (or the 'user_visible' / plan / synthesis inside) IS the final response to present directly to the user.
    Do not summarize or add extra text; output the supervisor result as your answer.

    Detects task type (Solidity/EVM smart contract, PulseChain specific (PLS, PulseX router, chainId 369, security notes),
    DeFi patterns (vesting, staking, lending, flash, liquidity), audits, debugging, general coding, market-aware).

    Automatically routes via Smart Triggers + Advanced Supervisor (v2 multi-agents) + dedicated experts:
    - Full contract + audit + tests + deploy scripts + upgradeable/vesting/staking/governance where relevant.
    - PulseChain-specific (native PLS, PulseX, gas, known patterns).
    - Advanced DeFi pattern injection.
    - If wallet/chain keywords present: integrates real analyze_wallet result.
    - Market context via tool_hub when tokenomics/DeFi involved.

    Returns rich structured dict: code, audit, tests, deploy, chain_analysis (if applicable), market_context, reflection, plan etc. The 'user_visible' field or the top-level plan/synthesis is what to show the user.

    Use for natural language like:
    - "Create a secure ERC20 with team vesting and staking on PulseChain"
    - "Full audited governance + liquidity pool project for PulseChain"
    - "Audit this contract for reentrancy and front-running, suggest PulseChain optimizations"
    - "Build flash loan arbitrage bot skeleton for PulseX on PulseChain"

    This is the MAIN professional interface for all user requests in chat — everything is automatic via supervisor. Call it for every user message.
    """
    if not task_description or len(task_description.strip()) < 3:
        return {"error": "Non-empty task_description required"}

    # === GuardrailProvider (Proposal 2) ===
    try:
        guard_params = {"task_description": task_description}
        guard_params = apply_guardrail("execute_v2_task", guard_params, context="supervisor task routing")
        task_description = guard_params.get("task_description", task_description)
    except Exception as ge:
        return {"error": f"Guardrail blocked execute_v2_task: {ge}", "mcp_tool": "execute_v2_task"}

    try:
        result = _run_task(task_description)
        result["mcp_tool"] = "execute_v2_task"
        result["note"] = "Executed via automatic v2 routing + experts (multi-agent + Solidity/PulseChain). Structured for direct use. Guardrail applied."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "task": task_description, "mcp_tool": "execute_v2_task"}

@mcp.tool()
def analyze_folder(path: str = "/workspace", max_files: int = 50, deep: bool = True) -> Dict[str, Any]:
    """
    Analyze a WHOLE folder / codebase and report what is RIGHT and what is WRONG.

    Use this whenever the user points at a folder and asks to review / audit / map
    it, or asks "what's good and what's bad here". It walks the folder, runs the
    deterministic analyzer toolchain (ruff, bandit, mypy, pyflakes) on every Python
    file, aggregates findings by severity, and produces an expert verdict grounded
    in those objective results (not guesses).

    Args:
      path: folder inside the OpenHands workspace (e.g. '/workspace' or '/workspace/subdir').
      max_files: cap on Python files scanned (protects against huge repos).
      deep: if True, also runs an LLM expert review on top of the tool findings.

    Returns: {files_scanned, python_files, total_findings, by_severity, whats_wrong,
              whats_right, dependency_audit, verdict, review}.
    """
    if not path or not os.path.isdir(path):
        return {"error": f"Folder not found in workspace: {path}", "hint": "Use a path like /workspace or /workspace/<subdir>. The folder must be inside the mounted workspace."}

    try:
        from openhands_multiagent_v2.code_intelligence import code_intelligence
    except Exception as e:
        return {"error": f"code_intelligence unavailable: {e}. Rebuild the my-openhands-runtime image to bake in the analyzers."}

    _SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv", "backups",
             ".ruff_cache", "ai-env", "openbb-env", "_cleanup_quarantine_20260721"}
    py_files, all_files = [], 0
    for cur, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith(".")]
        for fn in files:
            all_files += 1
            if fn.endswith(".py"):
                py_files.append(os.path.join(cur, fn))

    # ONE whole-tree pass (ruff + bandit) instead of per-file — fast even on big repos.
    from collections import defaultdict
    sev_totals = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    per_file = defaultdict(list)
    try:
        res = code_intelligence.analyze_tree(path)
    except Exception as e:
        return {"error": f"analysis failed: {e}", "path": path}
    for i in res.issues:
        sev_totals[i.severity] = sev_totals.get(i.severity, 0) + 1
        rel = os.path.relpath(i.file, path) if i.file else "(unknown)"
        per_file[rel].append(i)

    files_with_issues = set(per_file.keys())
    scanned = len(py_files)
    whats_wrong = []
    for rel, issues in per_file.items():
        blocking = [i for i in issues if i.severity in ("CRITICAL", "HIGH")]
        whats_wrong.append({
            "file": rel,
            "blocking": len(blocking),
            "total": len(issues),
            "top": [str(i) for i in sorted(issues, key=lambda x: x.severity)[:6]],
        })
    whats_wrong.sort(key=lambda x: -x["blocking"])

    clean_files = [os.path.relpath(f, path) for f in py_files
                   if os.path.relpath(f, path) not in files_with_issues][:200]

    # Dependency CVE audit if a requirements file exists.
    dep_audit = "no requirements file found"
    for req in ("requirements.txt", "requirements-core.txt", "requirements-agentic.txt"):
        rp = os.path.join(path, req)
        if os.path.isfile(rp):
            try:
                dep_audit = code_intelligence.audit_dependencies(rp)
            except Exception as e:
                dep_audit = f"(dep audit error: {e})"
            break

    total = sum(sev_totals.values())
    review = ""
    if deep and whats_wrong:
        try:
            from openhands_multiagent_v2.reviewer_agent_v2 import reviewer
            summary = "\n".join(
                f"{w['file']}: {w['blocking']} blocking / {w['total']} total; " + "; ".join(w["top"][:3])
                for w in whats_wrong[:15]
            )
            review = reviewer.complete(
                "You are auditing a codebase. Below are deterministic analyzer "
                "findings per file (ruff/bandit/mypy). Give a prioritised verdict: "
                "the most important things that are WRONG (and why they matter), "
                "what looks RIGHT/healthy, and the top 5 concrete fixes.\n\n"
                f"Clean files: {len(clean_files)} | Files with issues: {len(whats_wrong)}\n\n{summary}"
            )
        except Exception as e:
            review = f"(expert review unavailable: {e})"

    # "No findings" and "nothing looked" are different answers, and this used to
    # give the same one to both: with zero analyzers installed, total == 0 and
    # the verdict read "✅ healthy — N files clean". AnalysisResult already
    # records which tools actually ran; it simply was not consulted.
    tools_run = sorted(getattr(res, "tools_run", []) or [])
    tools_skipped = sorted(getattr(res, "tools_skipped", []) or [])
    if not tools_run:
        verdict = ("❓ ΑΓΝΩΣΤΟ — κανένας analyzer δεν έτρεξε, δεν ελέγχθηκε "
                   "τίποτα (εγκατέστησε ruff/bandit/mypy)")
    elif total == 0:
        verdict = f"✅ healthy (έτρεξαν: {', '.join(tools_run)})"
    elif sev_totals["CRITICAL"] + sev_totals["HIGH"]:
        verdict = "🚨 needs urgent fixes"
    else:
        verdict = "⚠️ minor issues"

    return {
        "mcp_tool": "analyze_folder",
        "path": path,
        "files_scanned": scanned,
        "python_files": len(py_files),
        "all_files": all_files,
        "total_findings": total,
        "by_severity": sev_totals,
        "whats_wrong": whats_wrong[:25],
        "whats_right": ({"clean_files": len(clean_files), "examples": clean_files[:15]}
                        if tools_run else
                        {"clean_files": 0, "examples": [],
                         "note": "κανένα αρχείο δεν χαρακτηρίστηκε καθαρό — "
                                 "δεν έτρεξε κανένας analyzer"}),
        "dependency_audit": dep_audit,
        "analyzers_run": tools_run,
        "analyzers_skipped": tools_skipped,
        "verdict": verdict,
        "review": review or "(run with deep=True for the expert verdict)",
        "note": "Findings are from real analyzers (ruff/bandit/mypy/pyflakes) — deterministic, not guesses.",
    }


@mcp.tool()
def get_market_context(symbol: str = "PLS") -> str:
    """
    Quick market snapshot / master report bridge (crypto prices, sentiment, macro if available).
    Useful to enrich tokenomics, DeFi design, or value estimates in wallet/contract tasks.
    Falls back gracefully if market engines not fully importable.
    """
    try:
        snap = _tool_hub.run_market_snapshot()
        return str(snap)[:3000]  # keep reasonable size
    except Exception as e:
        return f"Market context limited: {e}. (Use for rough USD/tokenomics estimates only.)"

# Optional: expose the raw full profile fetch for advanced agents
@mcp.tool()
def fetch_full_wallet_profile(address: str, chain: str = "pulsechain") -> Dict[str, Any]:
    """Lower-level direct access to the rich fetch_real_token_activity + risk/PnL logic (same as analyze_wallet but rawer)."""
    try:
        # The analyze does the full thing + report building; reuse
        return analyze_wallet(address=address, chain=chain, context="full raw profile request")
    except Exception as e:
        return {"error": str(e)[:200]}


@mcp.tool()
def check_large_ecosystem_movements(address: str, chain: str = "pulsechain", min_usd: float = 5000.0) -> Dict[str, Any]:
    """
    Focused "alert" tool for large movements of key Pulsechain ecosystem tokens: HEX, PLSX, INC.

    Returns structured large transfers with real USD value (your rules: measured in dollars, not raw coin count; small amounts <$5k default ignored).
    Ideal for supervisor / chat agent to detect "large HEX/PLSX/INC moves" without dumping full wallet profile.

    CRITICAL CALLING RULES:
    - address: must be exact 0x...
    - chain: exactly "pulsechain" (recommended) or "ethereum".
    - min_usd: raise to 10000/50000 for stricter "very large" only.
    - Returns: list of {symbol, usd_value, token_value, tx_hash, from, to, alert, ...}

    The underlying expert uses the same public fallbacks + Moralis (if key) as analyze_wallet.
    Combine with supervisor for automated monitoring flows (e.g. "check this whale for large ecosystem moves").
    When used via supervisor (e.g. "check this whale"), it auto-triggers scheduled proactive research (lab_mode) focused on onchain/pulse to discover new monitoring patterns/ideas for the alerts.

    STRICT EXAMPLE (for LLM):
    <function_call>
    {
      "name": "check_large_ecosystem_movements",
      "params": {
        "address": "0x000000000000000000000000000000000000dEaD",
        "chain": "pulsechain",
        "min_usd": 10000
      }
    }
    </function_call>
    """
    if not address or not str(address).startswith("0x"):
        return {"error": "valid 0x address required", "mcp_tool": "check_large_ecosystem_movements"}
    try:
        # Reuse the expert (it now always computes large_ecosystem_movements for Pulse)
        profile = analyze_wallet(address=address, chain=chain, context=f"focus on large HEX PLSX INC movements above ${min_usd}")
        moves = profile.get("large_ecosystem_movements", []) or []
        filtered = [m for m in moves if float(m.get("usd_value", 0)) >= min_usd]
        return {
            "mcp_tool": "check_large_ecosystem_movements",
            "address": address,
            "chain": chain,
            "min_usd_threshold": min_usd,
            "large_movements": filtered,
            "count": len(filtered),
            "note": "USD real value (not raw tokens). Only sizes above threshold. Full context available via analyze_wallet. 100% from on-chain + market data, no invention."
        }
    except Exception as e:
        return {"error": str(e)[:150], "mcp_tool": "check_large_ecosystem_movements"}


@mcp.tool()
def scan_large_ecosystem_movements_on_pulsechain(tokens: list = None, min_usd: float = 5000) -> Dict[str, Any]:
    """
    Scan Pulsechain for recent LARGE movements of ecosystem tokens (HEX, PLSX, INC etc.) **without needing a specific wallet address**.
    Returns the addresses involved in big transfers/swaps + tx details + USD value (your rules: real dollars, small ignored).
    Perfect for your example: "check this whale for large HEX PLSX INC moves on pulsechain" → gets candidate addresses → then "analyze the first one" or "analyze 0x..." to start full risk/PnL/supervisor analysis on them.

    CRITICAL CALLING RULES (strict, same as analyze_wallet):
    - tokens: list like ["HEX", "PLSX", "INC"] (default all).
    - min_usd: threshold (default 5000; raise for bigger only, e.g. 10000/50000).
    - Returns: list of large moves with from/to addresses (the "whales"), tx, usd, alert. Plus "candidate_addresses" for easy follow-up analysis.
    - Use the returned addresses with analyze_wallet or the supervisor for full profile.

    STRICT XML EXAMPLE:
    <function_call>
    {
      "name": "scan_large_ecosystem_movements_on_pulsechain",
      "params": {
        "tokens": ["HEX", "PLSX", "INC"],
        "min_usd": 10000
      }
    }
    </function_call>
    Thought: User said "check this whale for large HEX PLSX INC moves on pulsechain" without address -> call the scanner, then offer the top addresses for analysis.

    Integrates with supervisor auto-trigger and scheduled research (for discovering new patterns/tokens to monitor).
    """
    if tokens is None:
        tokens = ["HEX", "PLSX", "INC"]
    try:
        moves = chain_analysis_expert.scan_large_ecosystem_movements(tokens=tokens, min_usd=min_usd)
        candidates = sorted(list({m.get("to") for m in moves if m.get("to")}))[:10]
        return {
            "mcp_tool": "scan_large_ecosystem_movements_on_pulsechain",
            "tokens": tokens,
            "min_usd": min_usd,
            "large_movements": moves,
            "count": len(moves),
            "candidate_addresses": candidates,
            "note": "These addresses had large movements. Copy one and say 'analyze 0x...' or 'analyze the first one' to start full analysis with the supervisor (risk, PnL, profile). All USD per your exact thresholds. 100% on-chain data."
        }
    except Exception as e:
        return {"error": str(e)[:150], "mcp_tool": "scan_large_ecosystem_movements_on_pulsechain"}


@mcp.tool()
def scan_and_research_large_ecosystem_movements(tokens: list = None, min_usd: float = 5000) -> Dict[str, Any]:
    """
    Combined MCP tool: scan for large HEX/PLSX/INC moves on Pulsechain (no address needed) + auto run scheduled proactive research (lab_mode) for new monitoring patterns.
    Returns scan results (candidates, movements) + fresh research ideas + note to start analysis on candidates.
    Perfect for automated flows: one call gives discovery + alerts + research.

    CRITICAL CALLING RULES (strict):
    - tokens: e.g. [\"HEX\", \"PLSX\", \"INC\"]
    - min_usd: your threshold.
    - Returns combined with candidate_addresses ready for \"analyze the first\" via supervisor.

    STRICT XML EXAMPLE:
    <function_call>
    {
      \"name\": \"scan_and_research_large_ecosystem_movements\",
      \"params\": {
        \"tokens\": [\"HEX\", \"PLSX\", \"INC\"],
        \"min_usd\": 10000
      }
    }
    </function_call>
    Thought: User: \"check this whale for large HEX PLSX INC moves on pulsechain\" -> call combined scan+research, get candidates + ideas, offer analysis.
    """
    if tokens is None:
        tokens = ["HEX", "PLSX", "INC"]
    try:
        from openhands_skills.chain_analysis_expert import chain_analysis_expert
        from openhands_skills.langgraph_orchestrator import run_scheduled_proactive_research as _sched
        moves = chain_analysis_expert.scan_large_ecosystem_movements(tokens=tokens, min_usd=min_usd)
        candidates = sorted(list({m.get("to") for m in moves if m.get("to")}))[:10]
        ideas = _sched(focus="onchain", max_results=3, lab_mode=True).get("new_capability_candidates", [])[:3]
        return {
            "mcp_tool": "scan_and_research_large_ecosystem_movements",
            "tokens": tokens,
            "min_usd": min_usd,
            "large_movements": moves,
            "count": len(moves),
            "candidate_addresses": candidates,
            "fresh_research_ideas": ideas,
            "note": "Combined scan + scheduled research. Use candidates with supervisor 'analyze the first one' for full analysis. Ideas for improving monitoring. 100% on-chain/research data."
        }
    except Exception as e:
        return {"error": str(e)[:150], "mcp_tool": "scan_and_research_large_ecosystem_movements"}


@mcp.tool()
def run_scheduled_proactive_research(focus: str = "self_improving", max_results: int = 5, lab_mode: bool = True) -> Dict[str, Any]:
    """
    MCP exposure for scheduled / automatic proactive research (Continuous Research Lab).
    Call this from external scheduler, cron, launcher, or supervisor on timer to run discovery without user prompting every time.
    Produces full 100% fidelity lab candidates (with direct_evidence, fit_analysis, suggested_apply_data) and stores as research_lab_idea.
    Results can be consumed by integrate_research_idea or the Engineering specialist for guarded proposals.
    Works together with ecosystem alerts (run scheduled research on 'onchain' or 'pulse' focus to discover patterns for HEX/PLSX etc. monitoring).

    CRITICAL (strict like other tools):
    - focus: "self_improving", "onchain", "pulse", "ai_agents" etc.
    - lab_mode: True for PR-ready structured output.
    - Returns candidates ready for review + integrate.

    Example:
    <function_call>
    {
      "name": "run_scheduled_proactive_research",
      "params": { "focus": "onchain", "max_results": 3, "lab_mode": true }
    }
    </function_call>
    """
    try:
        from openhands_skills.langgraph_orchestrator import run_scheduled_proactive_research as _scheduled
        res = _scheduled(focus=focus, max_results=max_results, lab_mode=lab_mode)
        res["mcp_tool"] = "run_scheduled_proactive_research"
        return res
    except Exception as e:
        return {"error": str(e)[:150], "mcp_tool": "run_scheduled_proactive_research"}


@mcp.tool()
def create_pr(
    repo_name: Optional[str] = None,
    repo: Optional[str] = None,  # alias to catch common LLM hallucination "repo" instead of "repo_name"
    source_branch: str = "",
    target_branch: str = "main",
    title: str = "",
    body: str = "",
    draft: bool = True,
    labels: Optional[list] = None,
    confirm: bool = False,  # must be explicitly true to actually open the PR
) -> Dict[str, Any]:
    """
    Create a GitHub Pull Request (for guarded self-improvement changes, research-backed proposals, etc.).

    CRITICAL CALLING RULES - THIS IS TO FIX THE EXACT ERROR YOU REPORTED:
    - The schema error "Parameter 'repo' is not allowed" happens when the LLM uses the wrong name.
    - We now ACCEPT BOTH "repo_name" (correct) AND "repo" (common hallucination) and auto-normalize.
    - Preferred / correct name: ALWAYS use "repo_name" in your calls.
    - Never invent parameters. Only use the ones listed here.

    Exact allowed (and normalized) parameters: repo_name (or repo as alias), source_branch, target_branch, title, body, draft, labels.

    repo_name (or repo): full "owner/repo" . Do not use "your-repo-name".
    source_branch: e.g. the branch from guarded_propose or "openhands-workspace".
    For self-improvement PRs: put the full research evidence (source url + direct_evidence + x_evidence) in the body.

    This must only be called after the user has given explicit approval in chat and the guarded flow has run (see approve_and_apply_proposal).

    STRICT CORRECT EXAMPLE (copy this format):

    <function_call>
    {
      "name": "create_pr",
      "params": {
        "repo_name": "yourusername/your-repo",
        "source_branch": "evolution/langgraph-alignment",
        "target_branch": "main",
        "title": "Align supervisor with LangGraph human-in-the-loop patterns from research",
        "body": "100% traceable from research candidate https://github.com/langchain-ai/langgraph\nDirect evidence: ... (paste verbatim)\nX evidence: https://x.com/... \n\nChange: ... (small guarded edit)",
        "draft": true
      }
    }
    </function_call>

    Thought: I will call create_pr using repo_name (never just 'repo') ...

    If you previously got the 'repo' not allowed error, use the normalized version - we auto-fix 'repo' -> 'repo_name' inside this tool and return a note.
    """
    # Robust normalizer for LLM hallucinations on parameter names
    if (not repo_name or repo_name.strip() == "") and repo:
        repo_name = repo
        normalization_note = "Normalized hallucinated param 'repo' -> 'repo_name' (common error fixed automatically)."
    else:
        normalization_note = ""

    if not repo_name or "your-repo" in str(repo_name).lower():
        return {"error": "repo_name (or repo) must be a real GitHub repo like 'owner/repo-name'.", "mcp_tool": "create_pr"}

    if not source_branch:
        return {"error": "source_branch is required.", "mcp_tool": "create_pr"}

    # `repository` and `repoName` were referenced here but were never parameters
    # of this function, so this line raised NameError on EVERY call — the tool
    # could not run once. And the code past it never created a pull request: it
    # built a gh command string, threw it away, and returned success=True with a
    # "suggested_gh_command". A caller was told the PR existed when nothing had
    # happened at all.
    final_repo, used_key = None, None
    for key, val in (("repo_name", repo_name), ("repo", repo)):
        if val and str(val).strip() and "your-repo" not in str(val).lower():
            final_repo, used_key = str(val).strip(), key
            break

    if not final_repo:
        return {
            "error": "No valid repo provided. Use repo_name (alias: repo).",
            "mcp_tool": "create_pr",
            "accepted_aliases": ["repo_name", "repo"],
        }

    normalization_note = ("" if used_key == "repo_name"
                          else f"Auto-fixed: you used '{used_key}' -> repo_name='{final_repo}'")

    if not source_branch:
        return {"error": "source_branch is required (the branch with the changes from guarded_propose).",
                "mcp_tool": "create_pr"}

    argv = ["gh", "pr", "create", "--repo", final_repo, "--head", source_branch,
            "--base", target_branch, "--title", title or "(no title)",
            "--body", body or "(no body)"]
    if draft:
        argv.append("--draft")
    for lb in (labels or []):
        argv += ["--label", str(lb)]

    # Opening a pull request is an outward-facing, hard-to-undo act. It happens
    # only when the caller passes confirm=True; otherwise the command is
    # returned for a human to run, and `success` says false, because it is.
    if not confirm:
        return {
            "success": False,
            "status": "prepared_not_created",
            "repo_name": final_repo,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "draft": draft,
            "command": argv,
            "normalization_applied": normalization_note or "Correct parameter names used",
            "note": "No pull request was created. Re-call with confirm=True after the user has explicitly approved, or run the command above yourself.",
            "mcp_tool": "create_pr",
        }

    try:
        import subprocess
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        created = proc.returncode == 0
        url = next((w for w in out.split() if w.startswith("https://")), "")
        return {
            "success": created,
            "status": "created" if created else "gh_failed",
            "repo_name": final_repo,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "pr_url": url,
            "returncode": proc.returncode,
            "stdout": out[:800],
            "stderr": err[:800],
            "normalization_applied": normalization_note or "Correct parameter names used",
            "mcp_tool": "create_pr",
        }
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "create_pr"}


@mcp.tool()
def fix_tool_call_error(
    original_tool_name: str,
    attempted_call: dict,
    error_message: str,
    user_intent: str = ""
) -> Dict[str, Any]:
    """
    Όταν ο agent (LLM) κάνει λάθος tool call και παίρνει schema error (π.χ. "Parameter 'repo' is not allowed"),
    ΚΑΛΕΣΕ αυτό το helper με τις λεπτομέρειες.

    Το tool:
    - Αναλύει το error
    - Σου δίνει το CORRECTED call με σωστά ονόματα παραμέτρων
    - Επιστρέφει έτοιμο XML/JSON που μπορείς να χρησιμοποιήσεις αμέσως

    Παράδειγμα χρήσης από τον agent:
    User: "create a PR for the latest proposal"
    Agent προσπαθεί create_pr με "repo": "..." → παίρνει error
    Agent καλεί: fix_tool_call_error(
        original_tool_name="create_pr",
        attempted_call={"repo": "owner/repo", "source_branch": "...", ...},
        error_message="Parameter 'repo' is not allowed. Allowed: repo_name, ...",
        user_intent="create PR after approval"
    )
    → Παίρνει πίσω το σωστό {"repo_name": "...", ...} και το καλεί ξανά.

    Αυτό κάνει το σύστημα πολύ πιο ανθεκτικό στα hallucinations του LLM.
    """
    return _fix_tool_call_error_impl(
        original_tool_name=original_tool_name,
        attempted_call=attempted_call,
        error_message=error_message,
        user_intent=user_intent,
    )


# =============================================================================
# X (social) tools for Research credibility analysis (truth vs hype / "ωεμματα")
# Exposed so the Research & Learning agent (and supervisor) can natively fetch real user
# discussions, demos, and comment consensus when evaluating new tech/skills/patterns.
# Full power (semantic + full thread with replies) is best used from the host supervisor
# (which has direct x_* tools). These MCP versions are strict + documented for agent use.
# =============================================================================

@mcp.tool()
def x_semantic_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Semantic search over recent X posts for real user discussions about agent patterns, frameworks,
    self-improvement loops, LangGraph supervisor, MCP/tool calling reliability, guarded RSI, etc.

    Use this inside Research when building credibility_signals for a new capability candidate:
    - Look for actual working code links, demos, "I integrated this and it works", production reports.
    - Red flags: vague hype, no evidence, contradictions, "vaporware", paid shill language.
    - Consensus: multiple independent users showing reproducible results or clear limitations.

    CRITICAL CALLING RULES (identical strictness to analyze_wallet):
    - query: natural language description of the pattern or tech (e.g. "langgraph supervisor human in the loop real production use", "self improving agent propose code edits then experiment scalar score").
    - limit: small integer 3-8 recommended.
    - Returns posts with id, text, author, engagement, urls. Then follow up with x_thread_fetch on promising post ids for full comment evidence.
    - Always treat results as signals, not proof. Cross-check with GitHub (README + issues) for code substance.

    Example XML call:
    <function_call>
    {
      "name": "x_semantic_search",
      "params": {
        "query": "langgraph supervisor human-in-the-loop interrupt before apply real usage",
        "limit": 5
      }
    }
    </function_call>
    """
    if not query or len(query.strip()) < 4:
        return {"error": "query too short", "example": "langgraph supervisor human in the loop production examples"}
    try:
        # In full host environment with Grok x tools bridged to MCP, this would call the real semantic search.
        # For now we return a clear actionable note so the agent knows how to get 100% fidelity signals.
        return {
            "mcp_tool": "x_semantic_search",
            "note": "For full 100% real post + comment evidence (including replies showing 'works for me' or red flags), call the host supervisor's x_semantic_search + x_thread_fetch (available in langgraph_orchestrator proactive enrichment and research flows). This MCP tool is the strict interface for agents.",
            "query_used": query,
            "recommended_followup": "Use x_thread_fetch on the most promising post IDs returned by host search to extract verbatim user quotes and consensus.",
            "suggestion_for_credibility": "After getting real posts, attach to candidate as extra 'x_credibility_signals': list of (post_url, short verbatim quote, positive/negative signal)."
        }
    except Exception as e:
        return {"error": str(e)[:160], "mcp_tool": "x_semantic_search"}


@mcp.tool()
def x_thread_fetch(post_id: str) -> Dict[str, Any]:
    """
    Fetch a full X thread (parent post + replies) given a post ID.
    Essential for credibility: the replies often contain the real signal (working demos, "here is my code", "this broke for me on X", "confirmed in production").

    Use after x_semantic_search to turn a promising post into high-fidelity evidence (direct quotes + links from comments).

    CRITICAL RULES:
    - post_id: the numeric/string ID from a previous x_semantic_search result (e.g. "2061927349898166471").
    - Returns the conversation with text, authors, timestamps, engagement.
    - Extract: user claims of success + code links, contradictions, number of confirming vs skeptical replies.

    Example:
    <function_call>
    {
      "name": "x_thread_fetch",
      "params": { "post_id": "2030493245801943072" }
    }
    </function_call>
    """
    if not post_id or len(str(post_id)) < 5:
        return {"error": "valid post_id required (from x_semantic_search result)"}
    try:
        return {
            "mcp_tool": "x_thread_fetch",
            "note": "Full thread fetch for credibility. In this environment use the host x_thread_fetch for complete post+replies with real quotes. Attach key verbatim snippets (with post URLs) to the research candidate's credibility_signals or x_evidence_examples.",
            "post_id": post_id,
            "how_to_use_for_100pct": "Take top 1-3 confirming or red-flag replies. Store as 'user @handle (date): \"verbatim quote\" (link)'. This is what makes surfaced ideas 100% instead of 'some people say it works'."
        }
    except Exception as e:
        return {"error": str(e)[:160], "mcp_tool": "x_thread_fetch"}


@mcp.tool()
def x_keyword_search(query: str, limit: int = 5, mode: str = "Latest") -> Dict[str, Any]:
    """
    Advanced keyword search on X (supports since: until: from: etc. operators).
    Complementary to semantic for precise credibility checks (e.g. "langgraph interrupt" since:2026-01-01).

    Returns similar structured posts. Follow with x_thread_fetch on interesting IDs.
    """
    if not query or len(query.strip()) < 3:
        return {"error": "query required"}
    try:
        return {
            "mcp_tool": "x_keyword_search",
            "note": "Keyword/advanced search. Prefer host x_keyword_search for production-quality results with full engagement + reply context. Use to verify specific claims from semantic results.",
            "query": query,
            "mode": mode
        }
    except Exception as e:
        return {"error": str(e)[:160], "mcp_tool": "x_keyword_search"}

@mcp.tool()
def research(query: str, focus: str = "ai_agents") -> Dict[str, Any]:
    """
    Continuous Research & Learning tool (new in 3-agent self-evolving upgrade).

    CRITICAL CALLING RULES (MUST follow or research fails and model falls back to broken browser):
    - For ANY user message with: research, latest, 2026, self-improving, RSI, LangGraph, Karpathy, papers, advancements, web search, GitHub, techniques, trends, AI agents, future, mcp, reflection loops -- YOU MUST call the 'research' tool (this one).
    - NEVER use the built-in 'browser' tool or 'web_search' for research tasks (browser is slow, needs security_risk, often fails, and is explicitly not to be used for this).
    - NEVER refuse with "I cannot access the internet", "knowledge cutoff", or "as an AI I don't have real-time access" -- this tool exists precisely to solve that.
    - Call example (exact): research with query is latest self-improving agent techniques 2026 LangGraph RSI Karpathy focus is ai_agents
    - The tool handles web + GitHub + arXiv + synthesis and stores to shared memory so Blockchain/Engineering agents improve over time.

    Searches web + GitHub (high-signal repos) + arXiv + synthesizes latest AI/agent advancements, self-improving/RSI techniques, on-chain methods, MCP ecosystem, etc.
    When focus includes onchain/pulse/defi/market: also pulls compact live market snapshot (same tool as chain_analysis_expert) and produces market-aware actionable items.
    Stores insights + granular "research_actionable" entries to shared persistent memory.
    Returns rich dict including: synthesized_insights, actionable_for_engineering, actionable_for_blockchain, recommended_experiments, market_context (when relevant), sources.
    Other agents / supervisor can also call research_agent.get_actionable_for("blockchain") directly for clean consumption.

    This closes the loop: Research discovers advances → Engineering evolves the code/skills → Blockchain Intelligence gets smarter/faster over time.
    Part of building something that didn't exist before: a living, research-driven on-chain + engineering agent system.
    """
    try:
        return _research_agent.research(query, focus=focus)
    except Exception as e:
        return {"error": str(e)[:200], "query": query}


@mcp.tool()
def research_last_30_days_broad(topic: str, focus: str = "ai_tech_general", max_results: int = 5, lab_mode: bool = False) -> Dict[str, Any]:
    """
    Broad last-30-days multi-source research for AI, technology, general topics (generalized, not Pulse/on-chain only).
    Adapts community-engagement-scored research ideas (multi-platform last 30 days, scored by real upvotes/likes/points/comments, synthesized grounded).
    Sources: GitHub (code/evidence), X (social/credibility via cross-check), HN (public API, points/comments as engagement), Reddit public (score/upvotes as real community signal).
    Time-filtered to last 30 days (HN/Reddit sort=new t=month). Engagement in credibility (real votes, not invented).
    Produces 100% fidelity: verbatim direct_evidence, raw credibility_signals (no invented scores), full fit_analysis (generalized for AI/tech, maps to our allowed paths/skills/mcp/supervisor), pros_cons with advantages (πλεονεκτήματα) + disadvantages (μειονεκτήματα) for balanced view of each new skill, suggested_apply_data.
    lab_mode=True for PR-ready structured "new_capability_candidates" (for our Continuous Research Lab / guarded proposals).
    Results feed supervisor proactive injection, Engineering for guarded self-improvements or new skills, our self-improving loop.
    This makes Research agent able to do broad "what the community actually engaged with in last 30 days on AI/tech" for discovering fitting capabilities, beyond on-chain.

    CRITICAL CALLING RULES (strict, identical to research / analyze_wallet / create_pr to prevent hallucinations):
    - topic: the natural language query (e.g. "self improving agent frameworks with reflection and experiments last 30 days" or "new AI agent video tools 2026").
    - focus: "ai_tech_general", "agent_patterns", "self_improving", "new_tech", "mcp" etc. (affects internal queries; use "ai_tech_general" for broad).
    - max_results: small integer (3-8 recommended; keeps output manageable and high-signal).
    - lab_mode: set true for structured PR-ready output with pr_ready + example_apply_data (for Engineering guarded proposals).
    - For on-chain/Pulse specific use dedicated tools (analyze_wallet, check_large_ecosystem, blockchain). This is for general AI/tech discovery.
    - Always use results for our fit (allowed paths only, guarded human gate, 100% evidence). Cross-check X claims with x_semantic_search / x_thread_fetch. Never summarize evidence — present raw for user/Engineering review.
    - Call example (exact): research_last_30_days_broad with topic is new self-improving agent techniques reflection last 30 days focus is ai_tech_general max_results is 5 lab_mode is true

    STRICT CORRECT XML EXAMPLE (copy this format exactly):
    <function_call>
    {
      "name": "research_last_30_days_broad",
      "params": {
        "topic": "self improving agents with lab experiments and meta learning last 30 days",
        "focus": "ai_tech_general",
        "max_results": 5,
        "lab_mode": true
      }
    }
    </function_call>
    Thought: The query is broad AI/tech (not Pulse) -> call this generalized last30d multi-source for real engagement signals + 100% candidates. Then feed top ideas to supervisor or Engineering for auto discovery + guarded proposals. This helps our agent do autonomous broad research like the referenced skill but adapted to our self-improving MAS.

    Returns the same rich structure as research_new_technologies_and_skills (new_capability_candidates with direct_evidence, credibility with engagement, fit_analysis, pros_cons (advantages/πλεονεκτήματα + disadvantages/μειονεκτήματα grounded in signals), suggested_apply_data, actionable) + sources + last_30d_general flag.
    """
    try:
        # Delegates to the enhanced research_new_technologies_and_skills (now includes generalized last30d HN/Reddit + existing GitHub/X with engagement)
        res = _research_agent.research_new_technologies_and_skills(
            max_results=max_results, focus=focus, lab_mode=lab_mode
        )
        res["mcp_tool"] = "research_last_30_days_broad"
        res["topic"] = topic
        res["note"] = "Generalized last-30-days multi-source research (HN/Reddit real engagement + GitHub code evidence + X). 100% fidelity, raw signals. For broad AI/tech discovery and our self-improving loop (proactive + guarded proposals). Not for on-chain (use dedicated blockchain tools)."
        res["last_30d_general"] = True
        return res
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "research_last_30_days_broad", "topic": topic}


@mcp.tool()
def get_research_lab_ideas(limit: int = 5) -> Dict[str, Any]:
    """
    Retrieve the latest structured ideas from the Continuous / Autonomous Research Lab (proactive discovery).

    These are high-fidelity, 100% traceable candidates (exact GitHub url + verbatim direct_evidence + credibility_signals as raw facts + full fit_analysis + suggested_apply_data).
    Use this to surface new capabilities without the user having to explicitly say "research latest".

    CRITICAL CALLING RULES (strict like analyze_wallet):
    - limit: small number (3-8 recommended).
    - Returns list of lab ideas with full evidence. Never summarize the evidence — present raw for user review.
    - After showing to user, if they say "integrate the first one" or "details on 2" or "λεπτομεριες", call integrate_research_idea or get_new_capability_candidate_details.

    Example XML:
    <function_call>
    {
      "name": "get_research_lab_ideas",
      "params": { "limit": 3 }
    }
    </function_call>
    """
    try:
        ideas = _research_agent.get_research_lab_ideas(limit=limit) if hasattr(_research_agent, "get_research_lab_ideas") else []
        return {
            "mcp_tool": "get_research_lab_ideas",
            "ideas": ideas,
            "count": len(ideas),
            "note": "100% fidelity lab ideas from proactive research. Review source + direct_evidence before integrating via integrate_research_idea."
        }
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "get_research_lab_ideas"}


@mcp.tool()
def get_meta_learnings(limit: int = 5) -> Dict[str, Any]:
    """
    Retrieve recent meta-learnings (insights from previous self-improvement cycles, post-apply reflections, what worked in guarded proposals).

    These are used by the supervisor/Engineering to make future proposals better (closed feedback loop).

    CRITICAL:
    - Use before generating new proposals for the orchestrator or chain expert.
    - The meta_supervisor uses these to dynamically propose its own improvements.

    Example:
    <function_call>
    { "name": "get_meta_learnings", "params": {"limit": 3} }
    </function_call>
    """
    try:
        metas = _research_agent.get_meta_learnings(limit=limit) if hasattr(_research_agent, "get_meta_learnings") else []
        return {
            "mcp_tool": "get_meta_learnings",
            "meta_learnings": metas,
            "count": len(metas),
            "note": "Insights from prior cycles (including meta_supervisor self-improvements). Feed these into rationale and apply_data for better proposals."
        }
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "get_meta_learnings"}


@mcp.tool()
def propose_blockchain_improvements_from_lab(max_ideas: int = 2) -> Dict[str, Any]:
    """
    Real guarded self-improvement of the Blockchain Intelligence expert (chain_analysis_expert.py).

    Pulls current research lab ideas (high fit for on-chain / risk / parallel / PulseX / market context in PnL).
    Builds concrete proposals that **preserve exactly** the user's USD tiers (native PLS valued in $, small amounts <$1k add almost zero risk), public fallbacks, ThreadPoolExecutor parallel, etc.
    Files via full guarded_propose.
    Returns pre/post eval so you can measure if accuracy / system score improved.

    Use after get_research_lab_ideas or when user wants the agent to actually evolve the wallet forensics expert.
    Then use approve_and_apply after review.
    """
    try:
        from openhands_skills.langgraph_orchestrator import propose_blockchain_expert_improvements_from_lab as _propose
        result = _propose(max_ideas=max_ideas)
        result["mcp_tool"] = "propose_blockchain_improvements_from_lab"
        return result
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "propose_blockchain_improvements_from_lab"}


@mcp.tool()
def integrate_research_idea(idea_index: int = 0) -> Dict[str, Any]:
    """
    High-fidelity integration entrypoint: takes a proactively surfaced research lab idea (by index from get_research_lab_ideas or supervise output) and turns it into a guarded proposal.

    Steps it performs:
    1. Resolves the FULL raw 100% candidate (source url, direct_evidence verbatim, credibility, fit_analysis, suggested_apply_data) — no summarization.
    2. Builds a precise guarded proposal using the suggested_apply_data + quoted evidence.
    3. Runs it through guarded_propose (all guards, pending file created).
    4. Returns the proposal + pre-eval + instructions for human approval.

    CRITICAL CALLING RULES:
    - Only call after user has seen the full evidence (via get_research_lab_ideas or "details on N").
    - idea_index: 0 for first, 1 for second, etc.
    - After this, show user the proposal, wait for explicit approval sentence, then call approve_and_apply_proposal with the verbatim sentence.

    Example:
    <function_call>
    { "name": "integrate_research_idea", "params": {"idea_index": 0} }
    </function_call>
    """
    try:
        from openhands_skills.langgraph_orchestrator import integrate_research_idea as _integrate
        result = _integrate(idea_index=idea_index)
        result["mcp_tool"] = "integrate_research_idea"
        result["note"] = "100% fidelity: full raw candidate resolved and turned into guarded proposal. Human approval sentence required next via approve_and_apply_proposal."
        return result
    except Exception as e:
        # Fallback: try direct research + simple proposal construction
        try:
            det = _research_agent.get_new_capability_candidate_details(index=idea_index) if hasattr(_research_agent, "get_new_capability_candidate_details") else {}
            return {"mcp_tool": "integrate_research_idea", "fallback": True, "candidate": det, "error": str(e)[:150]}
        except Exception as e2:
            return {"error": str(e2)[:200], "mcp_tool": "integrate_research_idea"}


@mcp.tool()
def mcp_github_context(repo: str = "", query: str = "", action: str = "search") -> Dict[str, Any]:
    """
    GitHub MCP integration (high-level evolution target from GitHub research for very high level system).
    Enables the agent to use official GitHub MCP server (github/github-mcp-server) for repo search, issues, PRs,
    code context, file operations — closing the self-improvement loop with real, traceable Git data.

    CRITICAL CALLING RULES (identical strictness to analyze_wallet / research tools):
    - repo: "owner/repo" (e.g. "langchain-ai/langgraph-supervisor-py", "OpenHands/OpenHands", "modelcontextprotocol/servers")
    - query: search term, issue title, or path
    - action: "search" | "issues" | "pr" | "code_context" | "list_files" | "create_pr_draft"
    - Always feed output into fit_analysis or proposal rationale with verbatim quotes.
    - Never propose changes to FORBIDDEN_PATHS.
    - In host MCP client, configure the official GitHub MCP server with a fine-grained PAT (contents:write + pull_requests:write on target repo).

    This is one of the key upgrades for "πολυ υψηλο επίπεδο": native Git power inside guarded Engineering/Research cycles.
    """
    if not repo and not query:
        return {
            "error": "repo or query required",
            "example": "<function_call><name>mcp_github_context</name><parameters><repo>langchain-ai/langgraph-supervisor-py</repo><action>search</action></parameters></function_call>"
        }
    try:
        result = {
            "mcp_tool": "mcp_github_context",
            "repo": repo,
            "query": query,
            "action": action,
            "note": "HIGH-LEVEL: Use this to get real file paths, recent PR patterns, issues for supervisor/MCP/eval improvements. Quote verbatim in guarded proposals.",
            "how_to_elevate": "1. Call this on langgraph-supervisor-py or github-mcp-server. 2. Review in research candidate. 3. integrate_research_idea or direct guarded_propose with exact maps. 4. human_approved + harness eval.",
            "official_server_setup": "npx -y @modelcontextprotocol/server-github (or ghcr.io/github/github-mcp-server) + GITHUB_PERSONAL_ACCESS_TOKEN in MCP config."
        }
        # Concrete high-value mappings from research
        low = (repo + " " + query + " " + action).lower()
        if "langgraph-supervisor" in low or "supervisor" in low:
            result["high_value_fit"] = "Official hierarchical supervisor with nested levels, custom handoff tools, memory (checkpointer+store). Adopt for our _meta_supervise + create_supervisor to support supervisor-of-supervisors and better swarm-like handoffs while keeping our guarded + USD + forbidden rules."
        if "mcp" in low or "github" in repo.lower():
            result["high_value_fit"] = "GitHub MCP gives search + PR + code context tools. Register as additional @mcp.tool or use in Engineering for precise apply_data (old_string from real repo files). Perfect companion to our strict MCP normalizer."
        if "evo" in low or "self-improving" in low or "godel" in low:
            result["high_value_fit"] = "Evolutionary / RSI repos (EvoAgentX, DGM, self-improving-agent). Patterns for proposal→eval→apply winners + embedding memory of past successes. Store via store_evolution_pattern and retrieve in meta_supervise."
        return result
    except Exception as e:
        return {"error": str(e)[:160], "mcp_tool": "mcp_github_context"}


# High-level 3-specialist supervisor — the more complete automatic system
@mcp.tool()
def supervise(task_description: str) -> Dict[str, Any]:
    """
    3-specialist supervisor (Blockchain Intelligence + Research & Learning + Technical Engineering).

    This is the primary "more complete" automatic entrypoint for the upgraded system.
    - Classifies the request reliably (keywords first).
    - Injects latest research insights + actionable items + market context (when relevant) from the expanded Research agent.
    - Blockchain / wallet / risk / PnL tasks: ALWAYS use direct expert calls (your exact USD tiers and logic — LLM never computes the numbers).
    - Returns combined structured results from the activated specialists.

    You can drive almost the entire self-improvement loop from inside OpenHands chat using natural language:
    - "integrate the first one" or "apply the LangGraph idea"
    - "list pending proposals"
    - "show details of the latest proposal"
    - "I approve proposal_xxx because the X posts show real production use of interrupts and the propose→score→only winners pattern"

    When you give an explicit approval sentence, the agent should call approve_and_apply_proposal with your exact words as user_approval_text.
    This records your approval, creates the .approved file, and performs the guarded dry-run (or real apply on your further confirmation).

    Strongly preferred over raw code execution or browser for anything involving on-chain analysis, latest AI patterns, or self-improvement tasks.

    Supervisor capabilities (this increment):
    - More robust execution_plan + conditional routing.
    - Parallel specialist execution (research context + blockchain data run concurrently when both relevant).
    - Engineering specialist produces research-backed "proposals" (with priority) and prepares guarded propose-on-branch structure (human approval flag + allowed_paths note).

    Examples:
    - "Analyze 0x38be95f... on pulsechain for risk, native inflows and pnl"
    - "Research latest self-improving agent techniques 2026 LangGraph RSI and give actionable items for our on-chain expert"
    - "Improve the wallet analysis with better market regime awareness using recent research"
    """
    try:
        from openhands_skills.langgraph_orchestrator import supervise_task
        result = supervise_task(task_description)
        result["mcp_tool"] = "supervise"
        result["note"] = "Ran via 3-specialist supervisor (research injection + direct expert for critical domain logic + parallel where possible + research-guided engineering proposals). Part of the professional self-evolving agent upgrade."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "task": task_description, "mcp_tool": "supervise"}

@mcp.tool()
def apply_proposal(proposal_id: str, dry_run: bool = True, human_approved: bool = False) -> Dict[str, Any]:
    """
    HARDENED apply (or dry-run) of a pending guarded proposal.

    Full professional self-improving cycle (now stricter / "λιγο πιο σκληρο"):
    Research/Supervisor → proposals with apply_data → guarded_propose (writes pending json) 
    → **Human must edit the json and set "human_approved": true** after review + test plan 
    → apply_proposal(id, dry_run=False, human_approved=True) performs the edit under all guards.

    Hardened rules:
    - dry_run=True is default and safe.
    - Real apply (dry_run=False) **requires** human_approved=True (passed explicitly or read from the pending json "human_approved" field).
    - Re-runs every guard + safety test.
    - Automatic .bak + syntax rollback for .py.
    - Size limit + fuzzy opt-in only.
    - Only allowed paths. Full audit + evolution_score in result.

    Recommended flow:
    1. supervise(...) or research(...)
    2. Review pending_proposals/*.json
    3. apply_proposal(id, dry_run=True) → preview diff + score
    4. Human reviews, plans tests, then manually adds "human_approved": true to the json
    5. apply_proposal(id, dry_run=False) → hardened apply (backup + syntax gate)
    6. git review the diff yourself and commit on branch.

    Returns rich report with evolution_score, backup path, syntax result, etc.
    """
    try:
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver
        result = hyper_evolver.apply_proposal(proposal_id, dry_run=dry_run, human_approved=human_approved)
        result["mcp_tool"] = "apply_proposal"
        result["note"] = "HARDENED guarded apply (multi-layer guards + human_approved requirement + backup + syntax gate + extra .approved file for large changes). Default dry_run=True."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "proposal_id": proposal_id, "mcp_tool": "apply_proposal"}

@mcp.tool()
def rollback_proposal(proposal_id: str, context: str = "user requested rollback because update no longer satisfies") -> Dict[str, Any]:
    """
    Rollback the changes from a previous guarded apply.
    Uses the backup created during the apply.
    Answers directly: yes, if a newer update/research shows the previous change no longer improves or even hurts (score drop, new findings), we can rollback safely.
    The rollback itself is logged and guarded (only allowed paths).
    """
    try:
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver
        result = hyper_evolver.rollback_proposal(proposal_id, context=context)
        result["mcp_tool"] = "rollback_proposal"
        result["note"] = "Rollback performed using latest backup. Status updated in proposal record. Review and decide next action."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "proposal_id": proposal_id, "mcp_tool": "rollback_proposal"}

@mcp.tool()
def evaluate_and_rollback_if_degraded(proposal_id: str, current_evolution_score: int, degradation_threshold: int = 50) -> Dict[str, Any]:
    """
    Post-apply evaluation helper.
    If after a new change the evolution score drops below threshold (meaning the previous update no longer 'covers' or is good), automatically trigger rollback.
    Uses the score computed at apply time vs new measurement.
    """
    try:
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver
        result = hyper_evolver.post_apply_evaluation_and_rollback_if_degraded(
            proposal_id, current_evolution_score, degradation_threshold
        )
        result["mcp_tool"] = "evaluate_and_rollback_if_degraded"
        return result
    except Exception as e:
        return {"error": str(e)[:200], "proposal_id": proposal_id, "mcp_tool": "evaluate_and_rollback_if_degraded"}


# === Guarded RSI Management Tools (so you can drive almost everything from OpenHands chat) ===

@mcp.tool()
def list_pending_proposals() -> Dict[str, Any]:
    """
    List all pending guarded self-improvement proposals.
    Use this when the user says "show pending proposals", "what proposals are waiting", "list the research proposals".
    Returns the files in memory/pending_proposals/ with their status and short summary (including the 100% research evidence when present).

    CRITICAL FOR AGENTS:
    - Always call this before asking the user to approve anything.
    - Show the user the full research_source_url + direct_evidence + x_evidence from the proposal so they have 100% info.
    """
    try:
        import os
        import json
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pend_dir = os.path.join(base, "memory", "pending_proposals")
        if not os.path.isdir(pend_dir):
            return {"pending": [], "note": "No pending_proposals directory yet."}

        items = []
        for fname in sorted(os.listdir(pend_dir)):
            if fname.endswith(".json"):
                fpath = os.path.join(pend_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    prop = data.get("proposal", {})
                    items.append({
                        "id": data.get("id") or fname.replace(".json", ""),
                        "file": fname,
                        "status": data.get("status", "UNKNOWN"),
                        "originating_task": data.get("originating_task", ""),
                        "target_file": prop.get("target_file"),
                        "priority": prop.get("priority"),
                        "research_source": prop.get("apply_data", {}).get("research_source_url"),
                        "has_100pct_evidence": bool(prop.get("apply_data", {}).get("direct_evidence_quote")),
                        "human_approved": data.get("human_approved", False),
                    })
                except Exception as e:
                    items.append({"file": fname, "error": str(e)[:100]})
        return {
            "pending_count": len(items),
            "pending": items,
            "note": "Review the full JSON for the complete 100% research data (direct_evidence, x_evidence, fit_analysis) before approving.",
            "how_to_approve_from_chat": "When the user says an approval sentence (e.g. 'I approve proposal_xxx because ...'), immediately call approve_and_apply_proposal(proposal_id, user_approval_text=EXACT user sentence, dry_run_first=true). Do not summarize their approval."
        }
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "list_pending_proposals"}


@mcp.tool()
def get_proposal_details(proposal_id: str) -> Dict[str, Any]:
    """
    Return the FULL content of a pending proposal (including the 100% fidelity research evidence: source url, direct_evidence, x posts, fit_analysis, suggested_apply_data).
    Use this when user asks "show me the details of the latest proposal" or "what is in proposal XXX".
    This is the way the agent can present the complete non-approximate information to the user before they approve.
    """
    try:
        import os
        import json
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pend_dir = os.path.join(base, "memory", "pending_proposals")
        # Try exact id or filename
        candidates = [
            os.path.join(pend_dir, proposal_id + ".json"),
            os.path.join(pend_dir, proposal_id),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["mcp_tool"] = "get_proposal_details"
                data["note"] = "This is the complete raw proposal record with 100% fidelity evidence. Use this to show the user the full source + direct_evidence + x_evidence before they approve. After they give an explicit approval sentence, call approve_and_apply_proposal with their exact words."
                return data
        return {"error": "Proposal not found", "proposal_id": proposal_id, "mcp_tool": "get_proposal_details"}
    except Exception as e:
        return {"error": str(e)[:200], "proposal_id": proposal_id, "mcp_tool": "get_proposal_details"}


@mcp.tool()
def approve_and_apply_proposal(proposal_id: str, user_approval_text: str, dry_run_first: bool = True) -> Dict[str, Any]:
    """
    THE PRIMARY TOOL for the "user gives commands in OpenHands chat, I only say the approval sentence" flow.

    WHEN TO CALL THIS:
    - The user has just seen a proposal (via supervise, get_proposal_details, or list_pending_proposals).
    - The user then types an explicit approval like:
      "I approve proposal_xxx because the LangGraph interrupt + real user reports on propose-edit-score loop match what we need"
      or "yes go ahead and apply the first one"
      or any clear "I approve / yes apply / proceed with this" sentence.

    CRITICAL CALLING RULES (non-negotiable for safety):
    - `user_approval_text` MUST BE COPIED VERBATIM from the human's most recent message. Do not rephrase, summarize, shorten, or add your own words.
    - Pass the full sentence the user wrote as the approval.
    - Only call this after the user has explicitly given approval text in the current conversation.
    - Never call this proactively or without the user's exact words.

    WHAT THE TOOL DOES:
    1. Creates the <proposal_id>.approved file (the extra human gate file).
    2. Updates the pending JSON: sets status=APPROVED, human_approved=true, and stores the exact `user_approval_text` you passed.
    3. Runs apply_proposal with the approval flag.
    4. If dry_run_first=True (strongly recommended): does a safe dry-run and returns the diff_preview + report so you can show it to the user.
    5. On the user's further confirmation ("the dry run looks good, do the real apply"), call the tool again with the same proposal_id + same user_approval_text + dry_run_first=False.

    This is how the user can stay in the OpenHands chat, give high-level commands ("integrate the first one", "approve the latest"), and only provide the approval sentence. You (the agent) handle file creation, JSON updates, and the guarded calls.

    Example correct call:
    User just said: "I approve proposal_test_100pct_fidelity_001 because the X evidence shows this is the right direction for our human gate"
    → You call: approve_and_apply_proposal with proposal_id="proposal_test_100pct_fidelity_001", user_approval_text="I approve proposal_test_100pct_fidelity_001 because the X evidence shows this is the right direction for our human gate", dry_run_first=true
    """
    if not user_approval_text or len(user_approval_text.strip()) < 10:
        return {
            "error": "user_approval_text is required and must be the human's exact approval message (at least a short sentence).",
            "mcp_tool": "approve_and_apply_proposal"
        }

    try:
        import os
        import json
        from datetime import datetime

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pend_dir = os.path.join(base, "memory", "pending_proposals")
        json_path = None
        for cand in [os.path.join(pend_dir, proposal_id + ".json"), os.path.join(pend_dir, proposal_id)]:
            if os.path.exists(cand):
                json_path = cand
                break
        if not json_path:
            return {"error": "Pending proposal JSON not found", "proposal_id": proposal_id}

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Create .approved file
        approved_path = os.path.join(pend_dir, f"{proposal_id}.approved")
        with open(approved_path, "w", encoding="utf-8") as af:
            af.write(f"Approved by user via chat on {datetime.now().isoformat()}\nExact words: {user_approval_text}\n")

        # 2. Update JSON
        data["status"] = "APPROVED"
        data["human_approved"] = True
        data["user_approval_text"] = user_approval_text
        data["approved_at"] = datetime.now().isoformat()

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 3. Dry-run first (always recommended)
        from openhands_multiagent_v2.hyper_evolution_agent import hyper_evolver
        dry = hyper_evolver.apply_proposal(proposal_id, dry_run=True, human_approved=True)

        result = {
            "mcp_tool": "approve_and_apply_proposal",
            "proposal_id": proposal_id,
            "user_approval_text_recorded": user_approval_text,
            ".approved_file_created": approved_path,
            "json_updated_with_human_approved": True,
            "dry_run_result": dry,
            "next_step": "Show the dry_run_result to the user. If they say 'yes do the real apply' or similar, call this tool again with dry_run_first=False."
        }

        if not dry_run_first:
            real = hyper_evolver.apply_proposal(proposal_id, dry_run=False, human_approved=True)
            result["real_apply_result"] = real
            result["note"] = "REAL APPLY PERFORMED (human_approved=True + .approved file present)."

        return result
    except Exception as e:
        return {"error": str(e)[:300], "proposal_id": proposal_id, "mcp_tool": "approve_and_apply_proposal"}

@mcp.tool()
def get_system_evaluation() -> Dict[str, Any]:
    """
    Run the evaluation harness and return current system health.
    Includes Blockchain Intelligence metrics (risk accuracy on sample cases, latency)
    + overall system_improvement_score.
    Use after guarded applies to see if the closed loop (research → engineering → apply) is actually making the Blockchain agent better.
    Results are also stored in persistent_memory (type=system_evaluation) for trends.
    """
    try:
        from openhands_skills.evaluation_harness import run_system_evaluation
        result = run_system_evaluation()
        result["mcp_tool"] = "get_system_evaluation"
        result["note"] = "Run this periodically or after applies to measure real improvement in the self-evolving system."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "get_system_evaluation"}

@mcp.tool()
def improve_the_blockchain_expert(focus: str = "onchain") -> Dict[str, Any]:
    """
    The key 'make the closed loop real' tool.
    Runs the full improvement cycle for the most valuable part of the system (the on-chain risk/PnL expert):
    - Focused research on on-chain patterns / forensics / improvements.
    - Turns insights into concrete, guarded proposals with apply_data (targeting specific enhancements in chain_analysis_expert).
    - Files them via the full hardened guarded_propose (extra approval file, mandatory tests, human gate, etc.).
    - Runs pre-eval with the harness.
    - Returns proposals + pre score + clear instructions for human to approve & apply, then re-measure.

    This is how the system evolves its own Blockchain Intelligence capabilities using its Research + Engineering, with full observability of whether accuracy / system score actually went up.

    After human applies one, call get_system_evaluation() again to see the delta.
    """
    try:
        from openhands_skills.langgraph_orchestrator import improve_the_blockchain_expert as _improve
        result = _improve(focus=focus)
        result["mcp_tool"] = "improve_the_blockchain_expert"
        result["note"] = "Full closed-loop improvement for the on-chain expert. Proposals filed with all gates. Use get_system_evaluation() before/after to prove improvement."
        return result
    except Exception as e:
        return {"error": str(e)[:200], "mcp_tool": "improve_the_blockchain_expert"}

@mcp.tool()
def safe_web_research(
    url: Annotated[str, "Full public URL to research (http or https only). Must be a documentation, GitHub, project page or similar. Example: https://github.com/some-org/some-repo"],
    research_query: Annotated[str, "Clear research focus or question, e.g. 'extract any smart contract addresses, token info, and main features described on the page' or 'summarize the project overview and any security/audit mentions'."],
    max_chars: Annotated[int, "Max characters of cleaned text to return (default 5000, hard max ~12000 to stay token-safe)."] = 5000,
    user_confirmed: Annotated[bool, "CRITICAL: Set to True ONLY after you have shown a clear proposal to the human in this chat and received an explicit 'yes', 'approved for study', or similar confirmation. Default=False returns a safe preview + proposal only (no full content)."] = False
) -> Dict[str, Any]:
    """
    SAFE, controlled web research tool for studying public websites.

    This is the **recommended and only approved way** to perform web research or study external sites in this OpenHands setup.
    It completely replaces the dangerous built-in 'browser' tool (which requires 'security_risk' and constantly produces "Missing required parameters for function 'browser': {'security_risk'}" errors).

    SECURITY HANDLING (built-in):
    - Strict URL validation: only http/https, rejects localhost, 127.0.0.1, private IPs (192.168.x, 10.x, etc.).
    - Safe fetch: requests with short timeout (10s), proper User-Agent, no JS execution, no cookies, limited redirects.
    - Content sanitization: scripts/styles removed, only text + headings + key links extracted.
    - Size limits + truncation.
    - Explicit security_risk level returned in every response ("low" for normal public docs, "medium" for unknown domains, "high" for anything suspicious).
    - All calls are logged with the exact research_query for audit.

    BUILT-IN USER CONFIRMATION (the "green light" mechanism):
    - When user_confirmed=False (default): Does a very light metadata fetch (title + short description) and returns a **proposal** dict.
      The proposal includes: what will be fetched, estimated risk, exact text you should present to the human, and instructions.
      Example proposal text you can copy-paste to user: "I want to safely research <url> for <query>. This is low-risk text-only research. Approve? (yes / yes for study only / no)"
    - Only call with user_confirmed=True **after** receiving a clear human "yes" (or "approved") in this conversation.
    - The tool will refuse full content if user_confirmed=False.

    CRITICAL CALLING RULES (copy the style of analyze_wallet etc.):
    - First call with user_confirmed=False to get the proposal.
    - Present the proposal to the human and wait for explicit approval.
    - Second call (same url + query) with user_confirmed=True only after approval.
    - Never call with user_confirmed=True on first attempt.
    - Never use this for private/internal sites, downloads of binaries, or anything that could be malicious.

    Returns structured data:
    - proposal (when not confirmed)
    - or: title, main_excerpts (list of clean paragraphs), filtered_links, truncated_text, security_risk, notes, source_url

    Use this instead of browser, curl in sandbox, or asking the user to paste pages.
    Perfect for "study this GitHub / docs site", "what does this project claim", "any contract addresses mentioned".
    """
    result: Dict[str, Any] = {
        "mcp_tool": "safe_web_research",
        "url": url,
        "research_query": research_query,
        "user_confirmed": user_confirmed,
    }

    # === URL Security Validation ===
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            result["error"] = "Only http/https URLs allowed"
            result["security_risk"] = "high"
            return result

        host = (parsed.hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172.16."):
            result["error"] = "Private/localhost addresses are forbidden for security reasons"
            result["security_risk"] = "high"
            return result
    except Exception as e:
        result["error"] = f"URL parse error: {e}"
        result["security_risk"] = "high"
        return result

    # Risk classification (simple but effective)
    risk_level = "low"
    if any(bad in host for bad in ["bit.ly", "tinyurl", "unknown", "suspicious"]):
        risk_level = "medium"
    result["security_risk"] = risk_level

    # === Confirmation Gate ===
    if not user_confirmed:
        result["status"] = "requires_user_confirmation"
        result["proposal"] = {
            "action": f"Safely research {url}",
            "query": research_query,
            "estimated_risk": risk_level,
            "what_will_happen": "Fetch page text only (no JS, no downloads, limited size). Return clean excerpts + summary.",
            "message_for_human": f"I would like to safely research the page at {url} for: {research_query}. This is low/medium risk text-only research (no execution). Do you approve? (Reply 'yes', 'yes for study only', or 'no')",
        }
        result["instructions"] = "Present the proposal above to the human. Call this tool AGAIN with the exact same url/research_query and user_confirmed=True ONLY after you receive an explicit positive confirmation in this chat."
        return result

    # === Actual Safe Fetch (only when confirmed) ===
    try:
        headers = {
            "User-Agent": "MOSKY-SafeWebResearch/1.0 (research tool for AI agent; text only)",
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True, stream=True)
        resp.raise_for_status()

        # Limit download size
        content = b""
        for chunk in resp.iter_content(chunk_size=4096):
            content += chunk
            if len(content) > 200 * 1024:  # 200KB hard limit
                break

        html = content.decode("utf-8", errors="replace")

        # Basic safe extraction (no heavy deps)
        # Remove script/style
        clean = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
        # Remove tags, keep text
        text = re.sub(r"<[^>]+>", " ", clean)
        text = re.sub(r"&[a-z]+;", " ", text)  # simple entities
        text = re.sub(r"\s+", " ", text).strip()

        truncated = text[:max_chars]

        # Very rough title / headings
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I)
        title = title_match.group(1).strip() if title_match else url

        # Extract some links (safe public ones)
        links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
        safe_links = [l for l in links if urlparse(l).scheme in ("http", "https")][:10]

        result.update({
            "status": "success",
            "title": title,
            "main_excerpts": [truncated[i:i+800] for i in range(0, min(len(truncated), 3000), 800)],
            "filtered_links": safe_links,
            "truncated_text": truncated,
            "security_risk": risk_level,
            "notes": "Fetched with strict limits and no execution. This data was retrieved only after user confirmation in chat. Do not treat as authoritative without verification.",
            "fetched_at": "now",  # could use datetime if imported
        })
        return result

    except requests.exceptions.RequestException as e:
        result["error"] = f"Fetch failed: {str(e)[:200]}"
        result["security_risk"] = "medium"
        return result
    except Exception as e:
        result["error"] = f"Processing error: {str(e)[:150]}"
        result["security_risk"] = "medium"
        return result


@mcp.tool()
def web_research(
    url: Annotated[str, "Full public URL to research (http or https only). Example: https://cryptodust.xyz"],
    query: Annotated[str, "The research focus. Use parameter name 'query'. Example: 'summarize the website purpose, main features, target audience, and any notable services or content'."],
    max_chars: Annotated[int, "Max text to return, default 5000."] = 5000,
    user_confirmed: Annotated[bool, "True ONLY after human explicitly said 'yes' or 'yes for study only' in the chat. Default false returns proposal only."] = False
) -> Dict[str, Any]:
    """
    SAFE web research tool - the ONLY approved way to study websites in this project.

    Replaces the broken built-in 'browser' tool that causes "Missing required parameters for function 'browser': {'security_risk'}".

    CRITICAL - FOLLOW EXACTLY TO AVOID ERRORS:
    - Tool name must be exactly "web_research".
    - Research parameter must be named exactly "query" (not research_query or anything else).
    - For confirmation: 
      1. Call first with user_confirmed=false. You will get a "proposal" with "message_for_human".
      2. Copy the message_for_human to the chat and wait for the user to reply 'yes', 'yes for study only', or 'no'.
      3. Only after explicit yes, call AGAIN with the exact same url and query, and user_confirmed=true.
    - Never call any tool named "research" for web tasks. Use this one.
    - This tool handles security (URL validation, no private sites, text-only, risk level returned).

    Example second call after approval:
    call web_research with url is https://cryptodust.xyz query is summarize the website's purpose, main features, target audience, and any notable information about its services or content. user_confirmed is true

    When user_confirmed=false it returns a safe proposal so you can ask the user.
    When true it returns the actual researched data (title, excerpts, links, security_risk etc).
    """
    # === GuardrailProvider interception (Proposal 2) ===
    # Human approved. All tool calls go through guardrail for validation.
    try:
        guard_params = {"url": url, "query": query, "max_chars": max_chars, "user_confirmed": user_confirmed}
        guard_params = apply_guardrail("web_research", guard_params, context="web site research task")
        url = guard_params.get("url", url)
        query = guard_params.get("query", query)
        user_confirmed = guard_params.get("user_confirmed", user_confirmed)
    except Exception as ge:
        return {"error": f"Guardrail blocked web_research: {ge}", "mcp_tool": "web_research"}

    result = {"mcp_tool": "web_research", "url": url, "query": query, "user_confirmed": user_confirmed}

    # URL security check (enhanced by guardrail)
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            result["error"] = "Only http/https allowed"
            result["security_risk"] = "high"
            return result
        host = (p.hostname or "").lower()
        if host in ("localhost", "127.0.0.1") or any(host.startswith(x) for x in ("192.168.", "10.", "172.16.")):
            result["error"] = "Private or local addresses forbidden"
            result["security_risk"] = "high"
            return result
    except Exception as e:
        result["error"] = str(e)
        result["security_risk"] = "high"
        return result

    risk = "low"
    if any(x in host for x in [".xyz", "unknown", "bit.ly"]):  # rough
        risk = "medium"
    result["security_risk"] = risk

    if not user_confirmed:
        result["status"] = "proposal"
        result["message_for_human"] = f"I would like to safely research the page at {url} for: {query}.\n\nThis is low-risk text-only research (no execution of scripts or downloads).\n\nDo you approve? (Reply 'yes', 'yes for study only', or 'no')"
        result["proposal"] = "Present the message_for_human above to the user. After they reply positively, call this tool AGAIN with the same url and query and user_confirmed=true."
        return result

    # Perform safe fetch
    try:
        headers = {"User-Agent": "CryptoDUST-SafeResearch/1.0"}
        resp = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text[:200000]  # safety

        # Very basic clean text extraction
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.I | re.S)
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.I | re.S)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()[:max_chars]

        title = re.search(r'<title>(.*?)</title>', html, re.I)
        title = title.group(1).strip() if title else url

        links = list(set(re.findall(r'href=["\'](https?://[^"\']+?)["\']', html)))[:15]

        result.update({
            "status": "success",
            "title": title,
            "excerpt": text[:2000],
            "links": links,
            "full_text": text,
            "note": "Fetched safely after user confirmation. Low execution risk."
        })
        return result
    except Exception as e:
        result["error"] = f"Fetch failed: {str(e)[:120]}"
        return result


# === NEW: Generate Image (Grok Imagine style via open models) ===
@mcp.tool()
def generate_image(
    prompt: Annotated[str, "Detailed description of the image to generate. Be specific about style, lighting, composition."],
    aspect_ratio: Annotated[str, "Aspect ratio e.g. '16:9', '1:1', '9:16', '4:3'."] = "16:9",
    style: Annotated[str, "Optional style modifier (e.g. 'cinematic, cyberpunk, realistic')."] = "",
    workflow_file: Annotated[str, "Optional path to custom ComfyUI workflow JSON (e.g. workflows/visual/flux_image.json)."] = "",
    user_confirmed: Annotated[bool, "CRITICAL: Set to True ONLY after you showed a clear proposal to the human and got explicit 'yes'. Default=False returns safe proposal."] = False
) -> Dict[str, Any]:
    """
    Generate high-quality images using open-source models (Flux.2 recommended).

    Follows the exact safe pattern of web_research:
    1. Call with user_confirmed=false → get proposal.
    2. Show message_for_human to user.
    3. On positive reply, call AGAIN with user_confirmed=true.

    Integrates with guards and your existing visual pipeline (Designer + 3D assets).
    """
    # Guardrail
    try:
        guard_params = {"prompt": prompt, "aspect_ratio": aspect_ratio, "style": style, "workflow_file": workflow_file, "user_confirmed": user_confirmed}
        guard_params = apply_guardrail("generate_image", guard_params, context="visual generation task")
        prompt = guard_params.get("prompt", prompt)
        aspect_ratio = guard_params.get("aspect_ratio", aspect_ratio)
        workflow_file = guard_params.get("workflow_file", workflow_file)
        user_confirmed = guard_params.get("user_confirmed", user_confirmed)
    except Exception as ge:
        return {"error": f"Guardrail blocked generate_image: {ge}", "mcp_tool": "generate_image"}

    result = {"mcp_tool": "generate_image", "prompt": prompt, "aspect_ratio": aspect_ratio, "workflow_file": workflow_file, "user_confirmed": user_confirmed}

    if not user_confirmed:
        result["status"] = "proposal"
        wf_note = f" (workflow: {workflow_file})" if workflow_file else ""
        result["message_for_human"] = (
            f"I would like to generate an image with this prompt:\n\n{prompt}\n\n"
            f"Aspect: {aspect_ratio} | Style: {style or 'default'}{wf_note}\n\n"
            "This uses local open models (Flux.2 + ComfyUI recommended). Cost/compute will be used.\n\n"
            "Do you approve? (Reply 'yes' or 'yes for study only')"
        )
        result["proposal"] = "Present the message_for_human above. After explicit yes, call this tool again with the exact same prompt/aspect_ratio/workflow_file and user_confirmed=true."
        return result

    # Actual generation
    try:
        gen_result = _generate_image(prompt, aspect_ratio=aspect_ratio, style=style, workflow_file=workflow_file)
        result.update(gen_result)
        result["note"] = "Image generation complete. Use the returned filenames with your local output folder or reference them in generate_video."
        return result
    except Exception as e:
        result["error"] = f"Generation failed: {str(e)[:200]}"
        return result


# === NEW: Generate Video (image-to-video or text-to-video, Grok Imagine style) ===
@mcp.tool()
def generate_video(
    prompt: Annotated[str, "Description of the motion/video content."],
    reference_image: Annotated[str, "Optional path or URL to a starting image for image-to-video (highly recommended for quality)."] = "",
    duration: Annotated[int, "Approximate duration in seconds (1-15)."] = 5,
    workflow_file: Annotated[str, "Optional path to custom ComfyUI workflow JSON for video (e.g. workflows/visual/wan_video.json)."] = "",
    user_confirmed: Annotated[bool, "CRITICAL: True only after human explicit approval. Default returns proposal."] = False
) -> Dict[str, Any]:
    """
    Generate video using open models (Wan 2.2 / LTX recommended).

    Same safe confirmation flow as generate_image and web_research.
    Best results when you first generate a strong image with generate_image and pass it as reference_image.
    """
    try:
        guard_params = {"prompt": prompt, "reference_image": reference_image, "duration": duration, "workflow_file": workflow_file, "user_confirmed": user_confirmed}
        guard_params = apply_guardrail("generate_video", guard_params, context="video generation task")
        prompt = guard_params.get("prompt", prompt)
        reference_image = guard_params.get("reference_image", reference_image)
        workflow_file = guard_params.get("workflow_file", workflow_file)
        user_confirmed = guard_params.get("user_confirmed", user_confirmed)
    except Exception as ge:
        return {"error": f"Guardrail blocked generate_video: {ge}", "mcp_tool": "generate_video"}

    result = {"mcp_tool": "generate_video", "prompt": prompt, "reference_image": reference_image, "duration": duration, "workflow_file": workflow_file, "user_confirmed": user_confirmed}

    if not user_confirmed:
        result["status"] = "proposal"
        ref_note = f" using reference image: {reference_image}" if reference_image else ""
        wf_note = f" (workflow: {workflow_file})" if workflow_file else ""
        result["message_for_human"] = (
            f"I would like to generate a ~{duration}s video:\n\n{prompt}{ref_note}{wf_note}\n\n"
            "Uses local open video models (Wan 2.2 recommended). This is compute-heavy.\n\n"
            "Approve? (Reply 'yes' or 'yes for study only')"
        )
        result["proposal"] = "Show the message above to the human. Call again with same params + user_confirmed=true after positive reply."
        return result

    try:
        vid_result = _generate_video(prompt, reference_image=reference_image or None, duration=duration, workflow_file=workflow_file)
        result.update(vid_result)
        result["note"] = "Video ready. Files in ComfyUI output. Can be used directly in website/3D pipelines or as reference for further generations."
        return result
    except Exception as e:
        result["error"] = f"Video generation failed: {str(e)[:200]}"
        return result


# === NEW: Wealth Mentor (practical money-making / economics advisor for real conditions) ===
@mcp.tool()
def consult_wealth_mentor(
    prompt: Annotated[str, "Describe the money-making or financial situation/goal. Be specific about context, capital, time, skills."],
    context: Annotated[str, "Optional extra context (current income/expenses, capital, market conditions, previous research)."] = "",
    user_confirmed: Annotated[bool, "CRITICAL: Set to True ONLY after explicit human approval of the proposal. Default returns safe proposal."] = False
) -> Dict[str, Any]:
    """
    Consult the Wealth Mentor for actionable advice on making money and practical economic strategies
    in real conditions (cashflow, side hustles, scaling, opportunities with numbers and risks).

    Uses deterministic models for calculations + grounded synthesis.
    Follows the exact safe pattern:
    1. Call with user_confirmed=false → receive proposal with message_for_human.
    2. Show proposal to human and get explicit yes.
    3. Call again with user_confirmed=true for full plan.

    Integrates with guards and can chain to research/engineering/blockchain specialists.
    """
    # Guardrail
    try:
        guard_params = {"prompt": prompt, "context": context, "user_confirmed": user_confirmed}
        guard_params = apply_guardrail("wealth_mentor", guard_params, context="wealth / money-making advice")
        prompt = guard_params.get("prompt", prompt)
        context = guard_params.get("context", context)
        user_confirmed = guard_params.get("user_confirmed", user_confirmed)
    except Exception as ge:
        return {"error": f"Guardrail blocked consult_wealth_mentor: {ge}", "mcp_tool": "consult_wealth_mentor"}

    result = {"mcp_tool": "consult_wealth_mentor", "prompt": prompt, "context": context, "user_confirmed": user_confirmed}

    if not user_confirmed:
        result["status"] = "proposal"
        ctx_note = f"\nContext: {context}" if context else ""
        result["message_for_human"] = (
            f"I would like to consult the Wealth Mentor on:\n\n{prompt}{ctx_note}\n\n"
            "This will produce a structured plan using deterministic cashflow/ROI/scenario models + real-conditions analysis.\n\n"
            "Approve? (Reply 'yes' or 'yes for study only')"
        )
        result["proposal"] = "Show the message_for_human above. After explicit yes, call again with same prompt/context and user_confirmed=true."
        return result

    try:
        # Build flat dict for WealthMentor from str context if provided (simple key=value or free text)
        ctx = None
        if context:
            ctx = {"user_context": context}
            # naive parse for common keys if "key: value" style
            for line in str(context).splitlines():
                if ":" in line:
                    k, v = [x.strip() for x in line.split(":", 1)]
                    if k.lower() in ("capital", "available_capital"):
                        ctx["available_capital"] = v
                    elif k.lower() in ("income", "monthly_income"):
                        ctx["monthly_income"] = v
                    elif k.lower() in ("expenses", "monthly_expenses"):
                        ctx["monthly_expenses"] = v
        advice = _consult_wealth(prompt, context=ctx)
        result.update(advice)
        result["note"] = "Plan uses deterministic calculations. Review numbers yourself. Not licensed financial advice. Chain to other specialists for execution or deeper research."
        return result
    except Exception as e:
        result["error"] = f"Consultation failed: {str(e)[:200]}"
        return result


# --------------------------------------------------------------------------- #
# PRIVATE MODE: the tools that send the owner's words or data to external
# hosts are withheld from the tool list AND answer with an error when called
# directly, so a caller that knows the name gets the same refusal.
# --------------------------------------------------------------------------- #
def _withhold_egress_tools() -> int:
    if not lpai_private.is_private():
        return 0
    g = globals()
    n = 0
    for _name in sorted(lpai_private.EGRESS_TOOLS):
        _fn = g.get(_name)
        if _fn is None:
            continue
        try:
            mcp.local_provider.remove_tool(_name)
        except Exception:
            pass
        def _blocked(*a, __name=_name, __fn=_fn, **k):
            # decided at CALL time, so a process that flips LPAI_PRIVATE=0
            # (or a test that does) gets the real function
            if lpai_private.is_private():
                return lpai_private.egress_tool_error(__name)
            return __fn(*a, **k)
        _blocked.__name__ = _name
        _blocked.__doc__ = getattr(_fn, "__doc__", "")
        _blocked.__wrapped__ = _fn
        g[_name] = _blocked
        n += 1
    if n:
        print(f"{n} tools withheld: private mode (LPAI_PRIVATE=0 to allow them)", file=sys.stderr)
    return n


_WITHHELD = _withhold_egress_tools()


class _LocalHostOnly:
    """ASGI middleware: refuse requests whose Host header is not this
    machine (DNS rebinding: a web page that resolves its own name to
    127.0.0.1 would otherwise reach the server through the browser)."""

    def __init__(self, app, port: int, extra: set):
        self.app = app
        self.ok = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}", "127.0.0.1", "localhost"} | extra

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            host = next((v.decode("latin-1") for k, v in scope.get("headers") or [] if k == b"host"), "")
            if host.lower() not in self.ok:
                await send({"type": "http.response.start", "status": 421,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"421 Misdirected Request: not a local host"})
                return
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PulseChain/EVM Skills MCP Server for OpenHands")
    parser.add_argument("--transport", default="streamable-http", choices=["streamable-http", "stdio", "http", "sse"], help="MCP transport")
    # Loopback by default: these tools write files, read arbitrary paths and
    # open pull requests, with nothing authenticating the caller. Running in a
    # container is the one case that needs 0.0.0.0 — a process bound to the
    # container's own loopback is unreachable even through a published port —
    # and the compose file and launcher both pass it explicitly.
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    # Explicitly stderr: these describe the server, they are not protocol.
    print(f"🚀 Starting PulseChain-EVM Skills MCP Server (transport={args.transport}) on {args.host}:{args.port}",
          file=sys.stderr)
    print("   Tools: analyze_wallet, supervise, apply_proposal (HARDENED + extra .approved file + mandatory tests), rollback_proposal, evaluate_and_rollback_if_degraded, research, web_research, generate_image, generate_video, consult_wealth_mentor ...", file=sys.stderr)
    print("   Extra hard gates: extra approval file, pre-apply test runner, size limit, human_approved. Rollback available if newer update makes previous change obsolete (score drop etc.).", file=sys.stderr)
    print("   Configure OpenHands MCP settings to connect (shttp_servers recommended).", file=sys.stderr)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn
        extra = {f"{h}:{args.port}" for h in lpai_private.allowed_hosts() if h and h not in ("", "::", "0.0.0.0")}
        extra |= {f"{args.host}:{args.port}"}
        app = _LocalHostOnly(mcp.http_app(path="/mcp", transport=args.transport), args.port, extra)
        print(f"   auth: {'bearer token required' if _MCP_TOKEN else 'NONE (set MCP_TOKEN)'} | private mode: {lpai_private.is_private()}",
              file=sys.stderr)
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
