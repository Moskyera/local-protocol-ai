# OpenHands MCP Skills Server

Professional extension for the openhands_skills + openhands_multiagent_v2 system.

Exposes:
- `analyze_wallet(address, chain="pulsechain")`: Full real on-chain forensics with accurate USD native inflows, risk scoring (user-specified tiers: >$50k / $10k / $1k / $100), PnL + market context, portfolio, swaps (PulseX subgraph), approvals, persistent memory cross-refs, meme/low-activity pattern detection.
- `execute_v2_task(task_description)`: Automatic router for EVM/PulseChain smart contracts, DeFi, audits — full pipeline via v2 agents + experts (code + audit + tests + deploy + chain analysis when relevant).
- Supporting: market context bridge.

## Why this upgrade?
- Solves agent refusals ("I cannot access blockchain") by registering real capabilities as **native tools** (first-class in the agent's tool list + schemas).
- Bypasses fragile "write Python import + execute_ipython_cell every turn" and security_risk tool call errors for data tasks.
- Microagents (knowledge) + MCP tools = reliable keyword-triggered professional behavior.
- Leverages community/devs work: OpenHands official MCP support + FastMCP (used internally by OpenHands) + examples like custom openhands-mcp repos.
- Keeps everything free-preferring (Moralis optional key + public BlockScout / PulseX GraphQL / RPC) + your existing defensive code / path setup / custom runtime.

This takes the system to professional/agentic levels for PulseChain/EVM/DeFi work inside the nice localhost:3000 UI.

## Setup (already applied in this workspace)
1. Rebuild + restart: Use the canonical `start-ai.bat` (from C:\AI). The old `start-openhands.ps1` has been retired to experiments/old_launchers/. The sophisticated port cleanup + llama + Docker + MCP sidecar flow is now in start-ai.bat.
2. mcp-skills container starts on :8765 (streamable-http - switched for lower end-to-end latency vs SSE).
3. Configure in OpenHands:
   - Preferred: UI **Settings > MCP** → add Streamable HTTP server `http://mcp-skills:8765/mcp` (or `http://localhost:8765/mcp` / `http://host.docker.internal:8765/mcp`).
   - Or edit `~/.openhands/config.toml` (see the section we added) and restart openhands container.
4. Added in-memory lru_cache on analyze_address to avoid re-fetching on repeats (big win for latency in chat/debug sessions).
4. New conversation (or force new runtime by removing old runtime containers).
5. Test with natural language: "analyze the wallet 0x000000000000000000000000000000000000dEaD on pulsechain using the skills for full profile, risk score with USD native inflows, pnl..."

The agent should now see and prefer the native tools (no more "I cannot" + no need to paste Python).

## Files
- `server.py`: FastMCP server with tool wrappers (imports the real experts safely).
- Integrated with existing `runtime/Dockerfile` (fastmcp pip), `docker-compose.yml` (sidecar service), start script, microagent .md files (updated instructions).

## Notes
- Rebuild the custom image after changes to Dockerfile or mcp code for the sidecar.
- MORALIS_API_KEY (free tier) is picked from .env / env in the mcp service for richer categorized history; public fallbacks always work.
- For pure code-gen tasks the agent still uses its normal execute tools inside the (now preloaded) sandbox.
- If MCP not connected, the old microagent + code exec fallback still documented and works (with custom runtime).

This + the existing real-data chain logic + v2 automatic routing + persistent memory + market bridge = a powerful, evolving professional setup for your use cases.

Update microagents or add more @mcp.tool wrappers as needed for new experts.