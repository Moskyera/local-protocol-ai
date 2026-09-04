@echo off
setlocal

:: =============================================================================
:: MOSKY Voice Launcher .bat (simple, careful, robust)
::
:: This is the easy way to start the voice interface for your MOSKY system.
::
:: It runs the recommended launcher (launch_mosky.py) using your ai-env Python.
:: The launcher will:
::   - Verify you are using the correct Python (ai-env)
::   - Check/install voice packages (faster-whisper, piper-tts, etc.)
::   - Download Greek Piper voice model if missing
::   - Check Ollama is up (start-ai.bat should be running)
::   - Prefer the advanced Pipecat real-time voice (if `pip install pipecat-ai` done)
::     - Integrates with full system: research (with pros/cons, evolution patterns),
::       LangGraph supervisor, guarded actions, etc.
::   - Fall back to original voice if Pipecat not present.
::   - Speak "Έτοιμος, πες γεια σου mosky." and start listening.
::
:: HOW TO RUN:
::   - Double-click this .bat (or run from cmd)
::   - Best: Have start-ai.bat / the main system running first in another window.
::   - Speak after the ready message. Use wake word like "γεια σου mosky".
::
:: FIRST TIME SETUP (in a cmd as admin or in ai-env):
::   C:\AI\ai-env\Scripts\python.exe -m pip install faster-whisper piper-tts sounddevice webrtcvad numpy pipecat-ai
::
:: Greek voice model is auto-downloaded by the launcher if missing.
::
:: TROUBLESHOOTING:
::   - Wrong Python: the launcher will tell you the exact command to use.
::   - Missing packages: see the pip command above.
::   - No audio: check mic/speakers, run as the user who has audio devices.
::   - Pipecat for better voice: the pip install above includes it.
::
:: This .bat is minimal and safe. All real logic is in launch_mosky.py (which prefers the new Pipecat voice).
:: =============================================================================

echo.
echo [MOSKY] Starting voice launcher...
echo.

set "AI_ENV=C:\AI\ai-env"
set "PYTHON_EXE=%AI_ENV%\Scripts\python.exe"
set "PROJECT_DIR=%~dp0"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] ai-env Python not found at %PYTHON_EXE%
    echo Edit this .bat if your ai-env is in a different location.
    pause
    exit /b 1
)

cd /d "%PROJECT_DIR%"

echo [INFO] Using: %PYTHON_EXE%
echo [INFO] Project: %PROJECT_DIR%
echo.

"%PYTHON_EXE%" launch_mosky.py

echo.
echo [INFO] Voice session ended.
pause
exit /b 0