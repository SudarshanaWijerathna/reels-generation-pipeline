"""
run_pipeline.py
===============
Autonomous Video Generation & Social Publishing Pipeline.

Ties together all pipeline modules:
1. Quote Generation: Generates an introspective philosophical quote via quote_engine.py.
2. Video Compiling: Compiles a vertical 9:16 video reel with animated subtitles and FLUX images via generate_reel.py.
3. Social Publishing: Uploads the completed reel as a Facebook Reel using publishers/.
4. Memory DB Log: Logs transaction details to output_reels/published_history.jsonl.

Usage:
    python run_pipeline.py
    python run_pipeline.py --theme betrayal
    python run_pipeline.py --shadow-mode      # compiles video but skips FB upload
"""

import os
import sys
import json
import time
import argparse
import datetime

# Import local pipeline modules
from config import cfg
from quote_engine import generate_quote
from generate_reel import generate_full_reel
from publishers import publish_to_platforms, print_publish_summary

sys.stdout.reconfigure(encoding="utf-8")


def run_pipeline(theme: str = "", shadow_mode: bool = False):
    print("\n" + "=" * 60)
    print("        STARTING AUTOMATED REELS PUBLISHING PIPELINE")
    print("=" * 60 + "\n")

    run_timestamp = datetime.datetime.now().isoformat()
    start_time = time.time()

    # ───────────────────────────────────────────────────────────────────────
    # Step 1: Quote Generation
    # ───────────────────────────────────────────────────────────────────────
    print("Step 1: Generating original Whisprs quote...")
    try:
        quote = generate_quote(theme=theme)
        print(f"📜 Generated Quote:\n  \"{quote}\"\n")
    except Exception as e:
        print(f"❌ Quote generation failed: {e}")
        return

    # ───────────────────────────────────────────────────────────────────────
    # Step 2: Video Reel Compilation
    # ───────────────────────────────────────────────────────────────────────
    print("Step 2: Compiling video reel...")
    try:
        video_path = generate_full_reel(quote)
        print(f"🎥 Video compiled successfully: {video_path}\n")
    except Exception as e:
        print(f"❌ Video compilation failed: {e}")
        return

    # ───────────────────────────────────────────────────────────────────────
    # Step 3: Social Media Publishing
    # ───────────────────────────────────────────────────────────────────────
    publish_results = {}
    is_shadow = shadow_mode

    # Check if credentials are present
    fb_page_id = os.environ.get("FB_PAGE_ID", cfg.FB_PAGE_ID)
    fb_token = os.environ.get("FB_SYSTEM_USER_TOKEN", cfg.FB_SYSTEM_USER_TOKEN) or os.environ.get("FB_ACCESS_TOKEN", cfg.FB_ACCESS_TOKEN)

    if not fb_page_id or not fb_token:
        print("⚠️ Facebook Page ID or Token is missing in .env. Running in SHADOW MODE (local compile only).")
        is_shadow = True

    if is_shadow:
        print("\nStep 3: [SHADOW MODE] Skipping Facebook upload.")
        publish_results["facebook"] = {
            "success": True,
            "post_id": "shadow",
            "url": "local_preview_only",
            "message": "Shadow mode enabled — skipped publishing."
        }
    else:
        print("\nStep 3: Publishing to Facebook Reels...")
        # Caption is the quote itself
        caption = quote
        title = "Daily Reflections • Whisprs"
        
        publish_results = publish_to_platforms(
            video_path=video_path,
            title=title,
            description=caption,
            platforms=["facebook"]
        )
        print_publish_summary(publish_results)

    # ───────────────────────────────────────────────────────────────────────
    # Step 4: Memory Database Logging
    # ───────────────────────────────────────────────────────────────────────
    print("\nStep 4: Writing results to memory history log...")
    log_path = os.path.join(cfg.OUTPUT_DIR, "published_history.jsonl")
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    record = {
        "timestamp": run_timestamp,
        "elapsed_seconds": int(time.time() - start_time),
        "quote": quote,
        "theme": theme,
        "video_path": video_path,
        "shadow_mode": is_shadow,
        "publish_results": publish_results
    }

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"📝 Memory log updated: {log_path}")
    except Exception as e:
        print(f"⚠️ Failed to write to memory log: {e}")

    print("\n" + "=" * 60)
    print("                 PIPELINE RUN COMPLETED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisprs Video & Publishing Pipeline")
    parser.add_argument("--theme", type=str, default="", help="Theme of the quote to generate")
    parser.add_argument("--shadow-mode", action="store_true", help="Compile video locally but do not upload to FB")
    args = parser.parse_args()

    run_pipeline(theme=args.theme, shadow_mode=args.shadow_mode)
