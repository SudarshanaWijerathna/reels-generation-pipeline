"""
telegram_notifier.py
====================
Telegram Bot Notifier Module.
Sends instant text alerts, error logs, and full MP4 video previews directly
to your Telegram chat using Telegram Bot API.

SETUP INSTRUCTIONS:
1. Open Telegram -> Search for @BotFather -> Send /newbot
2. Name your bot and copy TELEGRAM_BOT_TOKEN (e.g. "123456789:ABC...")
3. Search for @userinfobot -> Copy your numerical TELEGRAM_CHAT_ID
4. Add to .env and GitHub Secrets:
     TELEGRAM_BOT_TOKEN=<your_token>
     TELEGRAM_CHAT_ID=<your_chat_id>
"""

import os
import sys
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()



def get_telegram_creds() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id

def send_telegram_message(text: str) -> bool:
    """Sends a text message / alert / error log to Telegram."""
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        print("  [Telegram] Notice: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping Telegram alert.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200:
            print("  [Telegram] ✅ Alert sent successfully to Telegram!")
            return True
        else:
            print(f"  [Telegram] Warning: Telegram API returned status {r.status_code}: {r.text}")
    except Exception as e:
        print(f"  [Telegram] Error sending message: {e}")

    return False

def send_telegram_video(video_path: str, caption: str = "") -> bool:
    """Sends a generated MP4 video file directly to your Telegram chat."""
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        print("  [Telegram] Notice: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping Telegram video send.")
        return False

    if not os.path.exists(video_path):
        print(f"  [Telegram] Error: Video file not found: {video_path}")
        return False

    url = f"https://api.telegram.org/bot{token}/sendVideo"
    
    try:
        print(f"  [Telegram] 📤 Uploading MP4 video ({os.path.getsize(video_path)/(1024*1024):.2f} MB) to Telegram...")
        with open(video_path, "rb") as video_file:
            files = {"video": video_file}
            data = {
                "chat_id": chat_id,
                "caption": caption[:1024]
            }
            r = requests.post(url, data=data, files=files, timeout=90)
            if r.status_code == 200:
                print("  [Telegram] ✅ Video successfully delivered to your Telegram chat!")
                return True
            else:
                print(f"  [Telegram] Warning: Video send returned status {r.status_code}: {r.text}")
    except Exception as e:
        print(f"  [Telegram] Error uploading video to Telegram: {e}")

    return False

if __name__ == "__main__":
    print("Testing Telegram Notifier...")
    token, chat_id = get_telegram_creds()
    if not token or not chat_id:
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to test.")
    else:
        send_telegram_message("🎬 <b>Reel Pipeline Test</b>\nTelegram notifications are working perfectly!")
