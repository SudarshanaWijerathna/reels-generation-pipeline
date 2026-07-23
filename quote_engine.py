"""
quote_engine.py
===============
LLM-powered quote generator for the Whisprs automated video pipeline.

Generates philosophical / introspective quotes in the exact Whisprs style
extracted from the 111-reel Facebook dataset (facebook_reels_transcripts.md).

Primary:  Google Gemini Flash (free tier)
Fallback: Groq Llama 3 70B (free tier, requires GROQ_API_KEY in .env)

Usage:
    # Python API
    from quote_engine import generate_quote
    quote = generate_quote()

    # CLI
    python quote_engine.py
    python quote_engine.py --count 5         # generate 5 quotes
    python quote_engine.py --theme betrayal  # themed generation
"""

import os
import re
import sys
import json
import random
import argparse
import datetime
import requests

from config import cfg

sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Dataset Loader — reads real Whisprs quotes from the transcript file
# ---------------------------------------------------------------------------

def load_dataset_quotes(n: int = 15) -> list[str]:
    """
    Extracts real quotes from facebook_reels_transcripts.md.
    Skips [Music / Background Sound] entries.
    Returns `n` randomly sampled quotes as a list of strings.
    """
    path = cfg.TRANSCRIPTS_FILE
    if not os.path.exists(path):
        print(f"  [WARN] Transcripts file not found: {path}")
        return []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Extract quote blocks — lines starting with > or under "**Full Quote**:"
    quotes = []
    # Match "**Full Quote**:\n> ..." blocks
    blocks = re.findall(r'\*\*Full Quote\*\*:\s*\n(.*?)(?=\n---|\Z)', content, re.DOTALL)
    for block in blocks:
        # Strip leading "> " from each line
        lines = [re.sub(r'^>\s*', '', line).strip() for line in block.strip().splitlines()]
        text = " ".join(l for l in lines if l)
        if text and "[Music" not in text and len(text) > 60:
            quotes.append(text)

    if not quotes:
        # Fallback: extract from TOC summary lines
        toc_lines = re.findall(r'\*"([^"]{60,}?)\.?\.\."?\*', content)
        quotes = [q.strip() for q in toc_lines if "[Music" not in q]

    if not quotes:
        print("  [WARN] Could not extract quotes from transcripts — using built-in examples.")
        quotes = _FALLBACK_EXAMPLES

    sample_size = min(n, len(quotes))
    return random.sample(quotes, sample_size)


_FALLBACK_EXAMPLES = [
    "If you see your friend with your enemy, be sure that both are your enemy. One openly, the other secretly. One walks beside you. The other walks behind you.",
    "The best decision I ever made was to be quiet. I have nothing to prove. I'm not here to impress anyone. Peace is my priority.",
    "Not everything deserves a reaction. Some things deserve your silence. You cannot pour from an empty cup. Protect your energy.",
    "Never search for your happiness in others. It will only make you feel alone. Find it in yourself. Then share it.",
    "I was silent, not blind. I kept my words to myself, but I saw everything and remembered more than you know.",
    "What's meant for you cannot pass you by. You are not late. You are not behind. You are exactly on time.",
    "I forgave, but I'm not sitting at that table again. Forgiveness doesn't mean you accept the behaviour. It means you chose your peace.",
    "The beautiful face will age and a perfect body will change. But a beautiful soul will always be beautiful.",
    "Most people are fighting battles you will never see. Be gentle with your words. Be patient with their silence.",
    "Do not beg to sit at tables you were never invited to. Know your worth. Walk away. Build your own table.",
    "Never ask a liar why they lied. To explain it, they would have to lie again. And they always do.",
    "Life is like a train station. People come and go. Some stay for a few stops. Others ride with you to the end.",
]


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def _build_prompt(examples: list[str], theme: str = "") -> str:
    examples_text = "\n".join(f'{i+1}. "{q}"' for i, q in enumerate(examples))
    theme_instruction = f"\nTheme focus: {theme}." if theme else ""

    return f"""You are a philosopher and spiritual writer for a mindfulness social media brand called "Whisprs".
Your task is to write ONE new original philosophical quote in the exact same voice, tone, and structure as the examples below.{theme_instruction}

STYLE RULES (follow strictly):
- 3 to 7 short clauses separated by commas or periods
- Each clause: 5–15 words, direct and punchy
- Tone: introspective, melancholic, wise, universal
- Person: "you", "I", or universal third-person
- NO rhyming forced
- NO hashtags, NO emojis, NO author attribution
- End with a powerful one-line conclusion
- Output ONLY the quote text. Nothing else.

REFERENCE EXAMPLES from the Whisprs dataset:
{examples_text}

Now write ONE new original quote in exactly this style. Output only the quote text:"""


