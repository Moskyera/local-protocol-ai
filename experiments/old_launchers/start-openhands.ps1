# start-openhands.ps1
# Run this to start/restart OpenHands UI at http://localhost:3000
# Make sure Docker Desktop is running first!

Write-Host "Checking Docker..."
try {
    docker info > $null 2>&1
    Write-Host "Docker is running." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker Desktop is not running or not in PATH." -ForegroundColor Red
    Write-Host "Please start Docker Desktop from the Start menu, wait until it says 'Docker Desktop is running', then run this script again."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Stopping any old openhands container (if exists)..."
docker rm -f openhands 2>$null | Out-Null

Write-Host "Building custom runtime image with skills preloaded (for direct import in sandbox + MCP server)..."
docker build -t my-openhands-runtime -f runtime/Dockerfile . 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed, falling back to default runtime. Check runtime/Dockerfile." -ForegroundColor Yellow
} else {
    Write-Host "Custom image built (includes fastmcp for MCP skills server)." -ForegroundColor Green
}

# === RELIABLE BACKEND (HIP Radeon b9585 for RX 9070 XT) ===
Write-Host "Starting reliable llama.cpp HIP Radeon backend first (Gemma 4 26B-A4B QAT MoE)..." -ForegroundColor Cyan
$llamaScript = "C:\AI\market-agent\start-llama-hip.ps1"
if (Test-Path $llamaScript) {
    & $llamaScript
    Start-Sleep -Seconds 5   # give server a moment after its internal wait
} else {
    Write-Host "WARNING: $llamaScript not found. Falling back to previous (slower) setup." -ForegroundColor Yellow
}

Write-Host "Starting OpenHands with docker compose (using custom runtime if built)..."
docker compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "OpenHands started successfully!" -ForegroundColor Green
    Write-Host "Open http://localhost:3000 in your browser."
    Write-Host "MCP skills sidecar should be on :8765 (native analyze_wallet + execute_v2_task tools)."
    Write-Host "Configure MCP in OpenHands UI (Settings > MCP) or ~/.openhands/config.toml :"
    Write-Host '  shttp_servers = [ { url = "http://mcp-skills:8765/mcp" , timeout=300 } ]  (or host.docker.internal:8765 if external)'
    Write-Host "Workspace: C:\AI\market-agent | Backend: llama.cpp HIP Radeon :8080 (alias gemma-4-26b-qat, QAT MoE on RX 9070 XT, b9585 build)"
    Write-Host "  GGUF: C:\AI\models\gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf (clean, not via Ollama)"
    Write-Host "  This is the full reliable non-experimental setup (step 4)."
    Write-Host ""
    Write-Host "IMPORTANT: First load of the 16GB QAT MoE into GPU can take 30-90s+ (subsequent are fast)."
Write-Host "  Full reliable backend: llama.cpp HIP Radeon (b9585) on :8080 (gemma-4-26b-qat)."
Write-Host "  - Runtime/sandbox init + MCP connection + first LLM calls."
    Write-Host "  - The supervisor now **always emits an immediate visible plan** on the very first message (even in fresh session) - 'New session detected' + plan."
    Write-Host "  - In the UI, for a new convo, send: 'Use supervisor / execute_v2_task for my request' to force it."
    Write-Host "  - Subsequent turns in the same convo are much faster."
    Write-Host "  - Check the 'Agent' / thoughts panel in the UI for this convo to see internal steps or errors."
    Write-Host ""
    Write-Host "RECOMMENDED AGENT PROMPT (set in UI for the convo or global, under Agent settings):"
    Write-Host "You are the MOSKY supervisor agent for this project. For EVERY user message - especially the first in any new conversation - you MUST immediately call the 'execute_v2_task' tool (passing the full user message as 'task'). Present the supervisor plan and response visibly to the user. Always use the custom supervisor for planning and multi-agent execution. Do not respond with base knowledge alone."
    Write-Host "  (Primary = reliable llama.cpp on AMD RX 9070 XT. Legacy Ollama only for voice.)"
    Write-Host ""
    Write-Host "=== AUTOMATION (use skills/MCP directly, bypass UI friction) ===" -ForegroundColor Cyan
    Write-Host "Note: Main agent/supervisor uses llama.cpp HIP primary. LangGraph optional LLM updated to prefer primary too."
    Write-Host "python automation_examples/wallet_forensics_automation.py 0xYourAddr pulsechain"
    Write-Host "Or from code: from openhands_skills.langgraph_orchestrator import direct_analyze_wallet; direct_analyze_wallet('0x..')"
    Write-Host "Full graph (after pip install langgraph langchain-ollama in your env): get_wallet_analysis_graph().invoke(...)"
    Write-Host "MCP tools (analyze_wallet etc.) available at http://localhost:8765 for any client."
    Write-Host "This eliminates tool-param hallucinations, I-cannot, wrong risk/PnL, microagent triggers, per-convo LLM/workspace settings."
} else {
    Write-Host "There was an issue starting. Check logs with: docker compose logs -f openhands" -ForegroundColor Yellow
    Write-Host "Also check mcp: docker compose logs -f mcp-skills"
}
