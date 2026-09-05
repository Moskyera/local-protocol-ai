@echo off
setlocal enabledelayedexpansion
TITLE Local Protocol AI - Agent Canvas (sandboxed)
color 0E

REM ---------------------------------------------------------------------------
REM The sandboxed path. The agent-server - the part that runs shell commands
REM and edits files - runs INSIDE WSL as a separate, unprivileged Linux user
REM who cannot see your Windows drive. The model and your tools stay on Windows
REM and are reached over the WSL network adapter only. The browser UI is the
REM same http://localhost:8000 as always.
REM
REM ONE-TIME SETUP FIRST (creates the user, hides C: from it, installs the
REM agent's own Node/uv/Canvas):
REM     wsl -d Ubuntu
REM     sudo bash /mnt/c/AI/market-agent/scripts/sandbox-canvas-setup.sh
REM     exit
REM     wsl --shutdown
REM See docs/SANDBOX.md for exactly what that does and does not protect.
REM ---------------------------------------------------------------------------

set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
for %%I in ("%PROJECT%\..") do set "AI_ROOT=%%~fI"
set AGENT_USER=lpai-agent
set DISTRO=Ubuntu
set MODEL_PORT=8080
set MCP_PORT=8765
set CANVAS_PORT=8000

set "VENV="
if exist "%PROJECT%\.venv\Scripts\python.exe" set "VENV=%PROJECT%\.venv"
if not defined VENV if exist "%AI_ROOT%\ai-env\Scripts\python.exe" set "VENV=%AI_ROOT%\ai-env"
if not defined VENV ( echo [!] No virtualenv. See the README. & pause & exit /b 1 )

echo ========================================
echo Local Protocol AI - Agent Canvas (sandboxed)
echo ========================================

pushd "%PROJECT%"
"%VENV%\Scripts\python.exe" -X utf8 -m local_ai
popd

:: === Is the sandbox actually there? ===
:: The setup script must have run, and `wsl --shutdown` after it, or the
:: agent user still sees C:. We check both and refuse rather than pretend.
wsl -d %DISTRO% -e id %AGENT_USER% >nul 2>&1
if errorlevel 1 (
    echo.
    echo [!] The sandbox user "%AGENT_USER%" does not exist in WSL yet.
    echo     Run the one-time setup, then wsl --shutdown:
    echo         wsl -d %DISTRO%
    echo         sudo bash /mnt/c/AI/market-agent/scripts/sandbox-canvas-setup.sh
    echo         exit
    echo         wsl --shutdown
    echo.
    pause
    exit /b 1
)
wsl -d %DISTRO% -u %AGENT_USER% -e sh -c "ls /mnt/c >/dev/null 2>&1" && (
    echo.
    echo [!] "%AGENT_USER%" can still read C:. The sandbox is NOT active.
    echo     You ran the setup but not the shutdown that applies it:
    echo         wsl --shutdown
    echo     Then start this again. Refusing to run un-sandboxed - use
    echo     start-canvas.bat if you actually want the un-sandboxed path.
    echo.
    pause
    exit /b 1
)
echo [ok] sandbox user %AGENT_USER% cannot see C:.

:: === The WSL network adapter address ===
:: NAT-mode WSL gets a fresh subnet on some reboots, so the address the model
:: binds to and the URL the agent uses are discovered every start, never
:: hardcoded. The Windows-side vEthernet(WSL) IPv4 is the address WSL sees as
:: its gateway - the two are the same in NAT mode.
for /f "usebackq tokens=*" %%A in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.InterfaceAlias -match 'WSL' } ^| Select-Object -First 1).IPAddress"`) do set "HOSTIP=%%A"
if not defined HOSTIP (
    echo [!] Could not find the WSL network adapter address. Is WSL running?
    pause
    exit /b 1
)
echo [ok] WSL adapter: %HOSTIP%  (model and tools bind here, not 0.0.0.0)

:: === Free the ports ===
taskkill /F /IM "llama-server.exe" >nul 2>&1
for %%p in (%MODEL_PORT% %MCP_PORT%) do (
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%%p " 2^>nul') do taskkill /F /PID %%i >nul 2>&1
)
wsl -d %DISTRO% -u %AGENT_USER% -e pkill -f "agent-canvas.mjs|openhands-agent-server|openhands.automation" >nul 2>&1

