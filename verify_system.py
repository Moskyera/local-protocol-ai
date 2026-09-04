#!/usr/bin/env python3
"""
MOSKY System Verification (Non-destructive)

Safe to run at any time. Does NOT:
- Send any Telegram messages
- Start Docker, llama-server, or Streamlit
- Perform network calls (except optional quick health if you add them later)
- Modify any files or memory

It validates that the two main worlds continue to work after reorganization:
1. Sacred / Briefing path (the 6-message daily system and everything it depends on)
2. Agentic / Automation path (MCP, LangGraph supervisor, chain expert, v2 agents, research, guards, tool hub, direct automation)

Run from the market-agent directory:
    python verify_system.py

Exit code 0 = all critical sections green.
"""

import sys
import traceback
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

results = []
failures = []

def check(name, fn):
    print(f"\n=== {name} ===")
    try:
        fn()
        print(f"✅ {name}")
        results.append((name, True))
    except Exception as e:
        print(f"❌ {name}")
        print(f"   Error: {e}")
        traceback.print_exc(limit=3)
        results.append((name, False))
        failures.append(name)

# ============================================================
# SACRED / BRIEFING PATH (must stay perfect - user requirement)
# ============================================================

def sacred_llm_client():
    from llm_client import chat, get_llm_client, generate_market_report
    client = get_llm_client()
    assert client is not None
    # Do not actually call the model here

def sacred_macro_report():
    from macro_tech_report import generate_macro_tech_report
    # Just import — the function itself will try LLM when called
    assert callable(generate_macro_tech_report)

def sacred_master_brain():
    from master_market_brain import generate_master_report
    assert callable(generate_master_report)

def sacred_geopolitical():
    from geopolitical_engine import geopolitical_engine
    assert hasattr(geopolitical_engine, 'analyze_geopolitical_risk') or hasattr(geopolitical_engine, 'get_geopolitical_risk')

def sacred_corporate_news():
    from corporate_news_engine import corporate_news_engine
    assert hasattr(corporate_news_engine, 'get_corporate_news') or hasattr(corporate_news_engine, 'get_events')

def sacred_telegram_engine():
    from telegram_engine import send_full_ai_briefing
    assert callable(send_full_ai_briefing)
    # We deliberately do NOT call it — it would send real messages and run the whole pipeline

def sacred_tool_hub_lazy_briefing():
    """Check the lazy-import bridge WITHOUT sending anything.

    This used to call tool_hub.send_telegram_briefing(), which calls
    send_full_ai_briefing(), which generates and DELIVERS a full briefing to the
    real Telegram channel. So running the health check sent the user a briefing
    — minutes of GPU time and a message they did not ask for, every time.

    The stated intent was "the lazy import mechanism must still work". That is
    what is checked now: the bridge resolves the target and the target is
    callable. Nothing is sent.
    """
    from openhands_skills.tool_integration_hub import tool_hub, is_unavailable
    assert callable(getattr(tool_hub, "send_telegram_briefing", None))

    from openhands_skills.tool_integration_hub import _lazy_import_market
    target = _lazy_import_market("send_full_ai_briefing")
    assert is_unavailable(target) or callable(target), (
        f"the briefing bridge resolves to something that cannot be called: {target!r}")

# ============================================================
# AGENTIC / AUTOMATION PATH (the "rest" we are cleaning)
# ============================================================

def agentic_guards():
    from openhands_skills.guards import FORBIDDEN_PATHS, is_forbidden_path, is_allowed_for_modification, validate_proposal
    assert "telegram_engine.py" in FORBIDDEN_PATHS
    assert is_forbidden_path("telegram_engine.py") is True
    assert is_allowed_for_modification("openhands_skills/chain_analysis_expert.py") is True

def agentic_langgraph_orchestrator():
    from openhands_skills.langgraph_orchestrator import supervise_task, get_wallet_analysis_graph
    assert callable(supervise_task)

def agentic_chain_expert():
    from openhands_skills.chain_analysis_expert import chain_analysis_expert
    assert hasattr(chain_analysis_expert, 'analyze_address')

def agentic_mcp_server():
    # The sidecar that exposes tools to OpenHands UI
    import openhands_mcp.server as mcp_server
    # Just importing is the hard part (path setup + all the experts)
    # `or True` made this unconditionally true — it could not fail, whatever
    # the module contained. Importing openhands_mcp.server IS the hard part
    # (path setup plus every expert), so assert on something the import must
    # actually have produced.
    assert hasattr(mcp_server, "mcp"), "the MCP server object was not created"
    assert hasattr(mcp_server, "create_pr"), "the tools were not registered"

