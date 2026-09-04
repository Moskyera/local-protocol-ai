@echo off
setlocal enabledelayedexpansion
TITLE Local Protocol AI - Agent Canvas
color 0B

REM ---------------------------------------------------------------------------
REM Starts the whole stack WITHOUT Docker: the coding model, your own tools,
REM and the Agent Canvas interface.
REM
REM This is the newer path. The Docker one is still start-ai.bat, and the two
REM do not collide: Canvas uses 8000, the model 8080, the tools 8765. What they
REM DO share is the model, so run one or the other, not both.
REM ---------------------------------------------------------------------------

set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
for %%I in ("%PROJECT%\..") do set "AI_ROOT=%%~fI"

set "VENV="
if exist "%PROJECT%\.venv\Scripts\python.exe" set "VENV=%PROJECT%\.venv"
if not defined VENV if exist "%AI_ROOT%\ai-env\Scripts\python.exe" set "VENV=%AI_ROOT%\ai-env"
if not defined VENV (
    echo.
    echo [!] No Python virtualenv found. Looked in:
    echo       %PROJECT%\.venv
    echo       %AI_ROOT%\ai-env
    echo.
    echo     python -m venv .venv ^&^& .venv\Scripts\activate ^&^& pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

set CANVAS_PORT=8000
set MODEL_PORT=8080
set MCP_PORT=8765

echo ========================================
echo Local Protocol AI - Agent Canvas
echo ========================================

:: === UPDATE CHECK ===
:: Silent when there is nothing to say; never blocks the boot.
pushd "%PROJECT%"
"%VENV%\Scripts\python.exe" -X utf8 -m local_ai
popd

:: === FIND AGENT CANVAS ===
:: Either installed in its own folder beside the repo, or globally on PATH.
set "CANVAS_CMD="
if exist "%AI_ROOT%\agent-canvas\node_modules\@openhands\agent-canvas\bin\agent-canvas.mjs" (
    set "CANVAS_CMD=node ""%AI_ROOT%\agent-canvas\node_modules\@openhands\agent-canvas\bin\agent-canvas.mjs"""
)
if not defined CANVAS_CMD (
    where agent-canvas >nul 2>&1 && set "CANVAS_CMD=agent-canvas"
)
if not defined CANVAS_CMD (
    echo.
    echo [!] Agent Canvas is not installed. Either:
    echo.
    echo       npm install -g @openhands/agent-canvas
    echo.
    echo     or, without touching your PATH:
    echo.
    echo       mkdir "%AI_ROOT%\agent-canvas"
    echo       cd /d "%AI_ROOT%\agent-canvas"
    echo       npm init -y ^&^& npm install @openhands/agent-canvas
    echo.
    echo     It needs Node.js 22.12 or newer and uv. See the README.
    echo.
    pause
    exit /b 1
)

:: === PORTS ===
echo [CLEANUP] Freeing ports and stopping any old model server...
taskkill /F /IM "llama-server.exe" >nul 2>&1
for %%p in (%CANVAS_PORT% %MODEL_PORT% %MCP_PORT% 18000 18001 3001) do (
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%%p " 2^>nul') do (
        taskkill /F /PID %%i >nul 2>&1
    )
)

:: === THE MODEL ===
:: -Parallel 1, and this matters. llama.cpp divides the context between
:: slots, so -Parallel 2 with -Ctx 32768 gives each request only 16384
:: tokens. An agent front end sends a system prompt plus tool definitions
:: that do not fit in that, and the failure is not obvious: the agent sits
:: on "Thinking" while the server log repeats "context window exceeded,
:: triggering condensation" forever. One user, one slot, whole context.
:: The coder launcher, because it passes --jinja. Without that llama.cpp does
:: not emit tool calls and the agent talks instead of acting.
::
:: No -BindHost here on purpose: its default is 127.0.0.1 and nothing in this
:: path runs in a container, so the model stays unreachable from the network.
echo [1/3] Starting the coding model on :%MODEL_PORT% ...
powershell -ExecutionPolicy Bypass -File "%PROJECT%\start-llama-coder.ps1" -Parallel 1 2>&1 || echo [WARNING] the model starter reported a problem, continuing...

set /a _wait=0
:wait_model
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:%MODEL_PORT%/v1/models' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if %errorlevel% equ 0 goto model_ready
set /a _wait+=1
if %_wait% gtr 120 (
    echo.
    echo [ERROR] The model did not become ready after about 10 minutes.
    echo Check the window the starter opened. The usual causes are a missing
    echo .gguf file or asking for more video memory than the card has.
    echo.
    pause
    exit /b 1
)
timeout /t 5 /nobreak >nul
goto wait_model
:model_ready
echo       ready.

:: === YOUR TOOLS ===
:: Natively, not in a container. Loopback by default.
echo [2/3] Starting the MCP tool server on :%MCP_PORT% ...
start "Local Protocol AI - tools" /min cmd /c ""%VENV%\Scripts\python.exe" -X utf8 -m openhands_mcp.server --transport streamable-http --port %MCP_PORT%"
timeout /t 4 /nobreak >nul

:: === AGENT CANVAS ===
echo [3/3] Starting Agent Canvas on :%CANVAS_PORT% ...
echo.
echo       NOTE: Agent Canvas binds 0.0.0.0 and has no option to change it.
echo       Run scripts\secure-agent-canvas.ps1 once to block it at the firewall.
echo.
cd /d "%AI_ROOT%\agent-canvas" 2>nul
start "Local Protocol AI - Agent Canvas" cmd /k "%CANVAS_CMD%"

set /a _wait=0
:wait_canvas
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:%CANVAS_PORT%/health' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if %errorlevel% equ 0 goto canvas_ready
set /a _wait+=1
if %_wait% gtr 90 (
    echo [WARNING] Canvas is taking a long time. On the very first run it
    echo downloads its Python backend, which can take several minutes.
    echo Watch the window it opened.
    goto canvas_ready
)
timeout /t 5 /nobreak >nul
goto wait_canvas
:canvas_ready

start http://localhost:%CANVAS_PORT%

echo.
echo ========================================
echo RUNNING
echo ========================================
echo   Agent Canvas   http://localhost:%CANVAS_PORT%
echo   Model          127.0.0.1:%MODEL_PORT%   qwen3-coder-30b
echo   Your tools     127.0.0.1:%MCP_PORT%/mcp
echo.
echo   The model and the tools are loopback only. Canvas is not, by its own
echo   design - see the note above.
echo.
echo   Close this window to leave everything running. To stop it all, close
echo   the two windows it opened and run: taskkill /F /IM llama-server.exe
echo.
pause
