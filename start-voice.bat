@echo off
setlocal enabledelayedexpansion
TITLE Local Protocol AI - VOICE
color 0B

:: === THE VOICE ASSISTANT ===
:: Talk to the stack in Greek or English through a headset. Three things must
:: be up, and this script starts only the ones that are not already running,
:: so it is safe to run next to start-ai.bat or start-canvas.bat:
::
::   1. gemma-4 on :8080 with --jinja (native tool calls) and --cpu-moe
::      (experts in RAM, ~3.7 GB VRAM measured 2026-09-11)
::   2. the MCP tool server on :8765, natively (no Docker), 35 tools
::   3. python -m voice_agent   (whisper on CPU, Piper voices, Silero VAD)
::
:: Options, in any order:
::   text     no microphone: type instead of speaking, same safety gate
::   no-mcp   local tools only (time, files, notes, clipboard, terminal)
::   quiet    do not start anything; just connect to what is already running
::   online   LPAI_PRIVATE=0 for this run: the internet tools are offered by
::            voice, each read back in full and needing the spoken phrase

set "PROJECT=%~dp0"
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"
for %%I in ("%PROJECT%\..") do set "AI_ROOT=%%~fI"

:: Private mode (the default): telemetry switches, tool-server token. See docs/PRIVACY.md
call "%PROJECT%\scripts\private-env.bat"

set "VENV="
if exist "%PROJECT%\.venv\Scripts\python.exe" set "VENV=%PROJECT%\.venv"
if not defined VENV if exist "%AI_ROOT%\ai-env\Scripts\python.exe" set "VENV=%AI_ROOT%\ai-env"
if not defined VENV (
    echo.
    echo [!] No Python virtualenv found. Looked in:
    echo       %PROJECT%\.venv
    echo       %AI_ROOT%\ai-env
    echo     See README.md, section "Voice assistant".
    pause
    exit /b 1
)
set "PY=%VENV%\Scripts\python.exe"

set "MODE_ARGS="
set "WANT_MCP=1"
set "QUIET=0"
for %%A in (%*) do (
    if /i "%%~A"=="text"   set "MODE_ARGS=!MODE_ARGS! --text"
    if /i "%%~A"=="no-mcp" (set "MODE_ARGS=!MODE_ARGS! --no-mcp" & set "WANT_MCP=0")
    if /i "%%~A"=="quiet"  set "QUIET=1"
    if /i "%%~A"=="online" set "LPAI_PRIVATE=0"
)
if /i "%LPAI_PRIVATE%"=="0" echo [!] online: the internet tools are ON for this run.

echo ========================================
echo   Local Protocol AI - voice assistant
echo ========================================
echo.

:: === 1. THE MODEL (8080) ===
:: A server that is already answering is reused as it is. If it was started
:: without --jinja the model will talk but cannot act; the agent says so.
"%PY%" -X utf8 -c "import urllib.request,sys;urllib.request.urlopen('http://127.0.0.1:8080/v1/models',timeout=2);sys.exit(0)" >nul 2>&1
if not errorlevel 1 (
    echo [1/3] Model already running on :8080 - reusing it.
) else if "%QUIET%"=="1" (
    echo [1/3] Model is NOT running on :8080 and "quiet" was given - the agent will report it.
) else (
    echo [1/3] Starting gemma-4 with --jinja --cpu-moe ^(tool calls on, experts in RAM^)...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT%\start-llama-vulkan.ps1" -Jinja -CpuMoe
    if errorlevel 1 (
        echo [!] The model did not start. Read the message above.
        pause
        exit /b 1
    )
)

:: === 2. THE TOOLS (8765) ===
:: Same server start-ai.bat runs in Docker, here as a plain process so the
:: voice assistant needs no container. Its window stays open; close it last.
if "%WANT_MCP%"=="0" (
    echo [2/3] MCP tools skipped ^(no-mcp^).
) else (
    "%PY%" -X utf8 -c "import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(0 if s.connect_ex(('127.0.0.1',8765))==0 else 1)" >nul 2>&1
    if not errorlevel 1 (
        echo [2/3] MCP tool server already running on :8765 - reusing it.
    ) else if "%QUIET%"=="1" (
        echo [2/3] MCP tool server is NOT running - continuing with local tools only.
    ) else (
        echo [2/3] Starting the MCP tool server on :8765...
        start "MCP tools (8765)" /min cmd /k ""%PY%" -X utf8 -m openhands_mcp.server --transport streamable-http --port 8765"
        REM it needs a few seconds to import everything; the agent retries once anyway
        timeout /t 6 /nobreak >nul
    )
)

:: === 3. THE VOICE AGENT ===
echo [3/3] Starting the voice agent%MODE_ARGS%...
echo.
echo     Say "telos" / "exit" to stop.  Ctrl+C also works.
echo     Anything destructive is read back to you and waits for
echo     "nai, synechise" / "yes, go ahead"  -  or  "ochi, akyrose to" / "no, cancel it".
echo.
pushd "%PROJECT%"
"%PY%" -X utf8 -m voice_agent%MODE_ARGS%
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" (
    echo.
    echo [!] The voice agent exited with code %RC%. Missing pieces are named above;
    echo     the usual ones are the Piper voices and the microphone. See README.md.
    pause
)
endlocal
