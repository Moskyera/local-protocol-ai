@echo off
cd /d "%~dp0"

echo ================================================
echo   YourChannel Channel Test - SUCCESS!
echo ================================================
echo.
echo The test already worked. The bot can post to the channel.
echo.
echo Recommended next step:
echo   Put the following in your real config.py:
echo.
echo   TELEGRAM_BOT_TOKEN = "your token"
echo   TELEGRAM_CHANNEL_ID = -1001234567890
echo.
echo Then run your normal briefing command from your project folder.
echo.
echo To re-test the channel:
uv run --with requests python test_channel_post.py
echo.
pause
