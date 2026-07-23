"""
publishers/__init__.py
======================
Distribution Engine — publishes rendered MP4 reels to social media platforms.

Supports:
  - Facebook Reels (Meta Graph API)
  - Instagram Reels (Instagram Graph API)
  - YouTube Shorts (YouTube Data API v3 via OAuth2)

Usage:
    from publishers import publish_to_all, publish_to_platforms

    # Publish to all configured platforms
    results = publish_to_all(
        video_path="output_reels/reel_spiritual_123.mp4",
        title="Daily Wisdom • Whisprs",
        description="#shorts #philosophy #wisdom",
    )

    # Publish to specific platforms only
    results = publish_to_platforms(
        video_path="output_reels/reel_spiritual_123.mp4",
        title="Daily Wisdom • Whisprs",
        description="#shorts #philosophy #wisdom",
        platforms=["facebook", "instagram"],
    )

    # Results structure:
    # {
    #   "facebook":  {"success": True,  "post_id": "...", "url": "..."},
    #   "instagram": {"success": False, "error": "IG_USER_ID not set"},
    #   "youtube":   {"success": True,  "video_id": "...", "url": "..."},
    # }
"""

from __future__ import annotations

from config import cfg

try:
    from publishers.facebook_publisher import publish_facebook_reel
except ImportError:
    publish_facebook_reel = None

try:
    from publishers.instagram_publisher import publish_instagram_reel
except ImportError:
    publish_instagram_reel = None

try:
    from publishers.youtube_publisher import publish_youtube_short
except ImportError:
    publish_youtube_short = None


SUPPORTED_PLATFORMS = ["facebook", "instagram", "youtube"]


def publish_to_platforms(
    video_path: str,
    title: str = "",
    description: str = "",
    platforms: list[str] | None = None,
) -> dict:
    """
    Publishes the video to the specified platforms.
    Returns a result dict keyed by platform name.
    """
    if platforms is None:
        platforms = SUPPORTED_PLATFORMS

    title = title or cfg.DEFAULT_REEL_TITLE
    description = description or cfg.DEFAULT_REEL_DESCRIPTION

    results = {}

    for platform in platforms:
        platform = platform.lower()
        print(f"\n{'─'*50}")
        print(f"  Publishing to {platform.upper()}...")
        print(f"{'─'*50}")

        try:
            if platform == "facebook":
                if publish_facebook_reel is None:
                    raise ImportError("facebook_publisher.py module not found.")
                results["facebook"] = publish_facebook_reel(video_path, title, description)
            elif platform == "instagram":
                if publish_instagram_reel is None:
                    raise ImportError("instagram_publisher.py module not found.")
                results["instagram"] = publish_instagram_reel(video_path, title, description)
            elif platform == "youtube":
                if publish_youtube_short is None:
                    raise ImportError("youtube_publisher.py module not found.")
                results["youtube"] = publish_youtube_short(video_path, title, description)
            else:
                results[platform] = {"success": False, "error": f"Unknown platform: {platform}"}
        except Exception as e:
            results[platform] = {"success": False, "error": str(e)}
            print(f"  [{platform}] Unhandled exception: {e}")

    return results


def publish_to_all(
    video_path: str,
    title: str = "",
    description: str = "",
) -> dict:
    """Convenience wrapper — publishes to all three platforms."""
    return publish_to_platforms(video_path, title, description, platforms=SUPPORTED_PLATFORMS)


def print_publish_summary(results: dict):
    """Pretty-prints publish results."""
    print(f"\n{'='*55}")
    print("  PUBLISH SUMMARY")
    print(f"{'='*55}")
    for platform, result in results.items():
        if result.get("success"):
            url = result.get("url", result.get("video_id", "N/A"))
            print(f"  ✅ {platform.upper():<12} → {url}")
        else:
            err = result.get("error", "Unknown error")
            print(f"  ❌ {platform.upper():<12} → FAILED: {err}")
    print()
