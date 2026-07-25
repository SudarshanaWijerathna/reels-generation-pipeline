"""
telegram_bot_listener.py
========================
Interactive Telegram Bot Remote Controller.
Listens for commands from your phone via Telegram Bot API:
  - /status   -> Checks video_store buffer count
  - /generate -> Triggers an on-demand Reel generation
  - /postnow  -> Forces an immediate Facebook Reel post
  - /help     -> Lists commands
"""

import os
import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram_notifier import get_telegram_creds, send_telegram_message
from video_store import get_stored_reels_count, MAX_STORE_CAPACITY

def run_listener():
    token, allowed_chat_id = get_telegram_creds()
    if not token or not allowed_chat_id:
        print("❌ Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env to run bot listener.")
        sys.exit(1)

    print("\n=======================================================")
    print("TELEGRAM INTERACTIVE BOT REMOTE CONTROLLER LISTENER")
    print("=======================================================")
    print(f"Bot Listener Active! Waiting for commands from Telegram Chat ID: {allowed_chat_id}")
    print("Commands supported: /status, /generate, /postnow, /help\n")

    last_offset = 0
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    while True:
        try:
            params = {"offset": last_offset, "timeout": 20}
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                updates = r.json().get("result", [])
                for update in updates:
                    last_offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_id = str(msg.get("chat", {}).get("id", ""))

                    # Security check: only respond to your personal chat ID
                    if chat_id != str(allowed_chat_id):
                        print(f"[Telegram Bot] Ignored message from unauthorized chat_id: {chat_id}")
                        continue

                    print(f"[Telegram Bot Command Received]: {text}")

                    if text.startswith("/status"):
                        count = get_stored_reels_count()
                        resp = f"📊 <b>Video Store Buffer Status:</b>\n\n• <b>Stored Reels:</b> {count}/{MAX_STORE_CAPACITY}\n• <b>Pipeline:</b> Healthy & Ready"
                        send_telegram_message(resp)

                    elif text.startswith("/generate"):
                        send_telegram_message("🎬 <b>Producer Triggered!</b> Generating a new Reel video now...")
                        from producer_workflow import run_producer
                        try:
                            run_producer()
                        except SystemExit:
                            pass
                        except Exception as e:
                            send_telegram_message(f"❌ <b>Producer Failed:</b> {e}")

                    elif text.startswith("/postnow"):
                        send_telegram_message("🚀 <b>Publisher Triggered!</b> Posting oldest reel to Facebook now...")
                        from publisher_workflow import run_publisher
                        try:
                            run_publisher()
                        except SystemExit:
                            pass
                        except Exception as e:
                            send_telegram_message(f"❌ <b>Publisher Failed:</b> {e}")

                    elif text.startswith("/help") or text.startswith("/start"):
                        help_text = (
                            "🎛️ <b>Whisprs Bot Commands:</b>\n\n"
                            "• <code>/status</code> — Check current store buffer count\n"
                            "• <code>/generate</code> — Generate a new Reel on demand\n"
                            "• <code>/postnow</code> — Post oldest reel to Facebook now\n"
                            "• <code>/help</code> — Show this menu"
                        )
                        send_telegram_message(help_text)

        except Exception as e:
            print(f"[Telegram Listener Exception]: {e}")
            time.sleep(5)

        time.sleep(1)

if __name__ == "__main__":
    run_listener()
