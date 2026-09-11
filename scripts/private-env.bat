@echo off
:: === PRIVATE MODE for everything a launcher starts ===
:: Called by start-ai.bat, start-canvas.bat, start-canvas-sandboxed.bat and
:: start-voice.bat right after PROJECT is known. Sets, in THIS shell, the
:: telemetry kill-switches that Node, uvx and Docker children read (they
:: never run our Python, so the environment is the only thing that reaches
:: them) and makes sure the tool server's bearer token exists.
::
:: LPAI_PRIVATE=1 is the default. The only way out is an explicit 0.
:: The Python side repeats the same switches in lpai_private.py, so a
:: process started by hand gets them too.

if not defined LPAI_PRIVATE set "LPAI_PRIVATE=1"

if /i "%LPAI_PRIVATE%"=="0" (
    echo [private mode] OFF: LPAI_PRIVATE=0 - market data, web research and telemetry switches are yours to manage.
    goto :token
)

set "HF_HUB_OFFLINE=1"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "HF_HUB_DISABLE_IMPLICIT_TOKEN=1"
set "DO_NOT_TRACK=1"
set "VITE_DO_NOT_TRACK=1"
set "GRADIO_ANALYTICS_ENABLED=False"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"
set "LITELLM_LOCAL_MODEL_COST_MAP=True"
set "LITELLM_TELEMETRY=False"
set "ANONYMIZED_TELEMETRY=false"
set "BROWSER_USE_CLOUD_SYNC=false"
set "OH_TELEMETRY_EXPORTER=none"
set "OH_TELEMETRY_CONSENT=denied"
set "OH_TELEMETRY_CONSENT_MODE=override"
set "LOCAL_AI_UPDATE_CHECK=0"
echo [private mode] ON: telemetry off, no process may leave this machine, internet tools withheld.

:token
:: The tool server on :8765 requires a bearer token. It lives next to the
:: Agent Canvas session key. Mint it here so every client in this shell
:: (voice assistant, Canvas config, containers) can read the same one.
set "MCP_TOKEN_FILE=%USERPROFILE%\.openhands\agent-canvas\mcp-token.txt"
if not exist "%USERPROFILE%\.openhands\agent-canvas" mkdir "%USERPROFILE%\.openhands\agent-canvas" >nul 2>&1
if not exist "%MCP_TOKEN_FILE%" (
    powershell -NoProfile -Command "$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [IO.File]::WriteAllText('%MCP_TOKEN_FILE%', ([Convert]::ToBase64String($b) -replace '[+/=]','x'))" >nul 2>&1
)
if exist "%MCP_TOKEN_FILE%" set /p MCP_TOKEN=<"%MCP_TOKEN_FILE%"
exit /b 0