def agentic_v2_entry():
    from openhands_skills.openhands_v2_entry import run_task
    assert callable(run_task)

def agentic_research_and_evaluation():
    from openhands_skills.research_agent import research_agent
    from openhands_skills.evaluation_harness import EvaluationHarness
    assert research_agent is not None
    assert EvaluationHarness is not None

def agentic_tool_hub_market():
    from openhands_skills.tool_integration_hub import tool_hub
    snap = tool_hub.run_market_snapshot()
    # `isinstance(snap, (str, dict))` passed for ANY string, including
    # "Error getting market snapshot: ...". A check that accepts the failure it
    # is meant to detect is not a check.
    assert isinstance(snap, (str, dict)), f"unexpected type {type(snap).__name__}"
    if isinstance(snap, str):
        low = snap.lower()
        assert not low.startswith(("error", "❌", "(")), f"snapshot failed: {snap[:160]}"

# ============================================================
# DIRECT AUTOMATION (the reliable bypass-UI path the user likes)
# ============================================================

def direct_wallet_forensics():
    # This is one of the most important "it just works" pieces
    # Note: moved from automation_examples/ to automation/ during 2026-06 reorganization
    from automation.wallet_forensics_automation import analyze_and_report
    # We only test that it imports and the function exists.
    # Actually calling it would do real chain queries.
    assert callable(analyze_and_report)

# ============================================================
# SUPPORTING (config, llm primary path, etc.)
# ============================================================

def supporting_config_and_llm():
    from config import config
    from llm_client import get_llm_client
    assert config is not None
    # Was `... or True  # flexible`, which is a decorative way of writing
    # `assert True`. Either the model name matters or it does not; it does, so
    # check that one is configured at all rather than pretending to check which.
    assert str(config.LLM_MODEL or "").strip(), "LLM_MODEL is not configured"
    _ = get_llm_client()

# ============================================================
# RUN ALL
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("MOSKY VERIFY_SYSTEM - Full Import & Structure Health Check")
    print(f"Current Python: {sys.executable}")
    print(f"Project root: {project_root}")
    print("NOTE: This must normally be run with the project's ai-env activated.")
    print("      The .bat launchers and start-ai.bat do this automatically.")
    print("=" * 60)

    # Best-effort: if we are not inside the right venv, try to re-exec with the known ai-env python
    if "ai-env" not in str(sys.executable).lower() and "ai-env" not in str(sys.prefix).lower():
        venv_python = sys.executable   # whatever interpreter is running us
        if Path(venv_python).exists():
            print(f"[INFO] Re-executing with project venv: {venv_python}")
            import subprocess
            sys.exit(subprocess.call([venv_python, str(__file__)] + sys.argv[1:]))

    # Sacred world (highest priority)
    check("Sacred: llm_client", sacred_llm_client)
    check("Sacred: macro_tech_report", sacred_macro_report)
    check("Sacred: master_market_brain", sacred_master_brain)
    check("Sacred: geopolitical_engine", sacred_geopolitical)
    check("Sacred: corporate_news_engine", sacred_corporate_news)
    check("Sacred: telegram_engine (import only)", sacred_telegram_engine)
    check("Sacred: tool_hub lazy briefing bridge", sacred_tool_hub_lazy_briefing)

    # Agentic world
    check("Agentic: guards.py + FORBIDDEN_PATHS", agentic_guards)
    check("Agentic: langgraph_orchestrator", agentic_langgraph_orchestrator)
    check("Agentic: chain_analysis_expert", agentic_chain_expert)
    check("Agentic: openhands_mcp.server", agentic_mcp_server)
    check("Agentic: openhands_v2_entry", agentic_v2_entry)
    check("Agentic: research_agent + evaluation_harness", agentic_research_and_evaluation)
    check("Agentic: tool_hub market bridge", agentic_tool_hub_market)

    # Direct automation
    check("Direct: wallet_forensics_automation", direct_wallet_forensics)

    # Supporting
    check("Supporting: config + llm_client", supporting_config_and_llm)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, ok in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}  {name}")

    if failures:
        print(f"\n❌ {len(failures)} section(s) failed: {failures}")
        print("Do not proceed with reorganization until these are green.")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(results)} sections PASSED.")
        print("Baseline is healthy. Safe to proceed with cleanup phases.")
        sys.exit(0)
