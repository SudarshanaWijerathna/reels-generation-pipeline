# Automated Video Reels Generation & Publishing Pipeline 🎬

An end-to-end automated video generation and social media publishing pipeline. The system utilizes Gemini/Groq LLMs to generate thematic quotes/scripts, synthesizes TTS audio, creates dynamic images, animates kinetic typography subtitles, renders reel-optimized vertical videos, and schedules/publishes them to social media platforms.

---

## 🏛️ System Architecture

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

## ✨ Features

- **Dynamic Content Generation:** Powered by LLMs using customized templates matching high-performing social media reels.
- **Audio Synthesis:** High-quality TTS generated via `edge-tts` with custom speech rates and parsing delay rules.
- **Visuals Generation:** Programmatically fetches stylistic AI illustrations tailored to every clause.
- **Kinetic Subtitles:** "Boiling" animated SVGs and typography rendered over the video for high engagement.
- **Auto-Publishing:** Integrates directly with Facebook & Instagram Graph APIs (with support for shadow/dry-run modes).

---

## 📁 Repository Structure

```text
video_generation_pipeline/
├── assets/                     # Soundtracks, music, and static assets
├── docs/                       # Architecture and design documentation
├── fonts/                      # TrueType/OpenType font files for subtitles
├── publishers/                 # Social media publisher modules (FB, IG, etc.)
├── config.py                   # Configuration and environment setup loader
├── generate_reel.py            # Standalone Local Video Generator & Stitcher
├── quote_engine.py             # Scripting and quote generation engine
├── run_pipeline.py             # Main entry point orchestration script
├── subtitle_boil.py            # Animated SVG font and subtitle rendering engine
├── requirements.txt            # Python package dependencies
├── .gitignore                  # Git ignore rules
└── .env.example                # Template configuration file
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg:** Ensure FFmpeg is installed and added to your system's PATH.

### 2. Installation
Clone this repository and install the dependencies:
```bash
git clone https://github.com/SudarshanaWijerathna/YOUR-REPO-NAME.git
cd video_generation_pipeline
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root of the project using the template provided:
```bash
cp .env.example .env
```
Open the `.env` file and populate it with your API keys and credentials:
- `GEMINI_API_KEY`: Google Gemini API key.
- `FB_PAGE_ID` & `FB_ACCESS_TOKEN`: Meta Graph API credentials for auto-publishing to Facebook/Instagram.

### 4. Running the Pipeline
To run the full automated loop (quote generation -> video rendering -> publishing):
```bash
python run_pipeline.py
```
To generate a single reel locally without publishing:
```bash
python generate_reel.py --prompt "your quote prompt"
```

---

## 🛡️ License

This project is licensed under the MIT License.
