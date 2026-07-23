import sys
import os
import re
import time
import base64
import urllib.parse
import shutil
import subprocess
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Hand-drawn boil animation subtitle system
from subtitle_boil import create_animated_subtitle_clip, boil_animate_svg_asset, cleanup_boil_frames

# Ensure FFmpeg is in PATH
import imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_dir = os.path.dirname(ffmpeg_exe)
target_ffmpeg = os.path.join(ffmpeg_dir, "ffmpeg.exe")
if not os.path.exists(target_ffmpeg):
    try: shutil.copy(ffmpeg_exe, target_ffmpeg)
    except: pass
os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

import edge_tts
import librosa
from moviepy import ImageClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, concatenate_videoclips

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE_DIR = r"c:\Users\User\Projects\video_generation_pipeline"
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output_reels")
TEMP_DIR = os.path.join(WORKSPACE_DIR, "temp_build")

# Output video resolution — 9:16 Full HD vertical format
VIDEO_W = 1080
VIDEO_H = 1920

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

UNIFIED_STYLE = "retro 90s anime style illustration, Studio Ghibli aesthetic, dark muted color palette, atmospheric low-key lighting, film grain noise texture, detailed line art, melancholic lofi mood, vertical 9:16 aspect ratio"

DEFAULT_QUOTE = "If you see your friend with your enemy, be sure that both are your enemy. One openly, the other secretly. One walks beside you. The other walks behind you. Time will show you which one was which. But by then, the damage is done."

# API Keys
DEFAULT_GEMINI_API_KEY = ""
DEFAULT_ELEVENLABS_API_KEY = ""

# Voice priority for ElevenLabs Fallback
ELEVENLABS_VOICES = [
    ("PB6BdkFkZLbI39GHdnbQ", "User Selected Voice (PB6BdkFkZLbI39GHdnbQ)"),
    ("xrNwYO0xeioXswMCcFNF", "Ingmar - Intimately Mysterious"),
    ("N2lVS1w4EtoT3dr4eOWO", "Callum - Deep Breathy Husky Whisper"),
    ("SAz9YHcvj6GT2YYXdXww", "River - Soft Calm & Relaxed"),
    ("EXAVITQu4vr4xnSDxMaL", "Sarah - Soft Reassuring Whisper"),
    ("JBFqnCBsd6RMkjVDRZzb", "George - Captivating Meditative Storyteller")
]

