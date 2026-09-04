"""
Standalone test script for posting to the YourChannel Telegram channel.

Run with:
    uv run --with requests python test_channel_post.py

This bypasses the broken system "python" command.
"""

import os
import requests

# ============================================
# STEP 1: HARDCODE TOKEN HERE FOR QUICK TEST
# ============================================
# If the script says "No TELEGRAM_BOT_TOKEN", do this:
# 1. Replace the line below with your real token from @BotFather
# 2. Run the test
# 3. After it works, you can remove the hardcoded token
#
TOKEN = None   # <--- PUT YOUR TOKEN HERE, e.g. TOKEN = "123456:ABCDEFghIJK..."
#
# Example (remove the # and put real value):
# TOKEN = "1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# ============================================

CHANNEL = os.getenv("TELEGRAM_CHANNEL_ID", "")   # no default: this
# script posts a REAL message, so it must never guess a destination.
OLD_CHAT = None

# Try .env file in the same directory (simple, no extra packages needed)
def _try_load_env():
    global TOKEN, CHANNEL, OLD_CHAT
    env_path = os.path.join(os.path.dirname(__file__ or "."), ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = [x.strip() for x in line.split("=", 1)]
                        v = v.strip().strip("\"' ")
                        ku = k.upper()
                        if ku == "TELEGRAM_BOT_TOKEN" and not TOKEN:
                            TOKEN = v
                        elif ku == "TELEGRAM_CHANNEL_ID":
                            CHANNEL = v
                        elif ku == "TELEGRAM_CHAT_ID" and not OLD_CHAT:
                            OLD_CHAT = v
        except Exception as ex:
            print("Warning reading .env:", ex)

_try_load_env()

# Try to import from config (your normal project config)
if not TOKEN:
    try:
        from config import config
        TOKEN = getattr(config, "TELEGRAM_BOT_TOKEN", None) or os.environ.get("TELEGRAM_BOT_TOKEN")
        ch = getattr(config, "TELEGRAM_CHANNEL_ID", None) or os.environ.get("TELEGRAM_CHANNEL_ID")
        if ch:
            CHANNEL = ch
        OLD_CHAT = getattr(config, "TELEGRAM_CHAT_ID", None) or os.environ.get("TELEGRAM_CHAT_ID")
    except Exception as e:
        print(f"Could not import from config: {e}")
        if not TOKEN:
            TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def send_message(chat_id: str, text: str):
    if not TOKEN:
        print("ERROR: No TELEGRAM_BOT_TOKEN.")
        print("Quick fix: Open this file in Notepad and set TOKEN = \"yourtoken\" near the top.")
        print("Or create a .env file next to this .py with:")
        print("  TELEGRAM_BOT_TOKEN=123456:ABC...")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=payload, timeout=20)
        print(f"HTTP {r.status_code}")
        print(r.text)
        try:
            return r.json().get("ok", False)
        except:
            return r.status_code == 200
    except Exception as e:
        print("Request error:", e)
        return False

def get_chat_info(chat_id: str):
    if not TOKEN:
        print("No token, skipping getChat")
        return None
    url = f"https://api.telegram.org/bot{TOKEN}/getChat"
    try:
        r = requests.post(url, data={"chat_id": chat_id}, timeout=15)
        print("\ngetChat response:")
        print(r.text)
        if r.status_code == 200:
            j = r.json()
            if j.get("ok"):
                return j["result"].get("id")
    except Exception as e:
        print("getChat error:", e)
    return None

if __name__ == "__main__":
    print("=== YourChannel Channel Test ===")
    print(f"Target channel: {CHANNEL}")
    if OLD_CHAT:
        print(f"(Old private chat was: {OLD_CHAT})")
    print()

    test_msg = (
        "<b>✅ Channel Test</b>\n\n"
        "This message was sent directly to the <b>CHANNEL</b>.\n"
        "If you see it at https://t.me/YourChannel , posting works!\n\n"
        "Bot: @YourBot"
    )

    print("--- Sending to CHANNEL ---")
    ok = send_message(CHANNEL, test_msg)
    print(f"\nSend to channel success: {ok}")

    if ok:
        print("\nSUCCESS! Check the actual Telegram channel now.")
    else:
        print("\nPosting failed. Common reasons:")
        print("  - Wrong / expired bot token")
        print("  - Bot is not admin or missing 'Post Messages' permission")
        print("  - Channel username wrong (must be exactly @YourChannel)")

    print("\n--- Trying to discover numeric channel ID ---")
    num_id = get_chat_info(CHANNEL)
    if num_id:
        print(f"\nYou can use this numeric ID in config if you want:")
        print(f"TELEGRAM_CHANNEL_ID = {num_id}")

    print("\nDone.")
