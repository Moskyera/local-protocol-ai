# MOSKY AI Workstation - Organization (2026-06)

This document describes the cleaned layout after the 2026-06 reorganization.

**Golden Rule**: The daily Telegram briefing (6 messages) is a **sacred, separate system**. It must continue to work flawlessly forever. Do not touch the files that generate or send it.

## Boot (the only thing most people should run)
- `start-ai.bat` (from C:\AI or inside market-agent) — canonical. It:
  - Cleans ports
  - Starts the reliable llama.cpp Vulkan backend (start-llama-vulkan.ps1)
  - Ensures Docker
  - Builds custom runtime image
  - Starts the two containers (cranky_hypatia OpenHands UI + mcp-skills sidecar)
  - Starts the Streamlit dashboard
- `stop-ai.bat` / `restart-ai.bat` — wrappers around the above.

All other .bat / .ps1 live under `launch/` (copies of the canonical ones) or have been retired to `experiments/old_launchers/`.

## Sacred / Briefing Zone (DO NOT TOUCH)
- telegram_engine.py
- send_briefing.bat + send_simplex_briefing.py
- master_market_brain.py
- macro_tech_report.py
- geopolitical_engine.py
- corporate_news_engine.py
- Any code whose only job is producing the 6 daily messages

These are protected by code in `openhands_skills/guards.py` (FORBIDDEN_PATHS). The self-improving agents are not allowed to propose changes here.

`tool_integration_hub.py` (allowed area) has lazy bridges that can optionally call some of the above — this is intentional and must keep working.

## Production / Daily Use Areas
- Core market engines (regime_engine, signal_engine, market_snapshot_engine, volatility_engine, etc.) — stay at project root.
- `llm_client.py` + `llm_agent.py` — primary interface to llama.cpp (OpenAI compatible on :8080). No Ollama in main path.
- `automation/` (promoted from automation_examples) — reliable direct Python automation. Example: `wallet_forensics_automation.py`. Use this when you want exact USD risk/PnL without going through the chat UI.
- `dashboard.py` — Streamlit market intelligence UI (started by start-ai.bat).

## Agentic Self-Improving System (the powerful "rest")
- `openhands_skills/` — the heart (chain_analysis_expert with your exact USD tiers, guards.py, langgraph_orchestrator.py, research_agent.py, evaluation_harness.py, tool_integration_hub.py, many specialist experts...).
- `openhands_mcp/` — the MCP sidecar that exposes real native tools (analyze_wallet, scan_large_ecosystem_movements, research, execute_v2_task, etc.) to the OpenHands UI at 8765.
- `openhands_multiagent_v2/` — current multi-agent implementation (supervisor, hyper_evolution, market_analyst_v2, strategic_oracle...).
- `langgraph_orchestrator.py` — recommended explicit graph layer for automation and the 3-specialist (Blockchain / Research / Engineering) supervisor. Bypasses many LLM hallucination problems by using direct Python experts for critical numbers.
- `automation/` — see above.

The agent system is designed to research, propose improvements (only inside allowed paths), get human approval, apply guarded edits, and measure whether the Blockchain expert actually got better (via evaluation_harness).

## Experiments / Legacy / Optional (do not rely on these for production)
- `experiments/`
  - `voice/` — everything voice-related (Piper Greek, STT, pipecat). Voice was removed from the main boot path.
  - `old_launchers/` — retired start scripts.
  - `web/` — mosky_web (Gradio experiment).
  - `reports/` — old duplicate of geopolitical code.
  - `demos_and_tests/` — most demo and test scripts.
  - `legacy_agents_v1/` — the older openhands_multiagent (v1). Superseded.
  - `archive/`

See `experiments/README.md` for details.

## Key Supporting Files
- `verify_system.py` — run this after any change. It checks both the sacred path and the full agentic/automation path. Must stay green.
- `requirements.txt` (being split in the reorganization into core / agentic / experiments for clarity).
- `runtime/Dockerfile` — custom image with skills preloaded for sandboxes + MCP.
- `memory/` — persistent state for the agent system (proposals, supervisor memory, vector db, etc.).
- `AGENT_UPGRADE_PLAN.md` — living history of the self-improving system (very detailed).

## How to Use
- Daily briefings: just run `send_briefing.bat` (or let it be scheduled).
- Full environment: `start-ai.bat`.
- Reliable wallet forensics without chat: `python automation\wallet_forensics_automation.py 0x... pulsechain`
- Advanced agent work: use the LangGraph supervisor or the MCP tools inside the OpenHands UI (localhost:3000).
- Self-improvement proposals: go through the guarded flow (the system will refuse anything that touches sacred briefing files).

## Python Environment
- Primary: `C:\AI\ai-env` (Python 3.14).
- The Docker runtime image uses Python 3.12 (by design).
- Always activate the venv (the .bat files do this for you).

This layout makes it obvious what is production, what is the powerful agent research platform, and what is experimental, while keeping the daily briefing completely isolated and reliable.
