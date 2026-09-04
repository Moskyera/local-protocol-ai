#!/usr/bin/env python3
"""
MOSKY Voice Launcher (recommended way, no .bat headaches)

HOW TO RUN (simple):
1. Make sure start-ai.bat is running and everything is ONLINE (primary LLM on :8080 preferred).
2. Run this file with the project ai-env Python:

   C:\AI\ai-env\Scripts\python.exe launch_mosky.py

   (You can make a desktop shortcut to this exact command, or
    right-click the .py file in Explorer → Open with → choose that python.exe)

It will:
- Check that you are using the correct Python (with the voice packages)
- Download the Greek Piper voice model if missing (el_GR-rapunzelina-low)
- Do a quick Ollama check
- Speak "Έτοιμος, πες γεια σου mosky." immediately
- Start listening for the wake word

Requirements:
- The ai-env must have the packages (the bat used to install them).
- Internet for first-time model download (if not already present).
"""

import sys
import os
import time
import urllib.request
from pathlib import Path

# Make sure we can import project modules
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def check_correct_python():
    exe = sys.executable.lower()
    if "ai-env" not in exe:
        print("ERROR: You are not running with the project ai-env Python.")
        print("Please run exactly like this:")
        print("  C:\\AI\\ai-env\\Scripts\\python.exe launch_mosky.py")
        print()
        print("Tip: Create a shortcut on the desktop with the above command.")
        input("Press Enter to exit...")
        sys.exit(1)

def ensure_voice_packages():
    try:
        # Import voice_interface FIRST. It has a broad try/except around webrtcvad
        # (which often fails with "pkg_resources" on Python 3.14+ due to old package).
        # It sets a fallback (energy-based VAD) so webrtcvad is non-critical.
        import automation_examples.voice_interface as vi  # noqa
        import faster_whisper  # noqa
        import piper           # noqa
        import sounddevice     # noqa
        import numpy           # noqa
        # webrtcvad import is intentionally omitted here - handled inside voice_interface

        # Try Pipecat for advanced real-time voice (optional but recommended)
        try:
            import pipecat  # noqa
            print("[OK] Pipecat available - using advanced real-time voice.")
        except Exception:
            print("[INFO] Pipecat not installed. Will use fallback audio loop.")
            print("       For best human-like experience: pip install pipecat-ai")

        return True
    except Exception as e:
        print("ERROR: Missing voice packages or cannot import MOSKY module.")
        print(f"Details: {e}")
        print()
        print("Fix: In a cmd window run:")
        print(r"  C:\AI\ai-env\Scripts\python.exe -m pip install faster-whisper piper-tts sounddevice webrtcvad numpy pipecat-ai pyaudio")
        print("Note: on Windows pyaudio may need additional setup or prebuilt wheel if portaudio issues.")
        print("Note: webrtcvad often fails with pkg_resources on this Python but MOSKY has energy fallback.")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

def ensure_greek_piper_voice():
    model = Path.home() / ".piper" / "voices" / "el_GR-rapunzelina-low.onnx"
    if model.exists() and model.stat().st_size > 10_000_000:
        print(f"[OK] Greek Piper voice found: {model}")
        return True

    print("[INFO] Greek Piper voice model not found or too small. Downloading now...")
    try:
        # Reuse the existing downloader (it knows the correct current voice)
        import download_piper_greek  # this will print its own messages
        # The script is designed to be importable/run directly
        # If it was run as module it may not execute the download, so we also run it as script
    except Exception:
        pass

    # Run the downloader script explicitly with the current python
    downloader = PROJECT_ROOT / "download_piper_greek.py"
    if downloader.exists():
        import subprocess
        result = subprocess.run([sys.executable, str(downloader)], capture_output=False)
        if result.returncode != 0:
            print("[WARN] Downloader script returned non-zero, but we continue.")

    # Re-check
    if model.exists() and model.stat().st_size > 10_000_000:
        print(f"[OK] Greek Piper voice downloaded: {model}")
        return True
    else:
        print("[ERROR] Could not get the Greek Piper voice model.")
        print("Please download manually:")
        print("  https://huggingface.co/rhasspy/piper-voices/tree/main/el/el_GR/rapunzelina/low")
        print("Place el_GR-rapunzelina-low.onnx and .onnx.json in:")
        print(f"  {model.parent}")
        print()
        input("Press Enter to exit...")
        sys.exit(1)

def check_primary_llm():
    """Check the primary reliable backend (llama.cpp on 8080)."""
    print("[INFO] Checking primary LLM (llama.cpp on :8080)...")
    try:
        # Use OpenAI compatible health
        import json
        req = urllib.request.Request("http://localhost:8080/v1/models", headers={"Authorization": "Bearer sk-dummy-local"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))
            models = [m.get("id", "") for m in data.get("data", [])]
            if any("gemma" in m.lower() or "qat" in m.lower() for m in models):
                print("[OK] Primary LLM (llama.cpp) responding with model(s):", models[:2])
                return True
            print("[OK] Primary LLM responding (models:", models[:3], ")")
            return True
    except Exception as e:
        print(f"[WARN] Primary LLM check failed: {e}")

    # Fallback info only
    print("       Primary llama.cpp not responding. Legacy Ollama may still be used by voice.")
    return False


def check_ollama():
    """Legacy check kept for voice launchers."""
    print("[INFO] Quick legacy Ollama check (secondary)...")
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=4) as r:
            data = r.read().decode("utf-8", errors="ignore")
            print("[INFO] Legacy Ollama responding.")
            return True
    except Exception as e:
        print(f"[WARN] Legacy Ollama not responding: {e}")
    return False

def main():
    print("=" * 55)
    print("  MOSKY Voice Interface (Greek)")
    print("=" * 55)
    print("This launcher speaks 'Έτοιμος, πες γεια σου mosky.' immediately.")
    print("Say the wake phrase to start talking to the agent.")
    print()
    print("Default: advanced Pipecat voice (real-time, full system integration).")
    print("Falls back if 'pipecat-ai' not installed in ai-env.")
    print()

    check_correct_python()
    ensure_voice_packages()
    ensure_greek_piper_voice()
    check_primary_llm()
    check_ollama()  # legacy / non-fatal

    print()
    print("Starting MOSKY voice interface...")
    print("You should hear the ready message in a moment.")
    print()

    # Set UTF-8 for Greek console + TTS
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["PYTHONUTF8"] = "1"

    # Now run the real interface
    # Prefer the new Pipecat-powered advanced voice (real-time, better integration with supervisor/research)
    try:
        import automation_examples.voice_pipecat_mosky as vpm
        if hasattr(vpm, 'run_pipecat_voice'):
            print("[INFO] Using advanced Pipecat MOSKY voice (recommended).")
            import asyncio
            asyncio.run(vpm.run_pipecat_voice())
        else:
            raise ImportError("No run function")
    except Exception as e:
        print(f"[INFO] Pipecat voice not available or failed ({e}), falling back to original.")
        import automation_examples.voice_interface as vi
        if hasattr(vi, 'main'):
            vi.main()
        else:
            print("No main() found in voice_interface. Please run manually.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nΈξοδος. Αντίο!")
    except Exception as fatal:
        print("\n[FATAL ERROR]")
        print(fatal)
        print("\nCommon fixes:")
        print("1. Run start-ai.bat first until everything is ONLINE.")
        print("2. Use exactly: C:\\AI\\ai-env\\Scripts\\python.exe launch_mosky.py")
        print("3. Make sure the Greek Piper model downloaded successfully.")
        input("\nPress Enter to close...")
        raise