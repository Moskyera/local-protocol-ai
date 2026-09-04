#!/usr/bin/env python3
"""
Simple non-interactive verification for MOSKY voice prerequisites.
Run with the ai-env python from inside market-agent.
Does NOT require microphone or load the heavy models (lazy loaded).
"""
import sys
from pathlib import Path

print("=" * 60)
print("MOSKY VOICE PREREQUISITES VERIFICATION")
print("=" * 60)

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

print(f"\n[1] Python: {sys.executable}")
print(f"    Version: {sys.version.split()[0]}")

# Check packages
print("\n[2] Checking voice packages import...")
try:
    import faster_whisper
    import piper
    import sounddevice as sd
    import webrtcvad
    import numpy as np
    print("    ✅ faster-whisper, piper-tts, sounddevice, webrtcvad, numpy: OK")
except Exception as e:
    print(f"    ❌ FAILED: {e}")
    sys.exit(1)

# Import the voice module (this was previously failing hard with sys.exit)
print("\n[3] Importing automation_examples.voice_interface ...")
try:
    import automation_examples.voice_interface as vi
    print("    ✅ Module imported successfully (no hard exit on missing packages)")
except SystemExit as e:
    print(f"    ❌ Module did sys.exit (packages still missing?): {e}")
    sys.exit(1)
except Exception as e:
    print(f"    ❌ Other import error: {e}")
    sys.exit(1)

# Check config values
print("\n[4] Module configuration:")
print(f"    WHISPER_MODEL_SIZE = {getattr(vi, 'WHISPER_MODEL_SIZE', 'N/A')}")
print(f"    WHISPER_DEVICE     = {getattr(vi, 'WHISPER_DEVICE', 'N/A')}")
print(f"    PIPER_MODEL_PATH   = {getattr(vi, 'PIPER_MODEL_PATH', 'N/A')}")

# Check if the expected model file exists according to the module's logic
print("\n[5] Checking Piper Greek voice model files...")
piper_path = Path(vi.PIPER_MODEL_PATH)
print(f"    Expected: {piper_path}")

found = False
for p in getattr(vi, '_possible_piper_paths', []):
    p = Path(p)
    if p.exists() and p.stat().st_size > 10_000_000:  # at least 10MB for a real model
        print(f"    ✅ Found usable model: {p} ({p.stat().st_size // 1024} KB)")
        found = True
        break

if not found:
    # Direct check for the known good file
    known = Path.home() / ".piper" / "voices" / "el_GR-rapunzelina-low.onnx"
    if known.exists() and known.stat().st_size > 10_000_000:
        print(f"    ✅ Found known good model: {known} ({known.stat().st_size // 1024} KB)")
        found = True
    else:
        print(f"    ❌ No suitable Greek Piper model found yet.")
        print(f"       Run the voice-chat.bat or python download_piper_greek.py")

if found:
    print("    Model files look good for Piper TTS.")

# Check primary LLM (llama.cpp) + legacy Ollama (voice)
print("\n[6] Checking primary LLM (llama.cpp :8080) + legacy Ollama (voice fallback)...")
try:
    import urllib.request, json
    # Primary
    req = urllib.request.Request("http://localhost:8080/v1/models", headers={"Authorization": "Bearer sk-dummy-local"})
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))
        models = [m.get("id","") for m in data.get("data",[])]
        print(f"    ✅ Primary LLM responding on 8080. Models: {models[:2]}")
except Exception as e:
    print(f"    ⚠️ Primary LLM (8080) not reachable: {e}")

# Legacy
try:
    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
        data = r.read().decode("utf-8", errors="ignore")
        print("    ✅ Legacy Ollama responding on 11434 (voice only)")
except Exception as e:
    print(f"    ⚠️ Legacy Ollama not reachable: {e}")
    print("       Make sure start-ai.bat is running (primary backend recommended).")

print("\n" + "=" * 60)
if found:
    print("✅ CORE PREREQUISITES LOOK GOOD")
    print("   You can now try running voice-chat.bat in a separate window.")
    print("   Say 'γεια σου mosky' then 'αξιολόγηση' or 'τι νέο από github και x'.")
else:
    print("⚠️  Model still missing — run the bat or download script.")
print("=" * 60)