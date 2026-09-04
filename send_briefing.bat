@echo off
setlocal enabledelayedexpansion
TITLE SEND FULL AI BRIEFING TO TELEGRAM
color 0A

:: ============================================================
::  Sends the full AI briefing (6 messages) to Telegram.
::
::  NEW: it checks BY ITSELF which model is loaded and, if needed,
::  switches to gemma (market) before sending.
::  Why: llama-server serves whatever is loaded and IGNORES the model
::  name the client asks for. Without this check, if you were in coding
::  mode, the 6 messages would be written by a CODING model with no
::  error at all - just noticeably worse market analysis.
::
::  Arg:  send_briefing.bat noswitch   -> check only, no automatic switch
:: ============================================================

set PROJECT=C:\AI\market-agent
cd /d "%PROJECT%"

echo ========================================
echo    SENDING FULL AI BRIEFING TO TELEGRAM
echo ========================================
echo.

echo [1/4] Activating virtual environment...
call C:\AI\ai-env\Scripts\activate.bat

echo [2/4] Checking that the MARKET model is loaded...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT%\check-briefing-model.ps1"
if %errorlevel% equ 0 goto model_ok

if /i "%~1"=="noswitch" (
    echo.
    echo Wrong model and 'noswitch' was requested. Aborting.
    echo Run start-ai.bat first, then retry.
    pause
    exit /b 1
)

echo.
echo [2b/4] Wrong model loaded - switching to gemma automatically...
echo        (this takes ~15-60 seconds)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT%\start-llama-vulkan.ps1"

echo.
echo [2c/4] Re-checking...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT%\check-briefing-model.ps1"
if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo    ABORTED - could not load the market model
    echo    Nothing was sent. Check llama-server logs:
    echo    C:\AI\llama\llama-server.err
    echo ========================================
    pause
    exit /b 1
)

:model_ok
echo.
echo [3/4] Generating and sending the briefing...
:: sys.exit(1) on partial delivery so the status below is HONEST.
python -c "import sys; from telegram_engine import send_full_ai_briefing; sys.exit(0 if send_full_ai_briefing() else 1)"
set BRIEF_RC=%errorlevel%

echo.
echo [4/4] Result:
if %BRIEF_RC% neq 0 (
    echo ========================================
    echo    BRIEFING INCOMPLETE - not all 6 messages
    echo    were delivered. See the errors above.
    echo ========================================
) else (
    echo ========================================
    echo    BRIEFING SENT SUCCESSFULLY ^(6/6^)
    echo ========================================
)
echo.
echo Note: the MARKET model (gemma) is now loaded.
echo       For coding, run:  start-ai-coder.bat
echo.
pause
exit /b %BRIEF_RC%
