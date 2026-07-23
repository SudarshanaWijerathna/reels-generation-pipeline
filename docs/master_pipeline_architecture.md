# Master Pipeline Architecture - Automated Video Publishing

This document outlines the complete architectural design for the end-to-end automated video generation and social media publishing pipeline.

---

## 🏛️ System Overview

```mermaid
flowchart TD
    subgraph 1. Content Generation Engine
        Scheduler[GitHub Actions Cron / Local Scheduler] -->|Daily Trigger| LLM[Google Gemini API / Groq]
        LLM -->|Generates Quote & Clause Array| Pipeline[Local Video Generation Tool]
    end

    subgraph 2. Video Rendering Engine (Sub-Pipeline)
        Pipeline --> ClauseSplitter[Clause & Delay Parser]
        ClauseSplitter --> TTS[Edge-TTS Whispering Generator]
        ClauseSplitter --> ImageGen[Pollinations.ai / SDXL 90s Anime Gen]
        TTS & ImageGen --> MoviePy[MoviePy Video Assembly]
        MoviePy --> MP4[Rendered Reel MP4 File]
    end

    subgraph 3. Social Media Distribution Engine
        MP4 --> FBPublisher[Meta Graph API - Facebook Reels]
        MP4 --> YTPublisher[YouTube Data API v3 - Shorts]
        MP4 --> IGPublisher[Meta Graph API - Instagram Reels]
    end
```

---

## 🧩 Modular Components

### 1. Quote & Script Engine
* **Tool**: Google Gemini API / Groq Llama 3 70B (Free tier).
* **Role**: Generates quotes following the exact 111-reel dataset extracted in `facebook_reels_transcripts.md`.
* **Output**: JSON payload with `full_quote` and array of clause objects with prompt hints.

### 2. Video Rendering Engine (Sub-Pipeline - Current Development Focus)
* **Script**: `generate_reel.py`
* **TTS Generator**: `edge-tts` (`en-US-ChristopherNeural` / `en-US-AndrewNeural`, `-15%` rate).
* **Delay Injector**: Inserts `0.5s` silence for commas `,` and `1.1s` silence for periods `.`.
* **Image Generator**: `Pollinations.ai` FLUX / SDXL model using `UNIFIED_STYLE` prompt template.
* **Video Assembler**: `MoviePy` / `FFmpeg` stitching 1 image + 1 audio clip per clause into a single MP4 with Ken Burns zoom, white bold subtitles, and lofi background music.

### 3. Distribution & Publishing Engine (Future Integration)
* **Facebook Reels**: Official Meta Graph API (`/video_reels` endpoint).
* **YouTube Shorts**: YouTube Data API v3 (`videos.insert` endpoint with `alteredOrSyntheticContent` disclosure).
* **Instagram Reels**: Instagram Graph API (`/media` + `/media_publish`).

---

## 📁 File Structure

```text
video_generation_pipeline/
├── docs/
│   └── master_pipeline_architecture.md   # Master System Design Document
├── output_reels/                          # Generated video MP4 outputs
│   └── reel_test.mp4
├── assets/
│   └── lofi_music.mp3                     # Royalty-free lofi audio tracks
├── generate_reel.py                        # Standalone Local Video Generator Tool
├── facebook_reels_transcripts.md          # Reference dataset (111 extracted quotes)
└── requirements.txt                       # Python dependencies
```