def generate_full_audio_gemini_tts(quote_text, output_audio, api_key):
    """
    Generates high quality spiritual audio using Google Gemini 3.1 Flash TTS (Preview) with voice 'Algenib'.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent?key={api_key}"
    style_instruction = "Sensual Hypnosis - Sensual, Seductive, Gentle, Spiritual, Charming voice. Suitable for ASMR, Guided Meditation and Hypnosis Inductions. Self realizing tone, with breadth between clauses"
    
    full_prompt = f"Please read this quote following this style instruction: ({style_instruction}).\n\nQuote: {quote_text}"
    
    payload = {
        "contents": [
            {"parts": [{"text": full_prompt}]}
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Algenib"
                    }
                }
            }
        }
    }
    
    print(f"Calling Google Gemini 3.1 Flash TTS API (Voice: Algenib)...")
    try:
        r = requests.post(url, json=payload, timeout=45)
        if r.status_code == 200:
            data = r.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for p in parts:
                    if "inlineData" in p:
                        b64_data = p["inlineData"]["data"]
                        raw_pcm = base64.b64decode(b64_data)
                        
                        import wave
                        wav_path = output_audio.replace(".mp3", ".wav")
                        with wave.open(wav_path, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(24000)
                            wf.writeframes(raw_pcm)
                        print(f"Successfully generated Google Gemini 3.1 Flash TTS voiceover (Algenib): {wav_path}")
                        return wav_path
        else:
            print(f"  Gemini TTS Notice [{r.status_code}]: {r.text[:150]}")
    except Exception as e:
        print(f"  Gemini TTS Request Exception: {e}")
        
    return None

def format_text_for_spiritual_pace(quote_text):
    """
    Returns pure, untouched quote text without any added markers or symbols.
    """
    return quote_text.strip()

def generate_full_audio_elevenlabs(quote_text, output_mp3, api_key):
    """
    Generates full-quote audio & exact timestamps using ElevenLabs Text-to-Speech API with clean voice settings.
    """
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    clean_quote = format_text_for_spiritual_pace(quote_text)
    
    for voice_id, voice_name in ELEVENLABS_VOICES:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/with-timestamps"
        payload = {
            "text": clean_quote,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.55,          # Standard stable, natural tone
                "similarity_boost": 0.75,    # High clarity
                "style": 0.20,               # Clean subtle emotion
                "use_speaker_boost": True
            }
        }
        
        print(f"Calling ElevenLabs API (Spiritual Whisper Voice: {voice_name} [{voice_id}])...")
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                audio_bytes = base64.b64decode(data["audio_base64"])
                with open(output_mp3, "wb") as f:
                    f.write(audio_bytes)
                print(f"Successfully generated ElevenLabs voiceover ({voice_name}):", output_mp3)
                alignment = data.get("alignment")
                return output_mp3, alignment
            else:
                print(f"  ElevenLabs Notice [{r.status_code}] for {voice_name}: {r.text[:120]}...")
        except Exception as e:
            print(f"  ElevenLabs Request Exception: {e}")
            
    return None, None

def generate_background_sound_elevenlabs(output_mp3, duration_sec, api_key):
    """
    Generates custom soft spiritual meditative lofi ambient sound effect using ElevenLabs Sound Effects API.
    """
    url = "https://api.elevenlabs.io/v1/sound-generation"
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    payload = {
        "text": "soft spiritual meditative lofi ambient background sound, peaceful atmospheric singing bowl drone, deep relaxation tone",
        "duration_seconds": min(max(int(duration_sec), 5), 22),
        "prompt_influence": 0.45
    }
    
    print(f"Generating ElevenLabs Spiritual Ambient Background Sound ({payload['duration_seconds']}s)...")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(output_mp3, "wb") as f:
                f.write(r.content)
            print("Successfully generated ElevenLabs spiritual ambient sound effect:", output_mp3)
            return output_mp3
        else:
            print(f"ElevenLabs Sound Gen Notice [{r.status_code}]: {r.text[:120]}")
    except Exception as e:
        print(f"Sound Gen Exception: {e}")
    return None

def generate_full_audio_edgetts(quote_text, output_mp3):
    """
    Fallback: Generates full-quote audio using edge-tts with slow, deep whisper pitch.
    """
    import asyncio
    async def _gen():
        voice = "en-US-ChristopherNeural"
        communicate = edge_tts.Communicate(quote_text, voice, rate="-25%", pitch="-6Hz")
        await communicate.save(output_mp3)
    asyncio.run(_gen())
    print("Generated Edge-TTS spiritual fallback voiceover:", output_mp3)
    return output_mp3

def parse_quote_into_clauses(quote_text):
    """
    Splits a quote into individual clauses based on punctuation.
    Assigns extended silence delays for spiritual, satisfying pacing:
    - Commas/semicolons: 1.2s delay
    - Periods/exclamations: 2.0s delay
    """
    raw_clauses = re.split(r'([,\.\;\!\?])', quote_text)
    clauses = []
    current_text = ""
    for token in raw_clauses:
        if token in [',', ';']:
            if current_text.strip():
                clauses.append({"text": current_text.strip(), "delay": 1.2, "punctuation": token})
                current_text = ""
        elif token in ['.', '!', '?']:
            if current_text.strip():
                clauses.append({"text": current_text.strip(), "delay": 2.0, "punctuation": token})
                current_text = ""
        else:
            current_text += token
    if current_text.strip():
        clauses.append({"text": current_text.strip(), "delay": 1.8, "punctuation": "."})
    return clauses

def align_clauses_with_elevenlabs_alignment(quote_text, clauses, alignment, total_duration):
    """
    Uses ElevenLabs character-level timestamp alignment for exact clause timing.
    Adjusts boundaries with satisfying inter-clause pause buffers.
    """
    print("\nUsing ElevenLabs Forced Alignment (Spiritual Character Timestamps)...")
    chars = alignment.get("characters", [])
    starts = alignment.get("character_start_times_seconds", [])
    ends = alignment.get("character_end_times_seconds", [])
    
    if not chars or not starts:
        return None
        
    full_str = "".join(chars)
    segments = []
    
    search_pos = 0
    for idx, clause in enumerate(clauses):
        c_text = clause["text"]
        start_char_idx = full_str.find(c_text, search_pos)
        if start_char_idx == -1:
            clean_c = re.sub(r'[^\w]', '', c_text)
            clean_full = re.sub(r'[^\w]', '', full_str)
            start_char_idx = search_pos
            
        end_char_idx = min(start_char_idx + len(c_text) - 1, len(starts) - 1)
        
        start_t = round(starts[start_char_idx], 3)
        end_t = round(ends[end_char_idx], 3)
        
        search_pos = end_char_idx + 1
        segments.append({
            "text": c_text,
            "start": start_t,
            "end": end_t,
            "duration": round(end_t - start_t, 3)
        })
        
    # Adjust contiguous segment boundaries to allow lingering visual pauses between clauses
    for i in range(len(segments) - 1):
        segments[i]["end"] = segments[i+1]["start"]
        segments[i]["duration"] = round(segments[i]["end"] - segments[i]["start"], 3)
    if segments:
        segments[-1]["end"] = total_duration
        segments[-1]["duration"] = round(total_duration - segments[-1]["start"], 3)

    print(f"  Aligned {len(segments)} spiritual clauses to timestamps:")
    for s in segments:
        print(f"    [{s['start']:.3f}s -> {s['end']:.3f}s] ({s['duration']:.2f}s): '{s['text']}'")
        
    return segments

def align_clauses_with_whisper(audio_mp3_path, clauses):
    """
    Forced Alignment using OpenAI Whisper Word-Level Timestamps.
    Maps actual spoken words directly to exact clause start & end timestamps.
    Ignores mid-sentence pauses, human breath gaps, or style variations.
    """
    print("\nRunning OpenAI Whisper Word-Level Forced Alignment...")
    try:
        import whisper
        y, sr = librosa.load(audio_mp3_path, sr=None)
        total_duration = float(librosa.get_duration(y=y, sr=sr))
        
        model = whisper.load_model("tiny")
        res = model.transcribe(audio_mp3_path, word_timestamps=True)
        
        all_words = []
        for s in res.get('segments', []):
            for w in s.get('words', []):
                clean_w = re.sub(r'[^\w]', '', w['word']).lower()
                if clean_w:
                    all_words.append({'word': clean_w, 'start': round(w['start'], 3), 'end': round(w['end'], 3)})
                    
        search_idx = 0
        segments = []
        
        for c in clauses:
            c_text = c["text"]
            c_words = [re.sub(r'[^\w]', '', w).lower() for w in c_text.split() if re.sub(r'[^\w]', '', w)]
            if not c_words:
                continue
                
            start_t = None
            end_t = None
            
            for i in range(search_idx, len(all_words)):
                if all_words[i]['word'] == c_words[0]:
                    start_t = all_words[i]['start']
                    match_count = 1
                    last_idx = i
                    for j in range(1, len(c_words)):
                        if i + j < len(all_words) and all_words[i+j]['word'] == c_words[j]:
                            match_count += 1
                            last_idx = i + j
                    end_t = all_words[last_idx]['end']
                    search_idx = last_idx + 1
                    break
                    
            if start_t is not None and end_t is not None:
                segments.append({'text': c_text, 'start': start_t, 'end': end_t, 'duration': round(end_t - start_t, 3)})
                
        if segments:
            for i in range(len(segments) - 1):
                segments[i]["end"] = segments[i+1]["start"]
                segments[i]["duration"] = round(segments[i]["end"] - segments[i]["start"], 3)
            segments[-1]["end"] = total_duration
            segments[-1]["duration"] = round(total_duration - segments[-1]["start"], 3)
            
            print(f"  Aligned {len(segments)} clauses using Whisper word timestamps:")
            for s in segments:
                print(f"    [{s['start']:.3f}s -> {s['end']:.3f}s] ({s['duration']:.2f}s): '{s['text']}'")
            return segments, total_duration
    except Exception as e:
        print(f"  Whisper alignment notice: {e}")
        
    return None, 0.0

def align_clauses_to_audio(audio_mp3_path, clauses):
    """
    Fallback: Forced Alignment using Audio Energy (RMS) Silence Detection.
    """
    print("\nRunning Silence-Gap Forced Alignment (librosa RMS energy)...")
    
    y, sr = librosa.load(audio_mp3_path, sr=None)
    total_duration = librosa.get_duration(y=y, sr=sr)
    
    frame_length = 2048
    hop_length = 512
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    
    rms_max = rms.max()
    rms_norm = rms / rms_max if rms_max > 0 else rms
    
    silence_threshold = 0.08
    min_silence_frames = int(0.12 * sr / hop_length)
    
    is_speech = rms_norm > silence_threshold
    
    onsets_frames = []
    in_silence = True
    silence_len = 0
    
    for i, speaking in enumerate(is_speech):
        if not speaking:
            in_silence = True
            silence_len += 1
        else:
            if in_silence and silence_len >= min_silence_frames:
                onsets_frames.append(i)
            in_silence = False
            silence_len = 0
    
    if is_speech[0] and (not onsets_frames or onsets_frames[0] > 5):
        onsets_frames.insert(0, 0)
    
    onset_times = librosa.frames_to_time(onsets_frames, sr=sr, hop_length=hop_length)
    
    n_clauses = len(clauses)
    n_onsets = len(onset_times)
    
    if n_onsets >= n_clauses:
        matched_onsets = list(onset_times[:n_clauses])
    else:
        matched_onsets = list(onset_times)
        gap_start = onset_times[-1] if onset_times else 0.0
        remaining = n_clauses - n_onsets
        step = (total_duration - gap_start) / (remaining + 1)
        for k in range(1, remaining + 1):
            matched_onsets.append(gap_start + k * step)
    
    segments = []
    for i, clause in enumerate(clauses):
        start_t = matched_onsets[i]
        end_t = matched_onsets[i + 1] if i + 1 < len(matched_onsets) else total_duration
        
        segments.append({
            "text": clause["text"],
            "start": round(start_t, 3),
            "end": round(end_t, 3),
            "duration": round(end_t - start_t, 3)
        })
        
    print(f"  Aligned {n_clauses} clauses to timestamps:")
    for s in segments:
        print(f"    [{s['start']:.3f}s -> {s['end']:.3f}s] ({s['duration']:.2f}s): '{s['text']}'")
        
    return segments, total_duration

def generate_clause_image_prompts_gemini(clauses, api_key):
    """
    Calls Gemini to generate high-quality visual image prompts for each clause.
    Returns a list of prompt strings of the same length as clauses.
    """
    import json
    
    clauses_list_str = "\n".join(f"{idx+1}. \"{c['text']}\"" for idx, c in enumerate(clauses))
    
    prompt = f"""You are a creative visual designer. We have a list of text clauses from a melancholic quote. 
