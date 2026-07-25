"""
video_store.py
==============
Decoupled Video Store Manager (Buffer Queue).
Maintains a local buffer of pre-generated Reels (max 5 videos) in `video_store/`.
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime

STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_store")
MAX_STORE_CAPACITY = 5

def ensure_store_dir():
    if not os.path.exists(STORE_DIR):
        os.makedirs(STORE_DIR, exist_ok=True)
    return STORE_DIR

def get_stored_reels_count() -> int:
    """Returns the current number of pre-generated reels in the video_store."""
    ensure_store_dir()
    mp4_files = [f for f in os.listdir(STORE_DIR) if f.startswith("reel_") and f.endswith(".mp4")]
    return len(mp4_files)

def add_reel_to_store(video_mp4_path: str, quote_text: str, caption_text: str = "", voice_preset: str = "Algenib") -> dict:
    """
    Moves a rendered video into `video_store/` with matching JSON metadata.
    """
    ensure_store_dir()
    current_count = get_stored_reels_count()
    if current_count >= MAX_STORE_CAPACITY:
        print(f"[VideoStore] ⚠️ Buffer full ({current_count}/{MAX_STORE_CAPACITY}). Cannot add more reels until published.")
        return {"success": False, "reason": "Buffer full"}

    timestamp = int(time.time())
    reel_id = f"reel_spiritual_{timestamp}"
    target_mp4 = os.path.join(STORE_DIR, f"{reel_id}.mp4")
    target_json = os.path.join(STORE_DIR, f"{reel_id}.json")

    shutil.copy2(video_mp4_path, target_mp4)

    metadata = {
        "reel_id": reel_id,
        "quote": quote_text,
        "caption": caption_text or quote_text,
        "voice_preset": voice_preset,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "mp4_file": f"{reel_id}.mp4",
        "json_file": f"{reel_id}.json"
    }

    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[VideoStore] ✅ Reel added to store: {target_mp4} (Store buffer: {current_count + 1}/{MAX_STORE_CAPACITY})")
    return {"success": True, "reel_id": reel_id, "mp4_path": target_mp4, "json_path": target_json}

def pop_oldest_reel() -> tuple[str, str, dict] | None:
    """
    Retrieves (mp4_path, json_path, metadata) for the oldest reel in the store.
    Returns None if store is empty.
    """
    ensure_store_dir()
    json_files = sorted([f for f in os.listdir(STORE_DIR) if f.startswith("reel_") and f.endswith(".json")])
    if not json_files:
        return None

    oldest_json_name = json_files[0]
    json_path = os.path.join(STORE_DIR, oldest_json_name)
    mp4_name = oldest_json_name.replace(".json", ".mp4")
    mp4_path = os.path.join(STORE_DIR, mp4_name)

    if not os.path.exists(mp4_path):
        print(f"[VideoStore] Warning: MP4 missing for metadata {oldest_json_name}, purging.")
        os.remove(json_path)
        return pop_oldest_reel()

    with open(json_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return mp4_path, json_path, metadata

def remove_from_store(reel_id: str):
    """Deletes the MP4 and JSON for a published reel from video_store/."""
    ensure_store_dir()
    mp4_path = os.path.join(STORE_DIR, f"{reel_id}.mp4")
    json_path = os.path.join(STORE_DIR, f"{reel_id}.json")

    if os.path.exists(mp4_path):
        try:
            os.remove(mp4_path)
        except Exception as e:
            print(f"[VideoStore] Error removing {mp4_path}: {e}")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception as e:
            print(f"[VideoStore] Error removing {json_path}: {e}")

    print(f"[VideoStore] 🧹 Purged published reel {reel_id} from store buffer.")

if __name__ == "__main__":
    ensure_store_dir()
    print(f"VideoStore initialized at: {STORE_DIR}")
    print(f"Current pre-generated reels count: {get_stored_reels_count()}/{MAX_STORE_CAPACITY}")
