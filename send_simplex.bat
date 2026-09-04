@echo off
title SEND AI BRIEFING TO SIMPLEX CHANNEL
color 0A

echo ========================================
echo   SENDING BRIEFING TO SIMPLEX CHANNEL
echo ========================================
echo.

call C:\AI\ai-env\Scripts\activate.bat

python send_simplex_briefing.py

echo.
echo ========================================
pause