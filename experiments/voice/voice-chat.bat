@echo off
echo.
echo ============================================================
echo  DEPRECATED: voice-chat.bat
echo ============================================================
echo  The old .bat had too many Windows parsing / encoding problems.
echo.
echo  NEW RECOMMENDED WAY:
echo    C:\AI\ai-env\Scripts\python.exe launch_mosky.py
echo.
echo  (Create a desktop shortcut with that exact command for one-click.)
echo.
echo  Make sure start-ai.bat is already running and ONLINE first.
echo.
pause
exit /b 0

REM (The rest of this file is legacy and ignored.)
REM Use launch_mosky.py instead.

cd /d "%~dp0"
set "AI_ROOT=%CD%"

echo.
echo ===============================================
echo   MOSKY Voice Interface (Greek)
echo ===============================================
echo Πες "γεια σου mosky" για να ξυπνήσεις.
echo Παράδειγμα: "τι νέο έχουμε σήμερα από github και x, ανάλυσε μου και πες μου αν μας ταιριάζει κάτι νέο σαν skill"
echo.
echo Αυτό το παράθυρο πρέπει να τρέχει ΜΕΤΑ το start-ai.bat.
echo Μην το βάζεις στο launcher να ανοίγει μόνο του.
echo.
echo Το bat φροντίζει μόνο του τα προαπαιτούμενα:
echo   - σωστό python (προτιμά C:\AI\ai-env)
echo   - bootstrap pip + voice packages
echo   - κατέβασμα σωστού Greek Piper (el_GR-rapunzelina-low)
echo.

REM ---------- Smart Python detection ----------
REM Προτιμάμε το ΠΛΗΡΕΣ / πλούσιο ai-env (C:\AI\ai-env), όχι το μικρό τοπικό μέσα στο market-agent.
REM Το τοπικό ai-env συχνά είναι ελλιπές (χωρίς pip).
set "PYTHON="

REM 1. Full rich envs first
if not defined PYTHON if exist "C:\AI\ai-env\Scripts\python.exe" (
    set "PYTHON=C:\AI\ai-env\Scripts\python.exe"
    echo [venv] Βρέθηκε C:\AI\ai-env (προτιμώμενο πλήρες περιβάλλον)
)

if not defined PYTHON if exist "..\ai-env\Scripts\python.exe" (
    set "PYTHON=%AI_ROOT%\..\ai-env\Scripts\python.exe"
    echo [venv] Βρέθηκε ..\ai-env (C:\AI\ai-env)
)

REM 2. Τοπικό ai-env μέσα στο market-agent (συχνά μικρό/ελλιπές - μόνο αν δεν βρέθηκε άλλο)
if not defined PYTHON if exist "ai-env\Scripts\python.exe" (
    set "PYTHON=%AI_ROOT%\ai-env\Scripts\python.exe"
    echo [venv] Βρέθηκε ai-env ΜΕΣΑ στο market-agent (προσοχή: μπορεί να είναι ελλιπές)
)

REM 3. Standard venv names
if not defined PYTHON if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%AI_ROOT%\.venv\Scripts\python.exe"
    echo [venv] Βρέθηκε .venv
)

if not defined PYTHON if exist "venv\Scripts\python.exe" (
    set "PYTHON=%AI_ROOT%\venv\Scripts\python.exe"
    echo [venv] Βρέθηκε venv
)

if not defined PYTHON (
    echo [WARN] Δεν βρέθηκε γνωστό venv. Θα προσπαθήσω με το 'python' από το PATH.
    echo          Αν αποτύχει, πρέπει να βάλεις τα πακέτα φωνής στο σωστό Python (συνήθως C:\AI\ai-env).
    set "PYTHON=python"
)

REM ---------- Validate that the chosen python has pip (the local tiny ai-env often doesn't) ----------
echo.
echo Έλεγχος ότι το επιλεγμένο Python έχει pip...
"%PYTHON%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [WARN] Το επιλεγμένο Python (%PYTHON%) δεν έχει pip!
    echo        Πιθανότατα είναι το μικρό/ελλιπές ai-env μέσα στο market-agent.
    echo        Θα προσπαθήσω να πέσω στο C:\AI\ai-env αν υπάρχει...
    if exist "C:\AI\ai-env\Scripts\python.exe" (
        set "PYTHON=C:\AI\ai-env\Scripts\python.exe"
        echo [FALLBACK] Τώρα χρησιμοποιώ: %PYTHON%
        "%PYTHON%" -m pip --version >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Ούτε το C:\AI\ai-env έχει pip. Πρέπει να φτιάξεις το περιβάλλον.
        )
    ) else (
        echo [ERROR] Δεν βρέθηκε εναλλακτικό πλήρες ai-env.
    )
) else (
    echo [OK] pip είναι διαθέσιμο στο επιλεγμένο Python.
)

echo.
echo Using Python:
echo   %PYTHON%
"%PYTHON%" --version 2>&1
echo.

