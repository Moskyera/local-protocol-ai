@echo off
setlocal enabledelayedexpansion
TITLE Local Protocol AI - BOOT
color 0A

:: === WHERE THINGS ARE ===
:: Derived from THIS script's own location, never written down. That is what
:: lets the repository be cloned anywhere: PROJECT is the folder this file sits
:: in, and AI_ROOT is its parent.
set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
for %%I in ("%PROJECT%\..") do set "AI_ROOT=%%~fI"
set "USER_OPENHANDS=%USERPROFILE%\.openhands"

:: Private mode (the default): telemetry switches, tool-server token. See docs/PRIVACY.md
call "%PROJECT%\scripts\private-env.bat"

:: The Python to use, in order of preference: a virtualenv inside the repo,
:: the shared one beside it, and otherwise stop with instructions. Failing
:: here with a clear message beats failing later on a confusing ImportError.
set "VENV="
if exist "%PROJECT%\.venv\Scripts\python.exe" set "VENV=%PROJECT%\.venv"
if not defined VENV if exist "%AI_ROOT%\ai-env\Scripts\python.exe" set "VENV=%AI_ROOT%\ai-env"
if not defined VENV (
    echo.
    echo [!] No Python virtualenv found. Looked in:
    echo       %PROJECT%\.venv
    echo       %AI_ROOT%\ai-env
    echo.
    echo     Create one and install the requirements:
    echo         python -m venv .venv
    echo         .venv\Scripts\activate
    echo         pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:: === WORKSPACE = the folder OpenHands can read (default = market-agent) ===
:: 2nd arg:  "full"/"root"/"all" = the whole C:\AI  ^|  <path> = your own folder
:: or set AI_WORKSPACE=... before running. Launchers + memory/skills stay in market-agent.
set WORKSPACE=%PROJECT%
if /i "%~2"=="full" (set WORKSPACE=%AI_ROOT%) else if /i "%~2"=="root" (set WORKSPACE=%AI_ROOT%) else if /i "%~2"=="all" (set WORKSPACE=%AI_ROOT%) else if not "%~2"=="" (set WORKSPACE=%~2)
if defined AI_WORKSPACE set WORKSPACE=%AI_WORKSPACE%

set OPENHANDS_PORT=3000
set STREAMLIT_PORT=8501
set MCP_PORT=8765

echo ========================================
echo AI WORKSTATION BOOT - PERSISTENT MODE
echo ========================================

:: === UPDATE CHECK ===
:: Prints a table of what is new since the running version, and prints
:: NOTHING when there is nothing to say. The check is bounded, cached for
:: an hour, and always exits 0: failing to reach GitHub must never be the
:: reason the stack does not boot. It reads which repo to ask about from
:: `git remote origin`, so a plain clone needs no configuration and an
:: unpublished tree stays silent instead of warning about a guessed name.
if exist "%VENV%\Scripts\python.exe" (
    pushd "%PROJECT%"
    "%VENV%\Scripts\python.exe" -X utf8 -m local_ai
    popd
)

:: Every service below publishes on 127.0.0.1 ONLY. None of them has any
:: authentication: the OpenHands UI can run containers as root through the
:: mounted docker socket, and the MCP sidecar writes files and opens pull
:: requests for anyone who can reach it. Publishing on 0.0.0.0 would hand
:: that to every machine on whatever network you happen to be joined to.
:: === PORT CLEANUP (prevents address-in-use after reboot/shutdown) ===
echo [CLEANUP] Closing old ports and llama-server (Vulkan backend for RX 9070 XT)...
taskkill /F /IM "llama-server.exe" >nul 2>&1
for %%p in (%OPENHANDS_PORT% %STREAMLIT_PORT% %MCP_PORT% 8080) do (
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%%p " 2^>nul') do (
        taskkill /F /PID %%i >nul 2>&1
    )
)

