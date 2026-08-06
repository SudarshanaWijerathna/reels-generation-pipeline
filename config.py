"""
config.py
=========
Centralized configuration and secrets management for the video generation pipeline.

All API keys and tunable settings are sourced from environment variables first,
then fall back to hardcoded defaults. Edit the .env file (copy from .env.example)
to configure your deployment.

Usage:
    from config import cfg
    api_key = cfg.GEMINI_API_KEY
    video_w  = cfg.VIDEO_W
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root (silently ignored if it doesn't exist)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.resolve()
load_dotenv(_ROOT / ".env", override=False)


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


class PipelineConfig:
    """Singleton-style config object — import `cfg` from this module."""

    # ── Workspace Paths ────────────────────────────────────────────────────
    WORKSPACE_DIR: str = str(_ROOT)
    OUTPUT_DIR:    str = str(_ROOT / "output_reels")
    TEMP_DIR:      str = str(_ROOT / "temp_build")
    ASSETS_DIR:    str = str(_ROOT / "assets")
    MUSIC_DIR:     str = str(_ROOT / "assets" / "music")
    FONTS_DIR:     str = str(_ROOT / "fonts")
    OVERLAY_DIR:   str = str(_ROOT / "overlay_video_footages")
    DOCS_DIR:      str = str(_ROOT / "docs")
    TRANSCRIPTS_FILE: str = str(_ROOT / "facebook_reels_transcripts.md")

    # ── Video Format ───────────────────────────────────────────────────────
    VIDEO_W:  int = 1080
    VIDEO_H:  int = 1920
    VIDEO_FPS: int = 30

    # ── Background Music ───────────────────────────────────────────────────
    BG_MUSIC_FILE:   str = str(_ROOT / "assets" / "music" / "heartbreaking_piano.mp3")
    BG_MUSIC_VOLUME: float = 1.00          # 100% volume
    BG_MUSIC_FADEOUT_SEC: float = 1.5      # fade-out duration at end of reel

    # ── Image Generation ───────────────────────────────────────────────────
    UNIFIED_STYLE: str = (
        "retro 90s anime style illustration, Studio Ghibli aesthetic, "
        "dark muted color palette, atmospheric low-key lighting, film grain noise texture, "
        "detailed line art, melancholic lofi mood, vertical 9:16 aspect ratio"
    )

    # ── TTS Voice Settings ─────────────────────────────────────────────────
    PRIMARY_TTS_ENGINE: str  = "GEMINI"  # "GEMINI", "F5_TTS", "ELEVENLABS", "EDGE_TTS"
    GEMINI_TTS_VOICES: list = ["Algenib", "Kore"]
    GEMINI_TTS_VOICE:  str  = "Algenib"
    GEMINI_TTS_STYLE:  str  = "You have a bit calm, mind relaxing voice. Say the following in a bit poetic and story telling way"
    EDGE_TTS_VOICE:    str  = "en-US-ChristopherNeural"
    EDGE_TTS_RATE:     str  = "-25%"
    EDGE_TTS_PITCH:    str  = "-6Hz"

    # ── F5-TTS Voice Cloning Settings ─────────────────────────────────────
    F5_TTS_ENABLED:   bool  = False
    F5_TTS_SPACE:     str   = "mrfakename/E2-F5-TTS"
    F5_TTS_REF_DIR:   str   = str(_ROOT / "reference_voices")
    F5_TTS_SPEED:     float = 0.9  # Deliberate, emotional storytelling pace
    HF_TOKEN:         str   = _env("HF_TOKEN", "")

    # ── ElevenLabs Voice Priority ──────────────────────────────────────────
    ELEVENLABS_VOICES: list = [
        ("hpp4J3VqNfWAUOO0d1Us", "Preferred Storytelling Voice (hpp4J3VqNfWAUOO0d1Us)"),
        ("PB6BdkFkZLbI39GHdnbQ", "User Selected Voice"),
        ("xrNwYO0xeioXswMCcFNF", "Ingmar - Intimately Mysterious"),
        ("N2lVS1w4EtoT3dr4eOWO", "Callum - Deep Breathy Husky Whisper"),
        ("SAz9YHcvj6GT2YYXdXww", "River - Soft Calm & Relaxed"),
        ("EXAVITQu4vr4xnSDxMaL", "Sarah - Soft Reassuring Whisper"),
        ("JBFqnCBsd6RMkjVDRZzb", "George - Captivating Meditative Storyteller"),
    ]

    # ── Clause Pacing (silence delays in seconds) ──────────────────────────
    CLAUSE_DELAY_COMMA:  float = 1.2
    CLAUSE_DELAY_PERIOD: float = 2.0
    CLAUSE_DELAY_END:    float = 1.8

    # ── Quote Engine ───────────────────────────────────────────────────────
    QUOTE_FEW_SHOT_SAMPLES: int = 12       # How many dataset quotes to include as examples
    QUOTE_MODEL_GEMINI:     str = "gemini-3.5-flash-lite"
    QUOTE_MODEL_GROQ:       str = "llama3-70b-8192"

    # ── API Keys ───────────────────────────────────────────────────────────
    GEMINI_API_KEY:      str = _env("GEMINI_API_KEY",      "")
    ELEVENLABS_API_KEY:  str = _env("ELEVENLABS_API_KEY",  "")
    GROQ_API_KEY:        str = _env("GROQ_API_KEY",        "")

    # ── Social Media Credentials (set via .env) ────────────────────────────
    # Facebook / Instagram (Meta Graph API)
    FB_PAGE_ID:          str = _env("FB_PAGE_ID",          "")   # Numeric Page ID
    FB_SYSTEM_USER_TOKEN:str = _env("FB_SYSTEM_USER_TOKEN", "")   # Business System User Token
    FB_ACCESS_TOKEN:     str = _env("FB_ACCESS_TOKEN",     "")   # Page Access Token
    IG_USER_ID:          str = _env("IG_USER_ID",          "")   # Instagram Business Account ID
    IG_ACCESS_TOKEN:     str = _env("IG_ACCESS_TOKEN",     "")   # IG Graph API token (often same as FB)

    # YouTube (OAuth2 — see publishers/youtube_publisher.py for setup)
    YT_CLIENT_SECRETS:   str = _env("YT_CLIENT_SECRETS",   str(_ROOT / "client_secrets.json"))
    YT_OAUTH_TOKEN:      str = _env("YT_OAUTH_TOKEN",      str(_ROOT / "yt_oauth_token.json"))
    YT_CHANNEL_ID:       str = _env("YT_CHANNEL_ID",       "")

    # ── Default Reel Settings ──────────────────────────────────────────────
    DEFAULT_QUOTE: str = (
        "If you see your friend with your enemy, be sure that both are your enemy. "
        "One openly, the other secretly. One walks beside you. The other walks behind you. "
        "Time will show you which one was which. But by then, the damage is done."
    )
    DEFAULT_REEL_TITLE:       str = "Daily Wisdom • Midnight Whispers"
    DEFAULT_REEL_DESCRIPTION: str = "👉 Follow @Midnight Whispers for daily deep thoughts & wisdom.\n\n#reels #facebookreels #midnightwhispers #philosophy #wisdom #quotes #motivation #mindset #deep"
    DEFAULT_REEL_TAGS:        list = ["reels", "facebookreels", "midnightwhispers", "philosophy", "wisdom", "quotes", "motivation", "mindset"]

    def validate(self) -> dict:
        """Returns a dict of which API keys are present vs. missing."""
        status = {}
        for key in ["GEMINI_API_KEY", "ELEVENLABS_API_KEY", "GROQ_API_KEY",
                    "FB_PAGE_ID", "FB_ACCESS_TOKEN", "IG_USER_ID", "IG_ACCESS_TOKEN",
                    "YT_CLIENT_SECRETS", "YT_CHANNEL_ID"]:
            val = getattr(self, key)
            status[key] = "✅ SET" if val and val != str(_ROOT / key.lower() + ".json") else "❌ MISSING"
        return status

    def ensure_dirs(self):
        """Creates all required pipeline directories."""
        for d in [self.OUTPUT_DIR, self.TEMP_DIR, self.MUSIC_DIR, self.FONTS_DIR]:
            os.makedirs(d, exist_ok=True)


# Singleton
cfg = PipelineConfig()


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  VIDEO GENERATION PIPELINE — Config Status")
    print("="*55)
    print(f"\n  Workspace : {cfg.WORKSPACE_DIR}")
    print(f"  Output    : {cfg.OUTPUT_DIR}")
    print(f"  Video     : {cfg.VIDEO_W}x{cfg.VIDEO_H} @ {cfg.VIDEO_FPS}fps")
    print(f"  BG Music  : {cfg.BG_MUSIC_FILE}")
    print(f"  TTS Voice : Gemini({cfg.GEMINI_TTS_VOICE}) / EdgeTTS({cfg.EDGE_TTS_VOICE})")
    print("\n  API Key Status:")
    for k, v in cfg.validate().items():
        print(f"    {k:<24} {v}")
    print()
    cfg.ensure_dirs()
    print("  All output directories confirmed.\n")
