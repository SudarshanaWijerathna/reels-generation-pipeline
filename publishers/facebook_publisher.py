"""
publishers/facebook_publisher.py
=================================
Publishes a local MP4 video as a Facebook Reel using the Meta Graph API.

SETUP REQUIRED
--------------
1. Create a Meta Developer App at https://developers.facebook.com/
2. Add "Facebook Login" + "Pages API" products
3. Generate a Page Access Token with these permissions:
   - pages_read_engagement
   - pages_show_list
   - publish_video
4. Get your Page ID (numeric, found in Page About section or via Graph API Explorer)
5. Set in .env:
   FB_PAGE_ID=<your_numeric_page_id>
   FB_ACCESS_TOKEN=<your_page_access_token>

API FLOW (3-step resumable upload)
-----------------------------------
Step 1: Initialize upload session → get upload_url + video_id
Step 2: Upload binary via PUT to upload_url
Step 3: Publish Reel → POST to /{page_id}/video_reels

Documentation:
  https://developers.facebook.com/docs/video-api/guides/reels-publishing
"""

from __future__ import annotations

import os
import sys
import requests

from config import cfg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


GRAPH_API_VERSION = "v22.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def get_page_access_token(page_id: str, system_user_token: str) -> str:
    """
    Fetches Page Access Token using Business System User Token.
    Falls back to the system user token if the request fails.
    """
    url = f"{GRAPH_BASE}/{page_id}"
    params = {
        "fields": "access_token",
        "access_token": system_user_token
    }
    try:
        print(f"  [FB] Attempting to retrieve Page Access Token dynamically using System User Token...")
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token")
            if token:
                print(f"  [FB] Successfully retrieved Page Access Token for Page: {page_id}")
                return token
        print(f"  [FB] Warning: Page Access Token request failed: {r.text}. Falling back to system user token.")
    except Exception as e:
        print(f"  [FB] Warning: Page Access Token request exception: {e}. Falling back to system user token.")
    return system_user_token


def _check_credentials() -> tuple[str, str]:
    """Validates that FB credentials are configured."""
    page_id = cfg.FB_PAGE_ID
    system_user_token = cfg.FB_SYSTEM_USER_TOKEN
    access_token = cfg.FB_ACCESS_TOKEN
    
    if not page_id:
        raise ValueError(
            "FB_PAGE_ID not set. Add it to your .env file.\n"
            "  Get it from: Facebook Page → About → Page ID"
        )
        
    if not access_token and not system_user_token:
        raise ValueError(
            "Neither FB_ACCESS_TOKEN nor FB_SYSTEM_USER_TOKEN is set. Add at least one to your .env file.\n"
            "  Generate at: https://developers.facebook.com/tools/explorer/"
        )
        
    if system_user_token:
        token = get_page_access_token(page_id, system_user_token)
    else:
        token = access_token
        
    return page_id, token



def _initialize_upload_session(page_id: str, token: str, file_size: int) -> tuple[str, str]:
    """
    Step 1: Initialize a resumable upload session.
    Returns (upload_url, video_id).
    """
    url = f"{GRAPH_BASE}/{page_id}/video_reels"
    params = {
        "upload_phase": "start",
        "access_token": token,
    }
    r = requests.post(url, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"FB init upload failed [{r.status_code}]: {r.text}")
    data = r.json()
    upload_url = data.get("upload_url")
    video_id = data.get("video_id")
    if not upload_url or not video_id:
        raise RuntimeError(f"Unexpected FB init response: {data}")
    print(f"  [FB] Upload session initialized. video_id={video_id}")
    return upload_url, video_id


def _upload_video_binary(upload_url: str, token: str, video_path: str) -> bool:
    """
    Step 2: Upload the MP4 binary via PUT to the upload URL.
    Returns True on success.
    """
    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"OAuth {token}",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Type": "application/octet-stream",
    }
    print(f"  [FB] Uploading {file_size / 1024 / 1024:.1f} MB to upload URL...")
    with open(video_path, "rb") as f:
        r = requests.post(upload_url, headers=headers, data=f, timeout=300)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"FB upload binary failed [{r.status_code}]: {r.text}")
    print(f"  [FB] Binary upload complete.")
    return True


def _publish_reel(page_id: str, token: str, video_id: str, title: str, description: str) -> dict:
    """
    Step 3: Publish the uploaded video as a Reel.
    Returns the API response dict.
    """
    url = f"{GRAPH_BASE}/{page_id}/video_reels"
    payload = {
        "access_token": token,
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "title": title[:255],
        "description": description[:2000],
    }
    r = requests.post(url, data=payload, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"FB publish failed [{r.status_code}]: {r.text}")
    return r.json()


def publish_facebook_reel(video_path: str, title: str = "", description: str = "") -> dict:
    """
    Full 3-step Facebook Reel publishing flow.

    Args:
        video_path:   Absolute path to the MP4 file.
        title:        Reel title (max 255 chars).
        description:  Reel description / caption (max 2000 chars).

    Returns:
        dict with keys: success, post_id, url, error (if failed).
    """
    title = title or cfg.DEFAULT_REEL_TITLE
    description = description or cfg.DEFAULT_REEL_DESCRIPTION

    if not os.path.exists(video_path):
        return {"success": False, "error": f"Video file not found: {video_path}"}

    try:
        page_id, token = _check_credentials()
        file_size = os.path.getsize(video_path)

        upload_url, video_id = _initialize_upload_session(page_id, token, file_size)
        _upload_video_binary(upload_url, token, video_path)
        result = _publish_reel(page_id, token, video_id, title, description)

        post_id = result.get("post_id") or result.get("id") or video_id
        reel_url = f"https://www.facebook.com/reel/{video_id}"
        print(f"  [FB] ✅ Published! Reel URL: {reel_url}")

        return {
            "success": True,
            "post_id": post_id,
            "video_id": video_id,
            "url": reel_url,
            "response": result,
        }

    except Exception as e:
        print(f"  [FB] ❌ Failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python publishers/facebook_publisher.py <path_to_reel.mp4>")
        sys.exit(1)
    result = publish_facebook_reel(sys.argv[1])
    print(result)
