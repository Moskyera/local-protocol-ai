# experiments/

This folder contains **non-production**, experimental, legacy, or optional code.

## Contents (as of 2026-06 reorganization)
- `voice/` — All voice / Piper / STT / pipecat experiments. Voice support has been removed from the main boot path (start-ai.bat uses llama.cpp only). These may have extra pip dependencies.
- `old_launchers/` — Duplicate or retired start scripts (start-ai-old.bat, New folder copies, start-openhands.ps1, any remaining start-llama-hip.ps1). Use only `start-ai.bat` (and the launch/ copies of the canonical scripts).
- `web/` — mosky_web.py (Gradio JARVIS-style experiment).
- `reports/` — Old duplicate of geopolitical_engine (the real one is at the project root and is part of the sacred briefing system).
- `demos_and_tests/` — Various *_demo.py and non-critical *_test.py files.
- `legacy_agents_v1/` — The older openhands_multiagent/ (v1). Superseded by openhands_multiagent_v2/ + langgraph_orchestrator.py.
- `archive/` — Truly dead files.

## Rules
- Do **not** rely on anything in experiments/ for daily work or the self-improving agent system.
- The agent self-improvement guards (in openhands_skills/guards.py) will still block any proposals that try to touch sacred briefing files, even if someone puts copies here.
- If you need something from here, copy it consciously and update imports.

Main production paths:
- Market engines stay at project root.
- Agentic system = openhands_skills/ + openhands_mcp/ + openhands_multiagent_v2/ + langgraph_orchestrator.py + automation/
- Boot = start-ai.bat (the only one you should double-click for normal use).

See ORGANIZATION.md at the project root for the full map.