:: === CHOOSE LLM BACKEND (16GB VRAM = ONE model at a time) ===
:: Default (no argument) = gemma (market briefings). "coder" = Qwen3-Coder-30B (dev agents).
set LLAMA_SCRIPT=start-llama-vulkan.ps1
set BACKEND_NAME=gemma-4-26b-qat (market)
set OH_MODEL=openai/gemma-4-26b-qat
set OH_ALIAS=gemma-4-26b-qat
if /i "%~1"=="coder" (
    set LLAMA_SCRIPT=start-llama-coder.ps1
    set BACKEND_NAME=qwen3-coder-30b (coding)
    set OH_MODEL=openai/qwen3-coder-30b
    set OH_ALIAS=qwen3-coder-30b
)

:: Keep the OpenHands UI/settings model label in sync with the loaded backend.
powershell -ExecutionPolicy Bypass -File "%PROJECT%\sync-openhands-model.ps1" -Model "%OH_MODEL%" 2>&1

:: -BindHost 0.0.0.0 is passed on PURPOSE and only here. The launcher's own
:: default is 127.0.0.1, but the OpenHands container reaches the host through
:: host.docker.internal, which is not loopback, so a loopback-bound server is
:: invisible to it. Because that bind is reachable from the LAN, the server
:: now REQUIRES an API key (-ApiKey): a device on your network can see the
:: port but cannot use your GPU. The key is minted once next to the tool
:: token and handed to the containers below. scripts/private-firewall.ps1
:: closes the port to the LAN entirely.
set "LLAMA_KEY_FILE=%USERPROFILE%\.openhands\agent-canvas\llama-key.txt"
if not exist "%LLAMA_KEY_FILE%" powershell -NoProfile -Command "$b = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [IO.File]::WriteAllText('%LLAMA_KEY_FILE%', 'sk-' + ([Convert]::ToBase64String($b) -replace '[+/=]','x'))" >nul 2>&1
set /p LLAMA_API_KEY=<"%LLAMA_KEY_FILE%"
:: === RELIABLE LLM BACKEND: llama.cpp on AMD RX 9070 XT via Vulkan ===
echo [1/5] Starting llama.cpp backend: %BACKEND_NAME% on :8080 ...
powershell -ExecutionPolicy Bypass -File "%PROJECT%\%LLAMA_SCRIPT%" -Parallel 4 -BindHost 0.0.0.0 -ApiKey "%LLAMA_API_KEY%" 2>&1 || echo [WARNING] llama (Vulkan) starter reported issue (see instructions above). Continuing...
echo Waiting for the backend to become ready. The launcher prints its VRAM budget
echo above: it sizes context and offloaded layers to the card instead of asking for
echo more than the 16 GB it has, which is what bugchecked the machine on 2026-09-03.
set /a _backend_wait=0
:wait_backend
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8080/v1/models' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if %errorlevel% equ 0 goto backend_ready
set /a _backend_wait+=1
if %_backend_wait% gtr 120 (
    echo.
    echo [ERROR] Backend still not responding after ~10 minutes.
    echo The llama-server process is probably not running or crashed during model load (15GB+ QAT model takes time + RAM).
    echo.
    echo Common with current packaging: the llama-server.exe is a small ~9KB loader; the real code is llama-server-impl.dll + Vulkan backend DLLs (latest official win-vulkan build).
    echo.
    echo Immediate fix steps:
    echo   1. End any llama-server in Task Manager if stuck.
    echo   2. Re-run the backend starter alone (it will validate the impl DLL now):
    echo      powershell -ExecutionPolicy Bypass -File "C:\AI\market-agent\start-llama-vulkan.ps1"
    echo   3. Watch for "Backend packaging OK: ... impl DLL X MB" and then "READY on :8080".
    echo   4. Once READY (or even if it says WARNING but process is listening on 8080), re-run:
    echo      cd C:\AI
    echo      .\start-ai.bat
    echo.
    echo To check manually:
    echo   netstat -ano ^| findstr :8080
    echo   Invoke-RestMethod http://localhost:8080/v1/models
    echo.
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul
goto wait_backend
:backend_ready
echo llama.cpp backend is responding on :8080.

:: === DOCKER READY (robust poll - based on official OpenHands docker run examples + community Windows reports for engine readiness after reboot) ===
echo [2/5] Ensuring Docker Engine is ready (required so controller can manage sandboxes via socket; prevents 500s and early failures)...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    :: The usual cause on this machine is that com.docker.service is set to
    :: "Manual" and is Stopped. Docker Desktop then exits within seconds because
    :: it cannot start that service without elevation. Detect it and say so,
    :: instead of polling for 80 seconds and printing a vague message.
    powershell -NoProfile -Command "if ((Get-Service com.docker.service -EA SilentlyContinue).Status -ne 'Running') { exit 3 } else { exit 0 }" >nul 2>&1
    if errorlevel 3 (
        echo.
        echo [!] The Docker Desktop SERVICE is stopped, and starting it needs admin.
        echo     Docker Desktop will keep exiting on its own until this is fixed.
        echo.
        echo     ONE-TIME FIX ^(right-click, Run with PowerShell, accept UAC^):
        echo         C:\AI\fix-docker-admin.ps1
        echo.
        echo     Or just open Docker Desktop yourself and accept its UAC prompt,
        echo     wait for "Engine running", then re-run this script.
        echo.
        pause
        exit /b 1
    )
    echo Launching Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    timeout /t 5 /nobreak >nul
)

