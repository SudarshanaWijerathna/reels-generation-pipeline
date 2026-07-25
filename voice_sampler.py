"""
voice_sampler.py
================
Generates a standalone TTS audio sample using Google Gemini TTS.
Use this to audition voices / style instructions without running the
full reel generation pipeline.

Usage:
    python voice_sampler.py                          # Algenib + wounded_sage style
    python voice_sampler.py --voice Charon           # different voice, same style
    python voice_sampler.py --style hypnosis         # different style preset
    python voice_sampler.py --all-voices             # audition every available voice
    python voice_sampler.py --list-voices            # print all voice names and exit
"""

import argparse
import base64
import os
import sys
import wave
import requests
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Sample quote (used when --text is not supplied)
# ---------------------------------------------------------------------------
SAMPLE_QUOTE = (
    "We build monuments to the memories we cannot save, holding tightly "
    "to the ghosts of who we used to be. You spend your nights negotiating "
    "with shadows, wishing the silence would answer your unspoken questions. "
    "Nothing stays pristine under the heavy weight of passing seasons, yet "
    "you still expect the world to stop turning for your grief. Learn to release "
    "the fragile things that were never truly yours to keep. Peace only finds "
    "you once you finally surrender the fight."
)

# ---------------------------------------------------------------------------
# Style presets — add new ones here to compare different deliveries
# ---------------------------------------------------------------------------
STYLE_PRESETS = {
    "wounded_sage": (
        "A mature, resonant voice (in their late 30s to 50s) speaking in a slow, "
        "deliberate, and intimate tone. The character is a Wounded Sage — someone "
        "who has experienced deep pain but speaks with calm, stoic wisdom and gentle "
        "acceptance rather than anger. The pacing should be measured, with intentional, "
        "breathy pauses before delivering philosophical truths. The voice should have a "
        "slight, cinematic rasp, sounding close to the microphone as if reading a highly "
        "personal letter or narrating a profound, late-night realization. Keep the "
        "emotional delivery melancholic, warm, and highly reflective."
    ),
    "hypnosis": (
        "Sensual Hypnosis - Sensual, Seductive, Gentle, Spiritual, Charming voice. "
        "Suitable for ASMR, Guided Meditation and Hypnosis Inductions. Self realizing "
        "tone, with breath between clauses."
    ),
}

# All available Gemini TTS prebuilt voices
ALL_VOICES = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam",
    "Aoede", "Autonoe", "Callirrhoe", "Charon", "Despina",
    "Enceladus", "Erinome", "Fenrir", "Gacrux", "Iapetus",
    "Kore", "Laomedeia", "Leda", "Orus", "Puck",
    "Pulcherrima", "Rasalgethi", "Sadachbia", "Sadaltager",
    "Schedar", "Sulafat", "Umbriel", "Vindemiatrix", "Wasat", "Zubenelgenubi",
]

TTS_MODEL  = "gemini-3.1-flash-tts-preview"
OUTPUT_DIR = os.path.join("output_reels", "voice_samples")


def generate_voice_sample(text: str, voice: str, style: str, api_key: str, out_path: str):
    """Calls Gemini TTS and saves the PCM data as a .wav file."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{TTS_MODEL}:generateContent?key={api_key}"
    )
    full_prompt = (
        "Please read this text following this style instruction exactly:\n\n"
        f"Style: {style}\n\n"
        f"Text to speak:\n{text}"
    )
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            },
        },
    }

    print(f"\n  Voice: {voice}")
    print(f"  Style: {style[:70]}...")
    print("  Requesting audio from Gemini TTS API...")

    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code != 200:
            print(f"  API error [{r.status_code}]: {r.text[:200]}")
            return None

        data       = r.json()
        candidates = data.get("candidates", [])
        if not candidates:
            print("  No candidates in response.")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for p in parts:
            if "inlineData" in p:
                raw_pcm = base64.b64decode(p["inlineData"]["data"])
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with wave.open(out_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(raw_pcm)
                print(f"  Saved: {out_path}")
                return out_path

        print("  No audio data in response.")
    except Exception as e:
        print(f"  Exception: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Gemini TTS Voice Sampler")
    parser.add_argument("--voice",       default="Algenib",
                        help="Gemini voice name (default: Algenib)")
    parser.add_argument("--style",       default="wounded_sage",
                        help="Style preset key or raw style string (default: wounded_sage)")
    parser.add_argument("--text",        default="",
                        help="Custom quote text (uses built-in sample if omitted)")
    parser.add_argument("--list-voices", action="store_true",
                        help="Print all available voice names and exit")
    parser.add_argument("--all-voices",  action="store_true",
                        help="Generate a sample for every available voice")
    args = parser.parse_args()

    if args.list_voices:
        print("\nAvailable Gemini TTS voices:")
        for v in ALL_VOICES:
            print(f"  {v}")
        return

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("GEMINI_API_KEY is not set. Please add it to your .env file.")
        sys.exit(1)

    text  = args.text.strip() or SAMPLE_QUOTE
    style = STYLE_PRESETS.get(args.style, args.style)

    print("\n" + "=" * 60)
    print("  WHISPRS VOICE SAMPLER")
    print("=" * 60)
    word_count = len(text.split())
    print(f"\nQuote ({word_count} words):\n  \"{text[:110]}...\"")
    print(f"\nStyle preset : {args.style}")

    if args.all_voices:
        print(f"\nGenerating samples for all {len(ALL_VOICES)} voices...")
        succeeded, failed = [], []
        for voice in ALL_VOICES:
            out_path = os.path.join(OUTPUT_DIR, f"sample_{voice.lower()}_{args.style}.wav")
            result   = generate_voice_sample(text, voice, style, api_key, out_path)
            (succeeded if result else failed).append(voice)

        print(f"\nDone. {len(succeeded)} succeeded, {len(failed)} failed.")
        if failed:
            print(f"Failed voices: {failed}")
        print(f"Samples saved to: {OUTPUT_DIR}/")
    else:
        out_path = os.path.join(OUTPUT_DIR, f"sample_{args.voice.lower()}_{args.style}.wav")
        print()
        result = generate_voice_sample(text, args.voice, style, api_key, out_path)
        if result:
            abs_path = os.path.abspath(result)
            print(f"\nAudio file: {abs_path}")
            print("Open that file in Windows Media Player or VLC to audition the voice.")
        else:
            print("\nVoice sample generation failed.")


if __name__ == "__main__":
    main()
