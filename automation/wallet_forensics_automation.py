#!/usr/bin/env python3
"""
STANDALONE AUTOMATION EXAMPLE - Wallet Forensics + USD Risk/PnL (no OpenHands UI or chat required).

This demonstrates exactly what "use the skills as automation" means:
- Import the expert (or the langgraph_orchestrator) from anywhere.
- Call directly with address/chain.
- Get your exact USD-tiered risk ( >50000 very large, >10000 large etc. ), PnL, flows, portfolio, persistent memory hits, explorer links.
- Run from PowerShell, Task Scheduler, cron (WSL), a watcher script, or your own FastAPI/Telegram bot layer.
- Zero per-convo UI settings, zero microagent trigger guessing, zero tool param hallucinations on the core (address is python arg).
- The OpenHands web UI (localhost:3000) and its CodeAct loop can stay for interactive coding if you like; this path bypasses it completely for automatic/reliable use.

Usage examples:
  # PowerShell
  python automation/wallet_forensics_automation.py 0x38be95f628ed004a000ddf8724142a95e3c4b492 pulsechain

  # From another script
  from automation.wallet_forensics_automation import analyze_and_report
  report = analyze_and_report("0xYourWallet", "pulsechain")

Requirements: the openhands_skills must be importable (the package _auto_path_setup handles common cases including C:/AI/market-agent).

For even more power (graphs, persistence, parallel, streaming, human-in-loop, visual debug): use the langgraph_orchestrator (see below).

Moralis note: if you see 401s, the free key may not grant /history on pulse (or expired). Public fallbacks still give basic native + token flows + nonce. USD values from balances when available. Improve fallbacks or use working key as needed.

Keep all Telegram *engine*.py untouched.
"""

import os
import sys
import json
from datetime import datetime, timezone

# Make skills importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from openhands_skills.chain_analysis_expert import chain_analysis_expert
except Exception as e:
    print("ERROR: cannot import chain_analysis_expert. Run from project root or ensure PYTHONPATH/C:/AI/market-agent in path.")
    print(e)
    sys.exit(1)

# Also try the advanced orchestrator (LangGraph if you installed the extras)
try:
    from openhands_skills.langgraph_orchestrator import (
        get_wallet_analysis_graph,
        direct_analyze_wallet,
        HAS_LANGGRAPH,
    )
    HAS_ORCH = True
except Exception:
    HAS_ORCH = False
    HAS_LANGGRAPH = False

def analyze_and_report(address: str, chain: str = "pulsechain", context: str = "automation run", use_graph: bool = True) -> dict:
    """Main automation function. Returns the full structured result + convenience fields."""
    address = address.strip()
    if not address.startswith("0x") or len(address) != 42:
        raise ValueError("address must be 0x... 42 chars")

    if use_graph and HAS_ORCH:
        # Preferred: the graph path (even in fallback mode it is reliable)
        g = get_wallet_analysis_graph(use_persistence=False)
        # Support both .invoke (real graph) and direct callable fallback
        if hasattr(g, "invoke"):
            out = g.invoke({"user_input": f"analyze {address} on {chain} {context}"})
        else:
            out = g({"user_input": f"analyze {address} on {chain} {context}"})
        report = out.get("final_report") or out.get("report") or {}
        report["_via"] = "langgraph_orchestrator" + (" (fallback direct)" if getattr(g, "is_fallback", False) else "")
        report["_summary_text"] = out.get("summary", "")
        return report

    # Pure direct (always works, maximum simplicity)
    result = chain_analysis_expert.analyze_address(address, chain=chain, context=context)
    result["_via"] = "direct_expert"
    return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python automation/wallet_forensics_automation.py <0xADDRESS> [pulsechain|ethereum] [optional context]")
        print("Example: python automation/wallet_forensics_automation.py 0x38be95f628ed004a000ddf8724142a95e3c4b492 pulsechain")
        sys.exit(1)

    addr = sys.argv[1]
    ch = sys.argv[2] if len(sys.argv) > 2 else "pulsechain"
    ctx = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "cli automation test - risk pnl native inflows"

    print(f"[{datetime.now(timezone.utc).isoformat()}Z] AUTOMATION RUN for {addr} on {ch}")
    print("Using graph orchestrator (LangGraph or fallback):" if HAS_ORCH else "Using direct expert call (install langgraph* for full graph mode):")

    try:
        rep = analyze_and_report(addr, ch, ctx, use_graph=True)
    except Exception as e:
        print("ERROR during analysis:", e)
        # last resort direct
        rep = chain_analysis_expert.analyze_address(addr, chain=ch, context=ctx)

    # Pretty console
    rs = rep.get("risk_score", rep.get("final_report", {}).get("risk_score", {})) if isinstance(rep, dict) else {}
    pnl = rep.get("pnl_estimate", rep.get("final_report", {}).get("pnl_estimate", {})) if isinstance(rep, dict) else {}

    print("\n=== RISK / PnL (USD per your thresholds) ===")
    print(f"Level: {rs.get('level', 'N/A')}  score={rs.get('score', 'N/A')}")
    print(f"Native inflow USD: ${rs.get('native_inflow_usd', 0):,.2f}  (PLS: {rs.get('native_inflow_pls', 0):,.0f})")
    print(f"Pattern: {rs.get('pattern_match', 'N/A')}")
    print("Reasons:", rs.get("reasons", []))
    print("Recommendations:", rs.get("recommendations", []))
    print("PnL:", pnl)

    print("\n=== Explorer ===")
    print(rep.get("explorer_link") or (rep.get("final_report", {}) or {}).get("explorer_link") or "N/A")

    # Full for scripts / json
    print("\n=== FULL STRUCTURED (for your scripts/bots) ===")
    # Avoid dumping huge history unless asked
    safe = {k: v for k, v in (rep.get("final_report") or rep).items() if k not in ("incoming_flows", "outgoing_flows", "real_activity", "token_buy_sell_history_and_coins", "actionable_agent_steps_for_real_history")}
    print(json.dumps(safe, indent=2, default=str)[:3000])

    # Show how to integrate e.g. for alerts
    if rs.get("native_inflow_usd", 0) > 10000 or rs.get("score", 0) >= 45:
        print("\n>>> ALERT CONDITION MET (big inflow or elevated risk) - your automation can now post to Telegram / log / notify / etc.")

if __name__ == "__main__":
    main()