:: Poll loop (up to ~80s). This is the key "deep search" fix for "engine running" / commands failing right after launch.
set /a _docker_wait=0
:wait_for_docker
docker info >nul 2>&1
if %errorlevel% equ 0 goto docker_ready
set /a _docker_wait+=1
if %_docker_wait% gtr 40 (
    echo.
    echo Docker Engine not ready. Open Docker Desktop and wait for the engine to show "running", then re-run the .bat.
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_for_docker

:docker_ready
echo Docker Engine ready.

cd /d "%PROJECT%"

:: Build (or reuse) custom runtime image.
:: Per official docs + project's docker-compose: build once with your preloaded skills/LangGraph/fastmcp.
:: Controller (cranky) uses official image; this image is ONLY for AGENT_SERVER (sandboxes) + mcp sidecar.
docker image inspect my-openhands-runtime >nul 2>&1
if %errorlevel% neq 0 (
    echo [build] Building my-openhands-runtime ...
    docker build -t my-openhands-runtime -f runtime/Dockerfile .
    if %errorlevel% neq 0 (
        echo WARNING: build issue. Force later: docker rmi my-openhands-runtime
    )
) else (
    echo Using cached my-openhands-runtime (force: docker rmi my-openhands-runtime)
)

:: === CRANKY_HYPATIA (local3000 OpenHands UI/controller) ===
:: Official/community pattern: controller image (ghcr or docker.all-hands) + AGENT_SERVER_* pointing ONLY to custom runtime for sandboxes.
:: Socket mount provides /var/run/docker.sock inside Linux container so controller can manage sandboxes (main cause of previous 500s).
:: --add-host helps host.docker.internal resolution for Ollama + MCP from inside container (widely recommended in issues/docs).
:: === OPENHANDS v1 (default) ===
:: We run ghcr.io/openhands/openhands:main. The OLD path
:: ghcr.io/all-hands-ai/openhands is frozen at 2025-10-23 (v0.59.0) and never
:: got the security_risk fix, which is why we used to need a local patch.
::
:: UPDATE 2026-09-04, verified against the GHCR manifests and the GitHub API:
:: THIS PATH IS NOW FROZEN TOO. ghcr.io/openhands/openhands:main was last
:: built 2026-07-24. On 2026-07-27 the Python monorepo was moved to
:: OpenHands/legacy and ARCHIVED; OpenHands/OpenHands is a TypeScript repo
:: now. The Dockerised Python GUI is discontinued, not merely behind.
::
:: The latest release, v1.16.0, is Agent Canvas - a DIFFERENT product.
:: ghcr.io/openhands/openhands:1.16 does not exist; a tag bump will fail.
:: The local llama.cpp wiring, the MCP sidecar and the security_risk
:: default were all re-checked and are unaffected. See the footer of
:: market-agent/docker-compose.yml for the full picture.
:: In v1 security_risk is OPT-IN (add_security_risk_prediction defaults to False),
:: so no patch is needed and the agent stops refusing to read files / run commands.
::
:: v1 keeps its settings in a DIFFERENT format, so it gets its own state dir.
:: Set MOSKY_OH=v0 to fall back to the old patched stack.
set OH_IMAGE=ghcr.io/openhands/openhands:main
set OH_STATE=%USERPROFILE%\.openhands-v1
if /i "%MOSKY_OH%"=="v0" (
    set OH_IMAGE=openhands-patched:local
    set OH_STATE=%USER_OPENHANDS%
    docker image inspect openhands-patched:local >nul 2>&1
    if errorlevel 1 docker build -t openhands-patched:local -f "%PROJECT%\runtime\Dockerfile.openhands-patched" "%PROJECT%"
)
if not exist "%OH_STATE%" mkdir "%OH_STATE%"

echo [3/5] Starting OpenHands (%OH_IMAGE%) on local%OPENHANDS_PORT% ...
echo        OpenHands workspace (readable folder): %WORKSPACE%
docker rm -f cranky_hypatia >nul 2>&1

if /i "%MOSKY_OH%"=="v0" (
    docker run -d --name cranky_hypatia -p 127.0.0.1:%OPENHANDS_PORT%:%OPENHANDS_PORT% -v "%WORKSPACE%":/workspace -v %PROJECT%\memory:/app/memory -v %PROJECT%\openhands_skills:/app/openhands_skills -v "%OH_STATE%":/.openhands -v //var/run/docker.sock:/var/run/docker.sock --add-host host.docker.internal:host-gateway -e OPENHANDS_WORKSPACE_BASE=/workspace -e LLM_MODEL=%OH_MODEL% -e OPENAI_BASE_URL=http://host.docker.internal:8080/v1 -e OPENAI_API_KEY=%LLAMA_API_KEY% -e LPAI_PRIVATE=%LPAI_PRIVATE% -e MCP_TOKEN=%MCP_TOKEN% -e DO_NOT_TRACK=1 -v "%PROJECT%\.env.example":/workspace/.env:ro -e AGENT_SERVER_IMAGE_REPOSITORY=my-openhands-runtime -e AGENT_SERVER_IMAGE_TAG=latest -e SANDBOX_VOLUMES=/workspace:/workspace %OH_IMAGE%
) else (
    docker run -d --name cranky_hypatia -p 127.0.0.1:%OPENHANDS_PORT%:3000 -v "%WORKSPACE%":/workspace -v "%OH_STATE%":/.openhands -v //var/run/docker.sock:/var/run/docker.sock --add-host host.docker.internal:host-gateway -e SANDBOX_USER_ID=0 -e SANDBOX_VOLUMES="%WORKSPACE%:/workspace" -e LPAI_PRIVATE=%LPAI_PRIVATE% -e MCP_TOKEN=%MCP_TOKEN% -e DO_NOT_TRACK=1 -v "%PROJECT%\.env.example":/workspace/.env:ro %OH_IMAGE%
)

:: === MCP SKILLS SIDECAR (8765) ===
:: Uses the custom runtime image (has the skills preloaded + fastmcp). Direct python -m command.
:: Matches project docker-compose mcp-skills service. Uses host port publish + host.docker.internal in OpenHands config for reachability (no compose network).
echo [4/5] Starting MCP Skills sidecar (native tools on 8765: analyze_wallet with exact 'address' param, execute_v2_task, get_market_context - using streamable-http for lower latency)...
docker rm -f mcp-skills >nul 2>&1
:: In private mode the container gets NO .env (the example file masks it and
:: the keys are unused anyway) and only loopback + host.docker.internal.
:: Outside private mode the keys are passed, as before.
if /i "%LPAI_PRIVATE%"=="0" (
    docker run -d --name mcp-skills -p 127.0.0.1:%MCP_PORT%:%MCP_PORT% --env-file .env -e LPAI_PRIVATE=0 -e MCP_TOKEN=%MCP_TOKEN% -e OPENAI_API_KEY=%LLAMA_API_KEY% -e PYTHONPATH=/workspace -v %PROJECT%:/workspace -v //var/run/docker.sock:/var/run/docker.sock my-openhands-runtime:latest python -m openhands_mcp.server --transport streamable-http --host 0.0.0.0 --port %MCP_PORT%
) else (
    docker run -d --name mcp-skills -p 127.0.0.1:%MCP_PORT%:%MCP_PORT% -e LPAI_PRIVATE=1 -e LPAI_ALLOW_HOSTS=host.docker.internal -e MCP_TOKEN=%MCP_TOKEN% -e OPENAI_API_KEY=%LLAMA_API_KEY% -e DO_NOT_TRACK=1 -e PYTHONPATH=/workspace -v %PROJECT%:/workspace -v "%PROJECT%\.env.example":/workspace/.env:ro -v //var/run/docker.sock:/var/run/docker.sock my-openhands-runtime:latest python -m openhands_mcp.server --transport streamable-http --host 0.0.0.0 --port %MCP_PORT%
)

:: === POINT OPENHANDS v1 AT THE LOADED MODEL + THE SKILLS SIDECAR ===
:: v1 stores settings under agent_settings and only accepts *_diff payloads, so
:: this must be done through its API, not by writing settings.json. It re-runs on
:: every boot, which is exactly what makes switching market <-> coding work.
if /i not "%MOSKY_OH%"=="v0" (
    echo [4b/5] Pointing OpenHands v1 at %OH_ALIAS% + MOSKY skills...
    "%VENV%\Scripts\python.exe" "%PROJECT%\configure-openhands-v1.py" %OH_ALIAS% --port %OPENHANDS_PORT% --mcp-port %MCP_PORT% --mcp-token "%MCP_TOKEN%" --api-key "%LLAMA_API_KEY%"
    if errorlevel 1 echo [WARNING] Could not configure OpenHands v1 automatically - set the model in the UI under Settings ^> LLM.
)

:: Short settle so containers are fully up before browsers and user interaction
timeout /t 4 /nobreak >nul

:: === STREAMLIT DASHBOARD ===
echo [5/5] Starting Market Dashboard...
start "Market Dashboard" cmd /k "%VENV%\Scripts\activate.bat && cd %PROJECT% && streamlit run dashboard.py --server.address 127.0.0.1 --server.port %STREAMLIT_PORT%"

:: === OPEN BROWSERS + STATUS ===
echo Opening services...
start http://localhost:%OPENHANDS_PORT%
start http://localhost:%STREAMLIT_PORT%

echo.
echo ========================================
echo AI WORKSTATION ONLINE (start-ai.bat / stop-ai.bat)
echo ========================================
echo OpenHands (local3000 - UI/controller) : http://localhost:%OPENHANDS_PORT%
echo LLM backend (llama.cpp :8080)         : gemma-4-26b-qat (QAT MoE, Vulkan on RX 9070 XT)
echo MCP sidecar (native tools, 8765)      : http://localhost:%MCP_PORT%  (streamable-http)
echo Dashboard                             : http://localhost:%STREAMLIT_PORT%
echo.
echo Status:
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" | findstr /i "cranky mcp"
echo.
echo NEW: MCP tools (analyze_wallet with real USD risk/PnL per your tiers, execute_v2_task for full auto contracts) are exposed as first-class tools.
echo For reliable wallet forensics (bypasses LLM param hallucinations): use automation_examples\wallet_forensics_automation.py or the LangGraph orchestrator.
echo.
echo After studying convo 0389eeb7... (github "new skills to increase agent score" request): added strict guardrails in microagents (tool-restrictions.md + openhands_v2_entry.md):
echo   - Max 1 research MCP call, immediate short user-facing summary only, correct task_list for plan, no raw 50k char blobs, no infinite integrate/list loops on timeout/rate_limit.
echo   - Restart stack after edits so microagent knowledge is reloaded.
echo.
echo (cranky = full OpenHands controller image; sandboxes + mcp use your my-openhands-runtime with preloaded skills)
echo Using local Vulkan llama.cpp backend (Ollama removed, load mitigations applied).
echo.
pause
