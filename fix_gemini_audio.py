import os
import sys
import wave
import subprocess
import imageio_ffmpeg

sys.stdout.reconfigure(encoding='utf-8')

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
samples_dir = os.path.join(_BASE_DIR, "output_reels", "gemini_voice_samples")


print("Converting Gemini raw PCM bytes into playable WAV & MP3 files...")

for file_name in os.listdir(samples_dir):
    if file_name.endswith(".mp3"):
        raw_path = os.path.join(samples_dir, file_name)
        base_name = file_name[:-4]
        
        with open(raw_path, "rb") as f:
            pcm_bytes = f.read()
            
        wav_path = os.path.join(samples_dir, f"{base_name}.wav")
        final_mp3_path = os.path.join(samples_dir, f"{base_name}_playable.mp3")
        
        # Write standard 24kHz 16-bit Mono WAV header
        with wave.open(wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(pcm_bytes)
            
        # Convert WAV to playable MP3 using ffmpeg
        cmd = [ffmpeg_exe, "-y", "-i", wav_path, "-acodec", "libmp3lame", "-ab", "192k", final_mp3_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Overwrite the original .mp3 file with the true playable MP3
        if os.path.exists(final_mp3_path):
            os.replace(final_mp3_path, raw_path)
            
        print(f"✅ Converted {file_name}: Playable WAV ({os.path.getsize(wav_path)} bytes) & MP3 ({os.path.getsize(raw_path)} bytes)")

print("\nAll Gemini audio samples converted to standard playable audio formats!")
