import os
import sys
import wave
import requests
import base64
import subprocess
import imageio_ffmpeg

sys.stdout.reconfigure(encoding='utf-8')

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
paid_api_key = os.getenv("GEMINI_API_KEY", "")


prompt_instruction = "You have a bit calm, mind relaxing voice. Say the following in a bit poetic and story telling way"

text_with_brackets = (
    "[soft breath] Never ask a liar why they lied. [sigh] To explain it, they would have to lie again. "
    "[soft breath] One lie is never born alone. It always needs another to keep alive. "
    "[sigh] Then another to protect the last. Until even they forget where the truth ended. "
    "[soft breath] And the lie becomes the only story they remember."
)

voices_to_test = [
    ("Algenib", "Calm meditative male/neutral"),
    ("Aoede", "Warm poetic female"),
    ("Puck", "Poetic storytelling male"),
    ("Kore", "Serene soothing female")
]

output_dir = r"c:\Users\User\Projects\video_generation_pipeline\output_reels\gemini_poetic_samples"
os.makedirs(output_dir, exist_ok=True)

print("🎙️ Generating Poetic Storytelling Voices with Bracketed Breathing Cues...")
print(f"Instruction: \"{prompt_instruction}\"")
print(f"Text with Cues: \"{text_with_brackets}\"\n")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={paid_api_key}"

for voice_name, voice_desc in voices_to_test:
    print(f"Generating voice: {voice_name} ({voice_desc})...")
    
    full_prompt = f"{prompt_instruction}:\n\n{text_with_brackets}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": full_prompt
            }]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        }
    }

    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=45)
        if r.status_code == 200:
            data = r.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    inline_data = part.get("inlineData", {})
                    audio_b64 = inline_data.get("data")
                    if audio_b64:
                        pcm_bytes = base64.b64decode(audio_b64)
                        
                        base_filename = f"poetic_{voice_name.lower()}"
                        wav_path = os.path.join(output_dir, f"{base_filename}.wav")
                        mp3_path = os.path.join(output_dir, f"{base_filename}.mp3")
                        
                        # Write 24kHz 16-bit Mono WAV
                        with wave.open(wav_path, "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(24000)
                            wf.writeframes(pcm_bytes)
                            
                        # Convert to MP3
                        cmd = [ffmpeg_exe, "-y", "-i", wav_path, "-acodec", "libmp3lame", "-ab", "192k", mp3_path]
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        import librosa
                        y, sr = librosa.load(wav_path, sr=None)
                        dur = librosa.get_duration(y=y, sr=sr)
                        
                        print(f"  [SUCCESS] {voice_name}: Duration {dur:.2f}s | WAV ({os.path.getsize(wav_path)}B) | MP3 ({os.path.getsize(mp3_path)}B)")
                        break
        else:
            print(f"  [NOTICE {r.status_code}]: {r.text[:150]}")
    except Exception as e:
        print(f"  [EXCEPTION]: {e}")

print("\nAll poetic storytelling audio samples generated and converted!")
