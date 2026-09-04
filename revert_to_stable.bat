@echo off
setlocal enabledelayedexpansion

TITLE REVERT TO STABLE WORKING STATE
color 0E

echo ========================================
echo   ΕΠΑΝΑΦΟΡΑ ΣΕ STABLE ΚΑΤΑΣΤΑΣΗ
echo ========================================
echo.
echo Αυτο το script θα γυρισει το project στην ΤΕΛΕΥΤΑΙΑ ΑΨΟΓΑ λειτουργουσα κατασταση
echo (stable-2026-06-12) που επιβεβαιωθηκε οτι δουλευει τελεια.
echo.
echo ΠΡΟΣΟΧΗ:
echo - Θα γινει git checkout stable-2026-06-12
echo - Οποια αλλαγη εχεις κανει απο τοτε θα χαθει (εκτος αν ειναι σε branch)
echo - Μετα την επαναφορα θα πρεπει να τρεξεις παλι start-ai.bat
echo.
pause

echo.
echo [1/3] Ελεγχος οτι βρισκομαστε στον σωστο φακελο...
if not exist ".git" (
    echo ΣΦΑΛΜΑ: Δεν βρεθηκε .git φακελος!
    echo Πρεπει να τρεξεις αυτο το bat απο μεσα στον φακελο C:\AI\market-agent
    pause
    exit /b 1
)
echo OK.

echo.
echo [2/3] Επαναφορα στην stable κατασταση...
git checkout stable-2026-06-12
if %errorlevel% neq 0 (
    echo.
    echo ΣΦΑΛΜΑ: Το git checkout απετυχε!
    echo Βεβαιωσου οτι το git ειναι εγκατεστημενο και το repo ειναι σωστο.
    pause
    exit /b 1
)
echo.
echo ✅ Επαναφορα ολοκληρωθηκε επιτυχως!
echo    Τωρα βρισκεσαι στην stable-2026-06-12 κατασταση.

echo.
echo [3/3] Προτεινομενα επομενα βηματα:
echo   1. Κλεισε ολα τα παλια παραθυρα (llama, Docker, Streamlit)
echo   2. Τρεξε: start-ai.bat
echo   3. Μετα την εκκινηση, τρεξε για επιβεβαιωση:
echo      python verify_system.py
echo.
echo Αν θελεις να δεις την ιστορια:
echo      git log --oneline -10
echo.

echo.
echo ========================================
echo   ΕΠΑΝΑΦΟΡΑ ΟΛΟΚΛΗΡΩΘΗΚΕ
echo ========================================
echo.
echo Πατα οποιοδηποτε πλήκτρο για να κλεισει το παραθυρο...
pause >nul

exit /b 0