:: === The model, bound to the WSL adapter only ===
:: Coder launcher for --jinja (tool calls) and --cpu-moe (low VRAM). The bind
:: is the WSL adapter, so the network exposure is the WSL virtual switch, not
:: your LAN. Not 0.0.0.0.
echo [1/3] Starting the coding model on %HOSTIP%:%MODEL_PORT% ...
powershell -ExecutionPolicy Bypass -File "%PROJECT%\start-llama-coder.ps1" -Parallel 1 -BindHost %HOSTIP% 2>&1 || echo [WARNING] model starter reported a problem, continuing...
set /a _w=0
:wm
powershell -NoProfile -Command "try{ if((Invoke-WebRequest -Uri 'http://%HOSTIP%:%MODEL_PORT%/health' -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200){exit 0} }catch{}; exit 1" >nul 2>&1
if not errorlevel 1 goto wm_ok
set /a _w+=1
if %_w% gtr 120 ( echo [ERROR] model not ready after ~10 min. & pause & exit /b 1 )
timeout /t 5 /nobreak >nul
goto wm
:wm_ok
echo       ready.

:: === Your tools, bound to the WSL adapter only ===
echo [2/3] Starting the MCP tool server on %HOSTIP%:%MCP_PORT% ...
start "Local Protocol AI - tools" /min cmd /c ""%VENV%\Scripts\python.exe" -X utf8 -m openhands_mcp.server --transport streamable-http --host %HOSTIP% --port %MCP_PORT%"
timeout /t 4 /nobreak >nul

:: === Agent Canvas, inside WSL, as the sandboxed user ===
:: The agent-server it spawns inherits that user: no C: drive, its own home.
:: We hand it the model and tool URLs on the adapter address and the same
:: session key the Windows install persisted, so the two stores agree.
echo [3/3] Starting Agent Canvas in WSL as %AGENT_USER% ...
set "KEYFILE=%USERPROFILE%\.openhands\agent-canvas\api-key.txt"
set "KEY="
if exist "%KEYFILE%" set /p KEY=<"%KEYFILE%"
wsl -d %DISTRO% -u %AGENT_USER% -e bash -lc "export PATH=$HOME/.local/bin:$HOME/.local/node/bin:$PATH; export LOCAL_BACKEND_API_KEY='%KEY%'; export LPAI_HOST='%HOSTIP%'; cd ~/lpai-canvas && setsid nohup node node_modules/@openhands/agent-canvas/bin/agent-canvas.mjs >~/lpai-canvas/canvas.log 2>&1 </dev/null & sleep 2; echo started"

set /a _w=0
:wc
powershell -NoProfile -Command "try{ if((Invoke-WebRequest -Uri 'http://localhost:%CANVAS_PORT%/health' -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200){exit 0} }catch{}; exit 1" >nul 2>&1
if not errorlevel 1 goto wc_ok
set /a _w+=1
if %_w% gtr 90 ( echo [WARNING] Canvas slow on first run - it downloads its Python backend. & goto wc_ok )
timeout /t 5 /nobreak >nul
goto wc
:wc_ok

start http://localhost:%CANVAS_PORT%
echo.
echo ========================================
echo RUNNING (sandboxed)
echo ========================================
echo   Agent Canvas   http://localhost:%CANVAS_PORT%   (open with localhost, not 127.0.0.1)
echo   Agent runs as  %AGENT_USER% in WSL - no access to your C: drive
echo   Model          %HOSTIP%:%MODEL_PORT%   qwen3-coder-30b
echo   Your tools     %HOSTIP%:%MCP_PORT%/mcp
echo.
echo   In Settings, point the model at  http://%HOSTIP%:8080/v1  (key: sk-dummy-local)
echo   and add an MCP server at         http://%HOSTIP%:8765/mcp  (streamable-http).
echo   The launcher cannot pre-fill these: the sandboxed backend keeps its own
echo   settings store, separate from the Windows one, which is the point.
echo.
echo   To stop: close this window, then
echo     taskkill /F /IM llama-server.exe
echo     wsl -d %DISTRO% -u %AGENT_USER% -e pkill -f agent-canvas
echo.
pause
