import os
import sys
import requests
import base64

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\User\Projects\video_generation_pipeline")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\User\Projects\video_generation_pipeline\.env")

VOICE_ID = "hpp4J3VqNfWAUOO0d1Us"
API_KEY = os.environ.get("ELEVENLABS_API_KEY", "9127a2934475543838b3c08cf0511a4da65becddbac2a42dd80dbf81683c3bdf")

quote_text = (
    "In the quietest moments of your life, when the world stops rushing, "
    "you will finally hear the whisper of your own soul. "
    "Trust the journey, even when you cannot see the path ahead."
)

output_mp3 = r"c:\Users\User\Projects\video_generation_pipeline\output_reels\sample_storytelling_voice.mp3"
output_wav = r"c:\Users\User\Projects\video_generation_pipeline\output_reels\sample_storytelling_voice.wav"
os.makedirs(os.path.dirname(output_mp3), exist_ok=True)

print(f"Generating ElevenLabs storytelling voice sample...")
print(f"Voice ID: {VOICE_ID}")
print(f"Quote: \"{quote_text}\"\n")

url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps"
headers = {
    "Content-Type": "application/json",
    "xi-api-key": API_KEY
}
payload = {
    "text": quote_text,
    "model_id": "eleven_multilingual_v2",
    "voice_settings": {
        "stability": 0.55,
        "similarity_boost": 0.80,
        "style": 0.25,
        "use_speaker_boost": True
    }
}

try:
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        data = r.json()
        audio_bytes = base64.b64decode(data["audio_base64"])
        with open(output_mp3, "wb") as f:
            f.write(audio_bytes)
            
        import shutil
        shutil.copy(output_mp3, output_wav)
        
        import librosa
        y, sr = librosa.load(output_mp3, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        size_kb = os.path.getsize(output_mp3) / 1024.0
        
        print(f"ElevenLabs Voiceover Generation Successful!")
        print(f"  Saved MP3: {output_mp3}")
        print(f"  Saved WAV: {output_wav}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  File Size: {size_kb:.1f} KB")
    else:
        print(f"ElevenLabs API error [{r.status_code}]: {r.text}")
except Exception as e:
    print(f"Exception calling ElevenLabs API: {e}")
