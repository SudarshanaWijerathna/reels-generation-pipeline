"""
producer_workflow.py
====================
Producer Workflow: Generates a new Reel video and buffers it into `video_store/`.
Runs 4 times a day via GitHub Actions Cron.

Logic:
1. Checks current video_store buffer count.
2. If buffer >= 5: exits cleanly (no unnecessary API usage or rendering).
3. If buffer < 5: generates quote + renders reel MP4 + adds to video_store.
"""

import os
import sys
import random

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_store import get_stored_reels_count, add_reel_to_store, MAX_STORE_CAPACITY
from generate_reel import generate_full_reel
from quote_engine import get_fresh_quote
from telegram_notifier import send_telegram_message, send_telegram_video

def run_producer():
    print("\n=======================================================")
    print("PRODUCER WORKFLOW: REEL GENERATOR & STORE BUFFER")
    print("=======================================================")
    
    current_count = get_stored_reels_count()
    print(f"Current Video Store Buffer: {current_count}/{MAX_STORE_CAPACITY} reels ready.")
    
    if current_count >= MAX_STORE_CAPACITY:
        print(f"✅ Video store buffer is FULL ({current_count}/{MAX_STORE_CAPACITY}). Skipping generation to conserve resources.")
        sys.exit(0)
        
    print(f"\n[Producer] Buffer space available ({current_count}/{MAX_STORE_CAPACITY}). Generating a new Reel video...")
    
    try:
        # 1. Fetch a fresh spiritual/story quote
        quote_data = get_fresh_quote()
        quote_text = quote_data.get("quote", "Never ask a liar why they lied. To explain it, they would have to lie again.")
        print(f"Selected Quote: \"{quote_text[:80]}...\"")
        
        # 2. Render Full Reel Video
        voice_choice = random.choice(["Algenib", "Kore"])
        output_mp4 = generate_full_reel(quote_text=quote_text, voice_preset=voice_choice, reuse_assets=False)
        
        if output_mp4 and os.path.exists(output_mp4):
            # 3. Add to video_store buffer
            caption = f"{quote_text}\n\n✨ Follow for daily quiet wisdom & spiritual stories.\n\n#quotes #mindset #motivation #wisdom #reels #life"
            result = add_reel_to_store(output_mp4, quote_text, caption, voice_choice)
            
            if result.get("success"):
                new_count = get_stored_reels_count()
                print(f"\n🎉 Producer Workflow Complete! Store Buffer is now at {new_count}/{MAX_STORE_CAPACITY} reels.")
                
                # Telegram Notification & Video Delivery
                tg_caption = f"🎬 <b>New Reel Generated & Buffered!</b>\n\n<b>Quote:</b> \"{quote_text}\"\n<b>Voice:</b> {voice_choice}\n<b>Buffer:</b> {new_count}/{MAX_STORE_CAPACITY}"
                send_telegram_video(output_mp4, caption=tg_caption)
            else:
                err_msg = f"❌ <b>Producer Error:</b> Failed to add reel to store: {result.get('reason')}"
                print(err_msg)
                send_telegram_message(err_msg)
                sys.exit(1)
        else:
            err_msg = "❌ <b>Producer Error:</b> Reel video rendering failed."
            print(err_msg)
            send_telegram_message(err_msg)
            sys.exit(1)

    except Exception as e:
        err_msg = f"🚨 <b>Producer Pipeline Crash Error:</b> {e}"
        print(err_msg)
        send_telegram_message(err_msg)
        sys.exit(1)


if __name__ == "__main__":
    run_producer()