REM ---------- Ensure pip exists in the venv (some ai-envs are created without it) ----------
echo [pre] Bootstrap pip if missing...
"%PYTHON%" -m ensurepip --upgrade --quiet 2>nul

REM ---------- Install / upgrade the voice packages in the chosen env ----------
echo [1/3] Εγκατάσταση / έλεγχος voice πακέτων (faster-whisper, piper-tts, sounddevice, webrtcvad, numpy)
echo       Αυτό μπορεί να πάρει αρκετά λεπτά την πρώτη φορά (κατεβάζει μοντέλα).
"%PYTHON%" -m pip install --upgrade pip --quiet
"%PYTHON%" -m pip install faster-whisper piper-tts sounddevice webrtcvad numpy --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo [WARNING] Το pip install των voice πακέτων έβγαλε error.
    echo           Δοκίμασε να τρέξεις χειροκίνητα σε cmd ως Administrator:
    echo             "%PYTHON%" -m pip install faster-whisper piper-tts sounddevice webrtcvad numpy
    echo           Ή άνοιξε το ai-env με activate και βάλε τα εκεί.
    echo.
    pause
)

REM ---------- Download Greek Piper voice model if missing (critical for TTS) ----------
echo [1.5/3] Έλεγχος / κατέβασμα Greek Piper voice model (αν λείπει)...
if not exist "%USERPROFILE%\.piper\voices\el_GR-rapunzelina-low.onnx" (
    echo Downloading Greek Piper voice (el_GR-rapunzelina-low) using helper...
    "%PYTHON%" "%AI_ROOT%\download_piper_greek.py"
) else (
    echo Greek Piper voice model already present.
)
if not exist "%USERPROFILE%\.piper\voices\el_GR-rapunzelina-low.onnx" (
    echo.
    echo [CRITICAL] Greek Piper voice model STILL MISSING after download attempt.
    echo            The voice interface will not be able to speak or start properly.
    echo            Check your internet, or manually download el_GR-rapunzelina-low.onnx + .json
    echo            from https://huggingface.co/rhasspy/piper-voices/tree/main/el/el_GR/rapunzelina/low
    echo            and place them in %USERPROFILE%\.piper\voices\
    echo.
    pause
)

REM ---------- Quick sanity import test ----------
echo.
echo [2/3] Γρήγορος έλεγχος voice πακέτων + MOSKY module...
"%PYTHON%" -c "import sys; sys.path.insert(0,r'%AI_ROOT%'); import faster_whisper,piper,sounddevice,numpy,automation_examples.voice_interface; print('Voice packages + MOSKY module: OK')" 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Voice packages or MOSKY module failed to load in this Python.
    echo         Most common: wrong python.exe (not the ai-env).
    echo         Fix: double-click voice-chat.bat from inside the market-agent folder,
    echo                or manually edit the PYTHON line in this .bat to point to the correct ai-env\Scripts\python.exe
    echo.
    pause
    goto :eof
)

REM ---------- Optional: check Ollama (simple, single line) ----------
echo.
echo [3/3] Έλεγχος ότι το Ollama τρέχει (χρειάζεται για το MOSKY)...
"%PYTHON%" -c "import urllib.request,sys; print('Ollama check (non-fatal)')" 2>&1 || echo Ollama not responding or check skipped (run start-ai.bat first)

echo.
echo ===============================================
echo   Εκκίνηση MOSKY Voice Interface...
echo   (Θα ακούσεις αμέσως φωνητικό μήνυμα "Έτοιμος")
echo ===============================================
echo.

REM Force UTF-8 output from the Python process (Greek text in console + TTS)
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

"%PYTHON%" -m automation_examples.voice_interface
set "EXITCODE=%errorlevel%"

echo.
if %EXITCODE% neq 0 (
    echo [MOSKY] Το πρόγραμμα τερματίστηκε με κωδικό %EXITCODE%.
    echo.
    echo ΣΥΝΗΘΙΣΜΕΝΑ ΠΡΟΒΛΗΜΑΤΑ ^& ΛΥΣΕΙΣ:
    echo   1. Δεν έτρεξες πρώτα το start-ai.bat (Ollama δεν απαντάει).
    echo   2. Τρέχεις το voice-chat.bat από λάθος φάκελο (πρέπει να είναι μέσα στο market-agent).
    echo   3. Δεν έχεις κατεβάσει το Greek Piper voice model (δες automation_examples\voice_interface.py).
    echo   4. Το Piper model path δεν ταιριάζει με το αρχείο που κατέβασες.
    echo   5. Δεν είναι εγκατεστημένα τα voice πακέτα στο σωστό venv (ai-env).
    echo   6. Δεν έχεις μικρόφωνο / speakers.
    echo.
    echo Για debug τρέξε χειροκίνητα σε cmd (από μέσα στον market-agent):
    echo   C:\AI\ai-env\Scripts\python.exe -m pip list ^| findstr /i "whisper piper"
    echo   C:\AI\ai-env\Scripts\python.exe -c "from automation_examples.voice_interface import main; print('imports OK')"
    echo.
)

pause