For each clause, write a highly descriptive and specific visual scene description (1-2 sentences) to be used as an image generation prompt. The scene should metaphorically or literally capture the mood and meaning of the text. Focus on characters, expressions, actions, environment, lighting, and objects.
Do not include style keywords like "90s anime style", "Ghibli", or aspect ratios in the description itself, as a unified style suffix will be appended later.

Input clauses:
{clauses_list_str}

Return your response as a JSON array of strings, where each element is the image prompt for the clause at that index. Do not add any markdown formatting (like ```json) outside the JSON. Return only valid JSON."""

    # Using gemini-flash-latest as configured in config.py
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.7,
            "maxOutputTokens": 1000
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
                prompts = json.loads(text)
                if isinstance(prompts, list) and len(prompts) == len(clauses):
                    return prompts
        else:
            print(f"    Gemini Prompts API Notice [{r.status_code}]: {r.text[:120]}")
    except Exception as e:
        print(f"    Gemini Prompts Exception: {e}")
        
    return None

def generate_clause_image_prompts_groq(clauses, api_key):
    """
    Calls Groq to generate high-quality visual image prompts for each clause as a fallback.
    """
    import json
    
    clauses_list_str = "\n".join(f"{idx+1}. \"{c['text']}\"" for idx, c in enumerate(clauses))
    
    prompt = f"""You are a creative visual designer. We have a list of text clauses from a melancholic quote. 
For each clause, write a highly descriptive and specific visual scene description (1-2 sentences) to be used as an image generation prompt. The scene should metaphorically or literally capture the mood and meaning of the text. Focus on characters, expressions, actions, environment, lighting, and objects.
Do not include style keywords like "90s anime style", "Ghibli", or aspect ratios in the description itself, as a unified style suffix will be appended later.

Input clauses:
{clauses_list_str}

Return your response as a JSON array of strings, where each element is the image prompt for the clause at that index. Do not add any markdown formatting (like ```json) outside the JSON. Return only valid JSON."""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            match = re.search(r'\[\s*".*"\s*\]', text, re.DOTALL)
            if match:
                text = match.group(0)
            prompts = json.loads(text)
            if isinstance(prompts, list) and len(prompts) == len(clauses):
                return prompts
    except Exception as e:
        print(f"    Groq Prompts Exception: {e}")
        
    return None

def generate_clause_image(clause_text, output_jpg):
    if os.path.exists(output_jpg) and os.path.getsize(output_jpg) > 5000:
        return output_jpg

    # Primary: Pollinations FLUX Model (Native 1080x1920 vertical 9:16 format)
    clean_text = re.sub(r'[^\w\s]', '', clause_text)
    prompt = f"{clean_text}, {UNIFIED_STYLE}"
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&model=flux&nologo=true"
    
    for attempt in range(4):
        try:
            print(f"    Generating image via FLUX model (attempt {attempt+1})...")
            r = requests.get(url, timeout=25)
            if r.status_code == 200:
                with open(output_jpg, "wb") as f:
                    f.write(r.content)
                print(f"    Successfully generated image via FLUX model.")
                return output_jpg
        except Exception as e:
            print(f"    FLUX model attempt {attempt+1} notice: {e}")
            time.sleep(1.5)
            
    return None

def create_cinematic_motion_clip(image_path, duration, output_size=(VIDEO_W, VIDEO_H), style_idx=0):
    """
    Converts a static image into a dynamic 1080x1920 Full HD video clip 
    with cinematic camera movement (Zoom-In, Slow Pan, Reveal, and Floating Tilt).
    100% Free, native resolution, zero external API costs.
    """
    from PIL import Image
    import numpy as np
    from moviepy import VideoClip

    pil_img = Image.open(image_path).convert("RGB")
    oversize_w = int(output_size[0] * 1.25)
    oversize_h = int(output_size[1] * 1.25)
    img_arr = np.array(pil_img.resize((oversize_w, oversize_h), Image.LANCZOS))

    out_w, out_h = output_size
    mode = style_idx % 3  # Rotate through 3 camera motion modes

    def make_frame(t):
        progress = max(0.0, min(1.0, t / max(0.1, duration)))
        ease = np.sin(progress * np.pi / 2)

        if mode == 0:
            # Mode 0: Smooth Zoom-In + Micro Float
            zoom = 1.0 + 0.14 * ease
            crop_w, crop_h = int(out_w * zoom), int(out_h * zoom)
            cx = (oversize_w - crop_w) / 2 + 15 * np.sin(progress * np.pi * 2)
            cy = (oversize_h - crop_h) / 2 + 10 * np.cos(progress * np.pi * 2)

        elif mode == 1:
            # Mode 1: Pan Left to Right + Slight Zoom
            zoom = 1.05 + 0.05 * ease
            crop_w, crop_h = int(out_w * zoom), int(out_h * zoom)
            cx = (oversize_w - crop_w) * progress
            cy = (oversize_h - crop_h) / 2

        else:
            # Mode 2: Slow Reveal / Zoom-Out
            zoom = 1.15 - 0.12 * ease
            crop_w, crop_h = int(out_w * zoom), int(out_h * zoom)
            cx = (oversize_w - crop_w) / 2
            cy = (oversize_h - crop_h) * (1 - ease)

        x1 = max(0, min(oversize_w - crop_w, int(cx)))
        y1 = max(0, min(oversize_h - crop_h, int(cy)))
        x2 = min(oversize_w, x1 + crop_w)
        y2 = min(oversize_h, y1 + crop_h)

        cropped = img_arr[y1:y2, x1:x2]
        frame = Image.fromarray(cropped).resize(output_size, Image.LANCZOS)
        return np.array(frame)

    return VideoClip(make_frame, duration=duration)

def create_subtitle_image(text, output_png, width=720, height=1280):
    """
    Legacy static PIL subtitle renderer — kept as debug fallback.
    The main pipeline now uses create_animated_subtitle_clip() from subtitle_boil.py
    which renders the Indie Flower font with frame-by-frame boil animation.
    """
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    font_size = 36
    font_path = os.path.join(WORKSPACE_DIR, "fonts", "IndieFlower-Regular.ttf")
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        
        if line_w <= width - 160:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    full_text = "\n".join(lines)
    
    bbox = draw.multiline_textbbox((0, 0), full_text, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (width - text_w) // 2
    y = (height - text_h) // 2 + 100
    
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx != 0 or dy != 0:
                draw.multiline_text((x + dx, y + dy), full_text, font=font, fill=(0, 0, 0, 240), align="center")
                
    draw.multiline_text((x, y), full_text, font=font, fill=(255, 255, 255, 255), align="center")
    img.save(output_png, "PNG")
    return output_png

def generate_full_reel(quote_text=DEFAULT_QUOTE):
    print(f"\n=======================================================")
    print(f"STARTING REEL GENERATION (SPIRITUAL WHISPER + Extended Pauses)")
    print(f"=======================================================\n")
    print("Quote Input:\n", quote_text)
    
    # Clean temp build directory before new reel generation
    for f in os.listdir(TEMP_DIR):
        f_path = os.path.join(TEMP_DIR, f)
        if os.path.isfile(f_path):
            try: os.remove(f_path)
            except: pass
            
    master_audio_file = os.path.join(TEMP_DIR, "master_narration.mp3")
    bg_sound_file = os.path.join(TEMP_DIR, "bg_ambient.mp3")
    
    gemini_key = os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_API_KEY)
    eleven_key = os.environ.get("ELEVENLABS_API_KEY", DEFAULT_ELEVENLABS_API_KEY)
    
    alignment_data = None
    audio_result = None
    
    # Primary TTS: Google Gemini 3.1 Flash TTS (Preview) - Voice Algenib with Sensual Hypnosis Style
    if gemini_key:
        audio_result = generate_full_audio_gemini_tts(quote_text, master_audio_file, gemini_key)
        if audio_result and os.path.exists(audio_result):
            master_audio_file = audio_result
            
    # Fallback 1: ElevenLabs API
    if not audio_result and eleven_key:
        audio_result, alignment_data = generate_full_audio_elevenlabs(quote_text, master_audio_file, eleven_key)
        
    # Fallback 2: Edge-TTS
    if not audio_result:
        print("Using Edge-TTS fallback...")
        generate_full_audio_edgetts(quote_text, master_audio_file)
        
    clauses = parse_quote_into_clauses(quote_text)
    print(f"\nParsed {len(clauses)} clauses from quote.")
    
    # Calculate audio duration
    y, sr = librosa.load(master_audio_file, sr=None)
    total_audio_duration = float(librosa.get_duration(y=y, sr=sr))
    
    # Align clauses using OpenAI Whisper Word-Level Timestamps (Primary), ElevenLabs API, or RMS Energy Fallback
    segments = None
    try:
        segments, total_audio_duration = align_clauses_with_whisper(master_audio_file, clauses)
    except Exception as e:
        print(f"Whisper alignment notice: {e}")
        segments = None
        
    if not segments and alignment_data:
        try:
            segments = align_clauses_with_elevenlabs_alignment(quote_text, clauses, alignment_data, total_audio_duration)
        except Exception as e:
            print(f"ElevenLabs timestamp alignment notice: {e}")
            segments = None
            
    if not segments:
        segments, total_audio_duration = align_clauses_to_audio(master_audio_file, clauses)
        
    # Generate ElevenLabs Soft Spiritual Ambient Sound Effect for depth
    bg_audio_clip = None
    if eleven_key:
        sound_res = generate_background_sound_elevenlabs(bg_sound_file, total_audio_duration, eleven_key)
        if sound_res and os.path.exists(sound_res):
            try:
                bg_audio = AudioFileClip(bg_sound_file)
                if bg_audio.duration < total_audio_duration:
                    bg_audio = bg_audio.with_duration(total_audio_duration)
                # Lower volume to 15% so whisper narration remains crisp, peaceful, and prominent
                bg_audio_clip = bg_audio.with_effects([lambda clip: clip.with_volume_scaling(0.15)]).with_duration(total_audio_duration)
            except Exception as e:
                print(f"Background audio blend note: {e}")

    # Build Master Audio Stream
    voice_clip = AudioFileClip(master_audio_file)
    if bg_audio_clip:
        final_audio = CompositeAudioClip([voice_clip, bg_audio_clip])
    else:
        final_audio = voice_clip

    # Generate descriptive visual prompts for each clause using Gemini/Groq
    print("\nGenerating descriptive visual prompts for each clause using Gemini/Groq...")
    visual_prompts = None
    if gemini_key:
        visual_prompts = generate_clause_image_prompts_gemini(clauses, gemini_key)
    if not visual_prompts and os.environ.get("GROQ_API_KEY"):
        visual_prompts = generate_clause_image_prompts_groq(clauses, os.environ.get("GROQ_API_KEY"))
    
    # Build a lookup mapping from clause text to visual prompt to handle any length mismatch safely
    clause_to_prompt = {}
    if visual_prompts and len(visual_prompts) == len(clauses):
        print("    Successfully generated descriptive visual prompts for all clauses!")
        for idx, vp in enumerate(visual_prompts):
            clause_to_prompt[clauses[idx]["text"]] = vp
            print(f"      - Clause {idx+1}: '{clauses[idx]['text']}' -> Prompt: '{vp}'")
    else:
        print("    Fallback: Using raw clause text for image prompts.")
        for c in clauses:
            clause_to_prompt[c["text"]] = c["text"]

    # Build Synchronized Video Clips for Each Aligned Segment
    clips = []
    for idx, seg in enumerate(segments):
        text = seg["text"]
        start_t = seg["start"]
        end_t = seg["end"]
        
        if idx == len(segments) - 1:
            end_t = max(end_t, total_audio_duration)
            
        dur = end_t - start_t
        if dur <= 0:
            continue
            
        image_file = os.path.join(TEMP_DIR, f"whisper_img_{idx}.jpg")
        boil_frames_dir = os.path.join(TEMP_DIR, f"boil_sub_{idx}")
        
        visual_prompt = clause_to_prompt.get(text, text)
        print(f"\nProcessing Segment {idx+1}/{len(segments)} [{start_t:.2f}s -> {end_t:.2f}s, dur: {dur:.2f}s]:")
        print(f"  - Generating Image with prompt: '{visual_prompt}'...")
        generate_clause_image(visual_prompt, image_file)
        
        print(f"  - Creating Boil Animated Subtitle...")
        font_path = os.path.join(WORKSPACE_DIR, "fonts", "IndieFlower-Regular.ttf")
        try:
            sub_clip = create_animated_subtitle_clip(
                text=text,
                duration=dur,
                font_path=font_path,
                canvas_w=1080,
                canvas_h=1920,
                output_temp_dir=boil_frames_dir,
            )
        except Exception as e:
            print(f"  - Boil subtitle error ({e}), using static fallback...")
            sub_file = os.path.join(TEMP_DIR, f"whisper_sub_{idx}.png")
            create_subtitle_image(text, sub_file)
            sub_clip = ImageClip(sub_file).with_duration(dur)
        
        # Load background image resized to 1080x1920 canvas
        bg_img = Image.open(image_file).convert("RGB")
        if bg_img.size != (VIDEO_W, VIDEO_H):
            bg_img = bg_img.resize((VIDEO_W, VIDEO_H), Image.LANCZOS)
        bg_arr = np.array(bg_img)
        img_clip = ImageClip(bg_arr).with_duration(dur)

        video_clip = CompositeVideoClip(
            [img_clip, sub_clip],
            size=(VIDEO_W, VIDEO_H)
        ).with_duration(dur)
        clips.append(video_clip)
        
    print("\nConcatenating synchronized video clips into master video stream...")
    final_video = concatenate_videoclips(clips, method="compose")

    # Add Scratch & Dust Noise Overlay using Premiere Pro Lighten Blend Mode
    noise_path = os.path.join(WORKSPACE_DIR, "overlay_video_footages", "scratch_noise_02.mp4")
    if os.path.exists(noise_path):
        print(f"\nAdding Scratch & Dust overlay ({os.path.basename(noise_path)}) with Lighten blend mode...")
        try:
            from moviepy import VideoFileClip, vfx
            noise_clip = VideoFileClip(noise_path)
            # Rotate 90 degrees (1920x1080 -> 1080x1920 vertical format)
            noise_clip = noise_clip.with_effects([vfx.Rotate(90)])
            # Loop/crop overlay to match full video duration
            if noise_clip.duration < final_video.duration:
                n_repeats = int(np.ceil(final_video.duration / noise_clip.duration))
                noise_clip = concatenate_videoclips([noise_clip] * n_repeats).subclipped(0, final_video.duration)
            else:
                noise_clip = noise_clip.subclipped(0, final_video.duration)

            # Premiere Pro Lighten Blend Mode: np.maximum(base_pixel, noise_pixel)
            final_video = final_video.transform(
                lambda get_frame, t: np.maximum(get_frame(t), noise_clip.get_frame(t))
            )
            print("  - Lighten blend mode overlay composited successfully.")
        except Exception as e:
            print(f"  - Noise overlay notice ({e}), rendering without overlay.")

    final_video = final_video.with_audio(final_audio)
    
    output_path = os.path.join(OUTPUT_DIR, f"reel_spiritual_{int(time.time())}.mp4")
    print(f"\nRendering final MP4 to: {output_path}...")
    
    final_video.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac"
    )
    
    print(f"\n=======================================================")
    print(f"SUCCESS! Spiritual Reel saved to: {output_path}")
    print(f"=======================================================\n")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom_quote = " ".join(sys.argv[1:])
        generate_full_reel(custom_quote)
    else:
        generate_full_reel()
