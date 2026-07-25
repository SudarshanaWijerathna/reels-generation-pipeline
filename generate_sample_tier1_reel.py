import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"c:\Users\User\Projects\video_generation_pipeline")

paid_api_key = os.getenv("GEMINI_API_KEY", "")
if paid_api_key:
    os.environ["GEMINI_API_KEY"] = paid_api_key


from generate_reel import generate_full_reel

quote = (
    "Never ask a liar why they lied. To explain it, they would have to lie again. "
    "One lie is never born alone. It always needs another to keep alive. "
    "Then another to protect the last. Until even they forget where the truth ended. "
    "And the lie becomes the only story they remember."
)

print("🎬 Generating High-RPM Tier-1 Sample Reel Video...")
print(f"Quote: \"{quote}\"\n")

output_mp4 = generate_full_reel(quote_text=quote, reuse_assets=True)

if output_mp4 and os.path.exists(output_mp4):
    size_mb = os.path.getsize(output_mp4) / (1024.0 * 1024.0)
    print(f"\n🎉 Reel Video Successfully Generated!")
    print(f"  File Path: {output_mp4}")
    print(f"  File Size: {size_mb:.2f} MB")
else:
    print("\n❌ Reel video generation failed.")
