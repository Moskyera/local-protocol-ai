#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print("Python:", sys.executable)

print("\nTrying direct webrtcvad (may fail on pkg_resources in some setups):")
try:
    import webrtcvad
    print("✅ webrtcvad direct")
except Exception as e:
    print(f"❌ webrtcvad direct: {type(e).__name__}: {e}")

print("\nImporting automation_examples.voice_interface (this runs the pkg_resources shim first):")
try:
    import automation_examples.voice_interface as vi
    print("✅ automation_examples.voice_interface import SUCCESS")
    print("   WHISPER_DEVICE =", getattr(vi, "WHISPER_DEVICE", "N/A"))
    print("   PIPER_MODEL_PATH =", getattr(vi, "PIPER_MODEL_PATH", "N/A"))
except SystemExit as e:
    print(f"❌ voice_interface did sys.exit: {e}")
except Exception as e:
    print(f"❌ voice_interface: {type(e).__name__}: {e}")

print("\nDone.")