# ---------------------------------------------------------------------------
# LLM Backends
# ---------------------------------------------------------------------------

def _generate_via_gemini(prompt: str) -> str | None:
    key = cfg.GEMINI_API_KEY
    if not key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg.QUOTE_MODEL_GEMINI}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 300,
            "topP": 0.95,
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code == 200:
            data = r.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    print(f"  [Gemini] Quote generated successfully.")
                    return text
        else:
            print(f"  [Gemini] Notice [{r.status_code}]: {r.text[:120]}")
    except Exception as e:
        print(f"  [Gemini] Exception: {e}")
    return None


def _generate_via_groq(prompt: str) -> str | None:
    key = cfg.GROQ_API_KEY
    if not key:
        print("  [Groq] GROQ_API_KEY not set — skipping Groq fallback.")
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": cfg.QUOTE_MODEL_GROQ,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 300,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                print(f"  [Groq Llama3-70B] Quote generated successfully.")
                return text
        else:
            print(f"  [Groq] Notice [{r.status_code}]: {r.text[:120]}")
    except Exception as e:
        print(f"  [Groq] Exception: {e}")
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_quote(theme: str = "") -> str:
    """
    Generates one original Whisprs-style philosophical quote.

    Tries Gemini Flash first, then Groq Llama 3 70B, then falls back
    to a random quote from the dataset if both APIs fail.

    Args:
        theme: Optional theme hint (e.g. "betrayal", "loneliness", "self-worth")

    Returns:
        Quote string.
    """
    print("\nLoading Whisprs dataset examples for few-shot prompting...")
    examples = load_dataset_quotes(n=cfg.QUOTE_FEW_SHOT_SAMPLES)
    print(f"  Loaded {len(examples)} reference quotes.")

    prompt = _build_prompt(examples, theme=theme)

    print("\nGenerating quote via Gemini Flash (primary)...")
    quote = _generate_via_gemini(prompt)

    if not quote:
        print("\nFalling back to Groq Llama 3 70B...")
        quote = _generate_via_groq(prompt)

    if not quote:
        print("\n  Both LLMs unavailable — using random dataset quote as fallback.")
        quote = random.choice(examples or _FALLBACK_EXAMPLES)

    # Clean up: strip surrounding quotes if LLM added them
    quote = quote.strip().strip('"').strip("'").strip()
    return quote


def log_quote(quote: str, metadata: dict = None):
    """
    Appends a generated quote + metadata to output_reels/quotes_log.jsonl.
    """
    log_path = os.path.join(cfg.OUTPUT_DIR, "quotes_log.jsonl")
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "quote": quote,
        **(metadata or {})
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  Logged quote to: {log_path}")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisprs Quote Generator")
    parser.add_argument("--count", type=int, default=1, help="Number of quotes to generate")
    parser.add_argument("--theme", type=str, default="", help="Optional theme (e.g. betrayal, loneliness)")
    parser.add_argument("--no-log", action="store_true", help="Don't log generated quotes")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  WHISPRS QUOTE ENGINE")
    print("="*55)

    for i in range(args.count):
        if args.count > 1:
            print(f"\n── Quote {i+1}/{args.count} ──")
        quote = generate_quote(theme=args.theme)
        print(f"\n📜 GENERATED QUOTE:\n\n  {quote}\n")
        if not args.no_log:
            log_quote(quote, {"theme": args.theme, "source": "llm_generated"})
