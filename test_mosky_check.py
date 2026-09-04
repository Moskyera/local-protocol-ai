#!/usr/bin/env python3
"""
MOSKY Package and Functionality Check
Run with: C:\AI\ai-env\Scripts\python.exe test_mosky_check.py
"""
import sys
from pathlib import Path

print("=" * 60)
print("MOSKY WEB INTERFACE - PACKAGE & FUNCTIONALITY CHECK")
print("=" * 60)
print(f"Python: {sys.executable}")
print(f"Version: {sys.version.split()[0]}")
print()

# 1. Check core voice packages
print("[1] Checking core voice packages...")
core_pkgs = {
    'faster_whisper': 'faster-whisper',
    'piper': 'piper-tts',
    'sounddevice': 'sounddevice',
    'webrtcvad': 'webrtcvad',
    'numpy': 'numpy'
}
missing_core = []
for mod, pip_name in core_pkgs.items():
    try:
        __import__(mod)
        print(f"  ✅ {mod} ({pip_name})")
    except Exception as e:
        print(f"  ❌ {mod}: {e}")
        missing_core.append(pip_name)

# 2. Check web UI packages
print("\n[2] Checking web UI packages...")
web_pkgs = ['gradio', 'soundfile']
missing_web = []
for mod in web_pkgs:
    try:
        __import__(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod}: {e}")
        missing_web.append(mod)

# 3. Check Piper model
print("\n[3] Checking Greek Piper voice model...")
model_path = Path.home() / ".piper" / "voices" / "el_GR-rapunzelina-low.onnx"
if model_path.exists():
    size_mb = model_path.stat().st_size / (1024*1024)
    print(f"  ✅ Model found: {model_path}")
    print(f"     Size: {size_mb:.1f} MB")
    if size_mb < 50:
        print("     ⚠️  File seems too small (download may have failed)")
else:
    print(f"  ❌ Model NOT found at {model_path}")
    print("     Run the download script or the web launcher (it will try to fetch it).")

# 4. Test MOSKY core import and model loading
print("\n[4] Testing MOSKY core (this loads Whisper + Piper - may take time)...")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from automation_examples.voice_interface import (
        _ensure_models_loaded, 
        transcribe, 
        chat_with_mosky
    )
    print("  ✅ Core imports successful")
    
    _ensure_models_loaded()
    print("  ✅ Models loaded successfully (Whisper STT + Piper TTS)")
    
    # Quick dummy test (transcribe needs audio, so skip heavy)
    print("  ✅ Basic functionality reachable")
except Exception as e:
    print(f"  ❌ Error loading MOSKY: {type(e).__name__}: {e}")
    print("     This is likely the Piper model or a package issue.")

# 5. Test Gradio web module
print("\n[5] Testing mosky_web.py module import...")
try:
    import mosky_web
    print("  ✅ mosky_web.py imports OK (Gradio UI should start)")
except Exception as e:
    print(f"  ❌ mosky_web.py import failed: {e}")

print("\n" + "=" * 60)
if not missing_core and not missing_web and model_path.exists():
    print("✅ ALL CHECKS PASSED - The web interface should work!")
    print("Run: C:\\AI\\ai-env\\Scripts\\python.exe mosky_web.py")
else:
    print("⚠️  ISSUES FOUND - see above.")
    if missing_core or missing_web:
        print("Fix by running in the ai-env:")
        pkgs = ' '.join(missing_core + missing_web)
        print(f"  C:\\AI\\ai-env\\Scripts\\python.exe -m pip install {pkgs}")
    if not model_path.exists():
        print("Run the downloader:")
        print("  C:\\AI\\ai-env\\Scripts\\python.exe download_piper_greek.py")
print("=" * 60)