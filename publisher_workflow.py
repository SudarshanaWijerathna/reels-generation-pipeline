"""
publisher_workflow.py
=====================
Publisher Workflow: Pops the oldest pre-generated Reel from `video_store/`
and uploads it to Facebook Page via Meta Graph API.
Runs 2 times a day at target posting times via GitHub Actions Cron.

Logic:
1. Pops the oldest (mp4_path, json_path, metadata) from video_store.
2. If store is empty: logs warning and exits.
3. Uploads video to Facebook Page using publishers/facebook_publisher.py.
4. Appends to published_history.jsonl.
5. Deletes uploaded MP4 and JSON from video_store/.
"""

import os
import sys
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_store import pop_oldest_reel, remove_from_store, get_stored_reels_count, MAX_STORE_CAPACITY
from publishers.facebook_publisher import publish_facebook_reel
from telegram_notifier import send_telegram_message

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "published_history.jsonl")

def run_publisher():
    print("\n=======================================================")
    print("PUBLISHER WORKFLOW: FACEBOOK REEL POSTING")
    print("=======================================================")
    
    current_count = get_stored_reels_count()
    print(f"Current Video Store Buffer: {current_count}/{MAX_STORE_CAPACITY} reels available.")
    
    reel_item = pop_oldest_reel()
    if not reel_item:
        msg = "⚠️ <b>Publisher Warning:</b> Video Store Buffer is EMPTY (0 reels available). Skipping publication run."
        print(msg)
        sys.exit(0)
        
    mp4_path, json_path, metadata = reel_item
    reel_id = metadata.get("reel_id", "unknown_reel")
    quote = metadata.get("quote", "")
    caption = metadata.get("caption", quote)
    
    # Ensure caption includes algorithmic hashtags and follower CTA
    if "#reels" not in caption:
        caption = f"{caption}\n\n👉 Follow @Midnight Whispers for daily deep thoughts & wisdom.\n\n#reels #facebookreels #midnightwhispers #philosophy #wisdom #quotes #motivation #mindset #deep"

    print(f"\n[Publisher] Popped oldest reel from buffer: {reel_id}")
    print(f"  - File: {mp4_path}")
    print(f"  - Created At: {metadata.get('created_at')}")
    print(f"  - Caption: \"{caption[:80]}...\"")
    
    print("\nPublishing Reel to Facebook Page...")
    try:
        res = publish_facebook_reel(mp4_path, title="Daily Wisdom • Midnight Whispers", description=caption)
        
        if res.get("success"):
            post_url = res.get("url", "")
            post_id = res.get("post_id", "")
            print(f"\n🎉 Successfully Published Reel to Facebook!")
            print(f"  - Reel URL: {post_url}")
            print(f"  - Post ID: {post_id}")
            
            # Log to published_history.jsonl
            history_entry = {
                "published_at": datetime.utcnow().isoformat() + "Z",
                "reel_id": reel_id,
                "post_id": post_id,
                "url": post_url,
                "quote": quote,
                "caption": caption
            }
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(history_entry, ensure_ascii=False) + "\n")
                
            # Remove from video_store buffer
            remove_from_store(reel_id)
            
            remaining_count = get_stored_reels_count()
            print(f"[Publisher] Store Buffer now has {remaining_count}/{MAX_STORE_CAPACITY} reels remaining.")
            
            # Telegram Success Alert
            tg_msg = f"🚀 <b>Published Reel to Facebook!</b>\n\n<b>Quote:</b> \"{quote[:100]}\"\n<b>URL:</b> {post_url}\n<b>Buffer Remaining:</b> {remaining_count}/{MAX_STORE_CAPACITY}"
            send_telegram_message(tg_msg)
        else:
            err_msg = f"❌ <b>Publisher Error:</b> Facebook publication failed: {res.get('error')}"
            print(err_msg)
            send_telegram_message(err_msg)
            sys.exit(1)
            
    except Exception as e:
        err_msg = f"🚨 <b>Publisher Pipeline Crash Error:</b> {e}"
        print(err_msg)
        send_telegram_message(err_msg)
        sys.exit(1)

if __name__ == "__main__":
    run_publisher()

