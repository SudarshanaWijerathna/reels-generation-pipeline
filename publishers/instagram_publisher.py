"""
publishers/instagram_publisher.py
==================================
Publishes a local MP4 video as an Instagram Reel using the Instagram Graph API.

SETUP REQUIRED
--------------
The Instagram Graph API requires a **public video URL** — it cannot upload
from a local file directly. Two options:

Option A (Recommended for automation): Upload the MP4 to a temporary public
    host first (e.g. Cloudinary, S3, or a simple Flask server with ngrok),
    then pass the public URL to this publisher.

Option B: If you already have a publicly accessible URL for the video
    (e.g. from a CDN or file host), pass it via the `video_url` parameter.

This publisher handles Option B natively. For Option A, set a `VIDEO_HOST_URL`
in your .env pointing to your hosting endpoint (see `_upload_to_host()`).

CREDENTIALS REQUIRED
---------------------
Set in .env:
    IG_USER_ID=<instagram_business_account_id>
    IG_ACCESS_TOKEN=<instagram_graph_api_access_token>

The access token must have permissions:
    instagram_basic, instagram_content_publish, pages_read_engagement

Get your IG Business Account ID:
    GET https://graph.facebook.com/v22.0/me/accounts?access_token=TOKEN
    Then: GET https://graph.facebook.com/v22.0/{page_id}?fields=instagram_business_account

Documentation:
    https://developers.facebook.com/docs/instagram-api/guides/content-publishing
"""

from __future__ import annotations

import os
import time
import requests

from config import cfg


GRAPH_API_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# How long to wait for Instagram to finish processing the video container
CONTAINER_POLL_INTERVAL_SEC = 5
CONTAINER_POLL_MAX_ATTEMPTS = 24  # ~2 minutes max


def _check_credentials() -> tuple[str, str]:
    user_id = cfg.IG_USER_ID
    token = cfg.IG_ACCESS_TOKEN
    if not user_id:
        raise ValueError(
            "IG_USER_ID not set. Add it to your .env file.\n"
            "  Get via: GET /me/accounts → find page → GET /{page_id}?fields=instagram_business_account"
        )
    if not token:
        raise ValueError(
            "IG_ACCESS_TOKEN not set. Add it to your .env file.\n"
            "  Generate at: https://developers.facebook.com/tools/explorer/"
        )
    return user_id, token


def _host_video_locally(video_path: str) -> str | None:
    """
    Optional: if VIDEO_HOST_URL is set in config, upload the file there
    and return the public URL. Otherwise returns None.

    Set VIDEO_HOST_URL to your hosting endpoint (e.g. a simple Flask upload server).
    """
    host_url = os.environ.get("VIDEO_HOST_URL", "").strip()
    if not host_url:
        return None
    try:
        with open(video_path, "rb") as f:
            r = requests.post(host_url, files={"file": f}, timeout=120)
        if r.status_code == 200:
            public_url = r.json().get("url") or r.text.strip()
            print(f"  [IG] Video hosted at: {public_url}")
            return public_url
    except Exception as e:
        print(f"  [IG] Video hosting failed: {e}")
    return None


def _create_media_container(user_id: str, token: str, video_url: str, caption: str) -> str:
    """
    Step 1: Create a Reels media container.
    Returns container_id.
    """
    url = f"{GRAPH_BASE}/{user_id}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption[:2200],
        "share_to_feed": "true",
        "access_token": token,
    }
    r = requests.post(url, data=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"IG create container failed [{r.status_code}]: {r.text}")
    container_id = r.json().get("id")
    if not container_id:
        raise RuntimeError(f"IG container response missing id: {r.json()}")
    print(f"  [IG] Media container created. id={container_id}")
    return container_id


def _wait_for_container_ready(user_id: str, token: str, container_id: str) -> bool:
    """
    Step 2: Poll container status until FINISHED.
    Instagram processes the video asynchronously.
    """
    print(f"  [IG] Waiting for video processing...")
    url = f"{GRAPH_BASE}/{container_id}"
    params = {"fields": "status_code,status", "access_token": token}

    for attempt in range(CONTAINER_POLL_MAX_ATTEMPTS):
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status_code", "")
            print(f"  [IG]   Attempt {attempt+1}: status={status}")
            if status == "FINISHED":
                return True
            elif status == "ERROR":
                raise RuntimeError(f"IG container processing error: {data.get('status', 'unknown')}")
        time.sleep(CONTAINER_POLL_INTERVAL_SEC)

    raise RuntimeError(f"IG container not ready after {CONTAINER_POLL_MAX_ATTEMPTS * CONTAINER_POLL_INTERVAL_SEC}s")


def _publish_container(user_id: str, token: str, container_id: str) -> dict:
    """
    Step 3: Publish the finished container.
    """
    url = f"{GRAPH_BASE}/{user_id}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": token,
    }
    r = requests.post(url, data=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"IG publish failed [{r.status_code}]: {r.text}")
    return r.json()


def publish_instagram_reel(
    video_path: str,
    title: str = "",
    description: str = "",
    video_url: str = "",
) -> dict:
    """
    Full 3-step Instagram Reel publishing flow.

    Args:
        video_path:   Absolute path to the local MP4 file.
        title:        Unused (Instagram captions don't have a separate title).
        description:  Caption / description text (max 2200 chars).
        video_url:    Public URL to the video (required). If empty, will attempt
                      to upload via VIDEO_HOST_URL env var.

    Returns:
        dict with keys: success, media_id, url, error (if failed).
    """
    description = description or cfg.DEFAULT_REEL_DESCRIPTION

    if not video_url:
        video_url = _host_video_locally(video_path) or ""

    if not video_url:
        msg = (
            "Instagram requires a publicly accessible video URL.\n"
            "  Options:\n"
            "  1. Set VIDEO_HOST_URL in .env to point to your upload endpoint\n"
            "  2. Upload the MP4 to a CDN and pass the URL via the video_url parameter\n"
            "  3. Use the Facebook publisher instead (supports local file upload)"
        )
        print(f"  [IG] ❌ {msg}")
        return {"success": False, "error": "No public video URL available. " + msg}

    if not os.path.exists(video_path) and not video_url:
        return {"success": False, "error": f"Video file not found: {video_path}"}

    try:
        user_id, token = _check_credentials()
        caption = f"{description}"

        container_id = _create_media_container(user_id, token, video_url, caption)
        _wait_for_container_ready(user_id, token, container_id)
        result = _publish_container(user_id, token, container_id)

        media_id = result.get("id")
        reel_url = f"https://www.instagram.com/reel/{media_id}/" if media_id else "N/A"
        print(f"  [IG] ✅ Published! Media ID: {media_id}")

        return {
            "success": True,
            "media_id": media_id,
            "url": reel_url,
            "response": result,
        }

    except Exception as e:
        print(f"  [IG] ❌ Failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python publishers/instagram_publisher.py <path_to_reel.mp4> <public_video_url>")
        sys.exit(1)
    result = publish_instagram_reel(sys.argv[1], video_url=sys.argv[2])
    print(result)
