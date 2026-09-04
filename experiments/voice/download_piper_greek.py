#!/usr/bin/env python3
"""Download Greek Piper voice model reliably using only stdlib."""
import os
import urllib.request
from pathlib import Path

print("=== Downloading Greek Piper TTS voice ===")
voices_dir = Path.home() / ".piper" / "voices"
voices_dir.mkdir(parents=True, exist_ok=True)
print(f"Target dir: {voices_dir}")
print("Note: If download fails here, the voice-chat.bat will warn you clearly.")

# Correct current path for Greek (el_GR / rapunzelina low) from the official piper-voices repo.
# Note: the original code used outdated "gr_GR-rapunzel-medium" which 404s.
base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/el/el_GR/rapunzelina/low/el_GR-rapunzelina-low"
files = [
    (f"{base_url}.onnx", "el_GR-rapunzelina-low.onnx"),
    (f"{base_url}.onnx.json", "el_GR-rapunzelina-low.onnx.json"),
]

success = True
for url, filename in files:
    dest = voices_dir / filename
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"Already present: {dest} ({dest.stat().st_size // 1024} KB)")
        continue
    print(f"Downloading {filename} ... (this may take a minute)")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as response:
            data = response.read()
        with open(dest, "wb") as f:
            f.write(data)
        print(f"  Saved {dest} ({len(data) // 1024} KB)")
    except Exception as e:
        print(f"  FAILED for {filename}: {e}")
        success = False

if success:
    onnx = voices_dir / "gr_GR-rapunzel-medium.onnx"
    if onnx.exists():
        print(f"\nSUCCESS: Greek Piper voice ready at {onnx}")
        print("You can also set env var PIPER_GREEK_VOICE to point to it if you move the file.")
else:
    print("\nSome downloads failed. You may need to manually download from https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/gr/gr_GR/rapunzel/medium")

print("Done.")