@echo off
setlocal

:: =============================================================================
:: MOSKY Web J.A.R.V.I.S. Launcher (.bat)
::
:: The easy double-click way to run:
::   C:\AI\ai-env\Scripts\python.exe mosky_web.py
::
:: What you get:
:: - Futuristic dark HUD with neon cyan (#00f0ff) glows
:: - Animated scanline + pulsing status bar
:: - Real-time JS canvas waveform visualizer (sine waves + live pulse when "speaking")
:: - Auto greeting voice on page open: "Έτοιμος. Πες γεια σου mosky..." (if Greek Piper ready)
:: - Voice input via browser mic (no pyaudio needed)
:: - Greek Piper TTS replies autoplay in the UI
:: - Direct access to advanced research (pros/cons + evolution patterns from GitHub/X)
:: - System evaluation / score reports
:: - Full LangGraph supervisor + guarded flow under the hood
::
:: HOW TO USE:
:: 1. Make sure your main system is up (start-ai.bat - primary LLM :8080 preferred, legacy Ollama 11434 for voice)
:: 2. Double-click this .bat  (or run from cmd / PowerShell)
:: 3. Browser opens at http://127.0.0.1:7860
:: 4. Immediately hear the ready greeting + see the live waveform animating.
:: 5. Use the mic tab or text tab. Try:
::      "τι νέο έχουμε από github και x; ανάλυσε pros/cons"
::      "τρέξε αξιολόγηση συστήματος"
::      normal conversation
::
:: FIRST TIME / TROUBLESHOOTING:
:: - The ai-env python must have: gradio, soundfile, numpy, piper-tts, faster-whisper (already present in your ai-env)
:: - Greek Piper voice (el_GR-rapunzelina-low.onnx + .json) must be in ~/.piper/voices/
::   If missing: run  C:\AI\ai-env\Scripts\python.exe download_piper_greek.py
::   or use the voice_mosky.bat once (it ensures it).
:: - If no TTS: the web UI still works fully in text + research; you will see a warning in console.
:: - Wrong Python: this .bat hard-checks for ai-env\Scripts\python.exe
:: - Port 7860 in use: close previous or edit the .py launch line.
::
:: This .bat is intentionally small and safe. All real code + effects are in mosky_web.py
:: (which you can also run directly with the exact python path you asked for).
:: =============================================================================

echo.
echo [J.A.R.V.I.S. Web] Starting MOSKY futuristic interface...
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
echo [INFO] Launching with full Jarvis effects (HUD + waveform + auto-greet + pros/cons research)...
echo [INFO] The script will automatically use port 7860 or the next free port if busy.
echo.

"%PYTHON_EXE%" mosky_web.py

echo.
echo [INFO] Web session ended (close the browser tab to stop the server).
pause
exit /b 0
