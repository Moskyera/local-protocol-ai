#!/usr/bin/env python3
"""
MOSKY - Greek Voice Interface (Smart Self-Improving Agent)

The agent name is **MOSKY**.

Run in a **separate terminal** after start-ai.bat.
**Do not** auto-launch from any .bat or launcher.

Wake word: "γεια σου mosky" (or "γεια σου μόσκι", "mosky γεια σου" etc.)

Once woken, MOSKY listens for commands like:
- "τι νέο έχουμε σήμερα από github και x, ανάλυσε μου και πες μου αν μας ταιριάζει κάτι νέο σαν skill ή τεχνολογία"
- "ανακάλυψε νέες τεχνολογίες και skills και πρότεινε τι μπορούμε να προσθέσουμε"
- "τρέξε αξιολόγηση συστήματος"

MOSKY is very smart:
- Uses the full discovery cycle (GitHub + X with credibility analysis of user comments — detects truth vs hype/bullshit).
- Analyzes fit for our allowed code and whether it makes the agent a better general professional helper.
- Speaks natural Greek, includes proposals, fit reasoning, credibility verdict from X comments, and current system score.
- All proposals stay fully guarded (human approval, extra .approved file, pre-tests, etc.).

Installation:
pip install faster-whisper piper-tts sounddevice webrtcvad numpy

Download a Greek Piper voice (the working one is el_GR-rapunzelina-low from the el/el_GR/rapunzelina/low folder).
See download_piper_greek.py or run the voice-chat.bat (it tries to fetch it automatically).
Set env var PIPER_GREEK_VOICE=... if you put the .onnx elsewhere.

Run (recommended):
    C:\\AI\\ai-env\\Scripts\\python.exe launch_mosky.py

(Or from inside the market-agent folder, double-click a shortcut you made with the above command.)

Alternative (advanced / basic loop):
    python -m automation_examples.voice_interface

For the **best real-time human-like experience** (recommended from GitHub research):
    python -m automation_examples.voice_pipecat_mosky
    (Uses Pipecat framework + your LangGraph supervisor/research/MCP as the brain.
     Install: pip install pipecat-ai
     Reuses your Greek Piper + Whisper. Full-duplex capable, interruptions, multi-agent friendly.)
"""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
try:
    import requests
except ImportError:
    requests = None  # will be checked inside chat_with_mosky


# Make sure we can import our skills
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Compatibility shim for pkg_resources (some ML packages like older/forked
# faster-whisper / ctranslate2 internals still do "import pkg_resources").
# On certain Python 3.14 + wheel combinations it is not auto-exposed.
try:
    import pkg_resources  # noqa: F401
except ImportError:
    try:
        import setuptools  # this usually registers pkg_resources
        import pkg_resources  # noqa: F401
    except Exception:
        pass  # the packages may still work or will fail later with clearer error

# The heavy agent imports are done lazily inside the functions that need them
# so that the module can be imported from the dashboard without crashing if the env is not perfect.

# Conversation memory for natural dialogue (last N turns)
CONVERSATION_HISTORY = []
MAX_HISTORY_TURNS = 10  # keep recent context to not overwhelm the model

def get_primary_llm_base():
    """Primary = llama.cpp OpenAI-compatible (recommended)."""
    return os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")

def chat_with_mosky(user_message, system_prompt=None, use_history=True):
    """
    Natural dialogue with MOSKY using the primary LLM (llama.cpp on :8080).
    Falls back to legacy Ollama only if primary is unreachable.
    """
    global CONVERSATION_HISTORY

    model = os.getenv("LLM_MODEL", "gemma-4-26b-qat").replace("ollama/", "")

    if use_history:
        CONVERSATION_HISTORY.append({"role": "user", "content": user_message})

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    for turn in CONVERSATION_HISTORY[-MAX_HISTORY_TURNS*2:]:
        messages.append(turn)

    if requests is None:
        return "Fallback: requests not available."

    # Try primary (llama.cpp OpenAI compat) first
    try:
        base = get_primary_llm_base()
        # OpenAI compatible
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        # llama-server accepts /v1/chat/completions
        url = f"{base}/chat/completions" if "/v1" not in base else f"{base}/chat/completions"
        if "/v1" not in base:
            url = f"{base}/v1/chat/completions"

        resp = requests.post(url, json=payload, timeout=120, headers={"Authorization": "Bearer sk-dummy-local"})
        resp.raise_for_status()
        data = resp.json()
        assistant_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        if use_history and assistant_reply:
            CONVERSATION_HISTORY.append({"role": "assistant", "content": assistant_reply})

        return assistant_reply or "Λυπάμαι, δεν κατάλαβα καλά. Μπορείς να το ξαναπείς;"
    except Exception as primary_err:
        # Fallback to legacy Ollama (old /api/chat) for voice continuity
        try:
            ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
            legacy_model = os.getenv("OLLAMA_MODEL", model)
            resp = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": legacy_model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.7}
                },
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            assistant_reply = data.get("message", {}).get("content", "").strip()
            if use_history and assistant_reply:
                CONVERSATION_HISTORY.append({"role": "assistant", "content": assistant_reply})
            return assistant_reply or "Λυπάμαι, δεν κατάλαβα καλά."
        except Exception as e:
            return f"Πρόβλημα με LLM (primary + legacy): {str(e)[:120]}. Τρέξε start-ai.bat."

def clear_history():
    global CONVERSATION_HISTORY
    CONVERSATION_HISTORY = []
    print("[MOSKY] Conversation memory cleared.")

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("WARNING: missing faster-whisper (voice STT will be limited). Run: pip install faster-whisper")
    WhisperModel = None

try:
    from piper import PiperVoice
except ImportError:
    print("WARNING: missing piper-tts (voice TTS will be limited). Run: pip install piper-tts")
    PiperVoice = None

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("WARNING: missing sounddevice or numpy (audio I/O limited). Run: pip install sounddevice numpy")
    sd = None
    np = None

try:
    import webrtcvad
    VAD_AVAILABLE = True
except Exception as e:  # broader catch for legacy pkg_resources / build issues on Python 3.14+
    print(f"WARNING: webrtcvad import failed ({e}).")
    print("         Falling back to simple energy-based VAD (still works for wake word + commands).")
    webrtcvad = None
    VAD_AVAILABLE = False

# Heavy agent imports are done lazily (inside the command handlers) so that
# simple import errors or missing optional things don't kill the whole voice module at startup.
# We only do a very light validation here.
try:
    import openhands_skills  # just to confirm the package is visible via our sys.path hack
except Exception as e:
    print(f"[WARN] openhands_skills package not importable yet: {e}")
    print("This is often fixed by running from inside market-agent with the correct ai-env python.")

# === CONFIG ===
WHISPER_MODEL_SIZE = "large-v3"  # Best Greek accuracy. Use "medium" or "small" for lower RAM/GPU.
# Smart device selection: prefer CUDA if available, otherwise CPU.
# The previous "or True" forced CUDA always, which breaks on systems without proper CUDA.
try:
    import torch
    WHISPER_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    WHISPER_DEVICE = "cpu"

# Piper Greek voice (adjust path after you download)
# Current working Greek voice from the official repo is el_GR-rapunzelina-low (see download_piper_greek.py).
# You can override with env var: set PIPER_GREEK_VOICE=C:\path\to\el_GR-rapunzelina-low.onnx
_default_piper = os.path.expanduser("~/.piper/voices/el_GR-rapunzelina-low.onnx")
PIPER_MODEL_PATH = os.environ.get("PIPER_GREEK_VOICE", _default_piper)
PIPER_CONFIG_PATH = PIPER_MODEL_PATH + ".json"

# Also try a few other common locations if the default is missing
_possible_piper_paths = [
    PIPER_MODEL_PATH,
    os.path.expanduser("~/.piper/voices/el_GR-rapunzelina-low.onnx"),
    os.path.expanduser("~/.piper/el_GR-rapunzelina-low.onnx"),
    os.path.join(os.path.dirname(__file__), "..", "voices", "el_GR-rapunzelina-low.onnx"),
]

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # for VAD
VAD_AGGRESSIVENESS = 2   # 0-3, higher = more aggressive speech detection

# Models are loaded lazily inside the functions that need them (to avoid loading when imported by dashboard)
stt_model = None
tts_voice = None
vad = None

def _ensure_models_loaded():
    global stt_model, tts_voice, vad
    if stt_model is None:
        print("Loading Whisper for MOSKY (Greek)...")
        stt_model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type="float16" if WHISPER_DEVICE == "cuda" else "int8")
    if tts_voice is None:
        print("Loading Piper TTS (Greek voice for MOSKY)...")
        piper_path = None
        for p in _possible_piper_paths:
            if p and os.path.exists(p):
                piper_path = p
                break
        if not piper_path:
            raise RuntimeError(
                f"Piper Greek voice not found. Tried: {PIPER_MODEL_PATH} and a few other common spots.\n"
                "Run the voice-chat.bat again (it calls download_piper_greek.py automatically).\n"
                "Or manually download el_GR-rapunzelina-low from https://huggingface.co/rhasspy/piper-voices/tree/main/el/el_GR/rapunzelina/low\n"
                "Put the .onnx and .onnx.json in ~/.piper/voices/ or set PIPER_GREEK_VOICE env var."
            )
        PIPER_MODEL_PATH = piper_path
        PIPER_CONFIG_PATH = piper_path + ".json"
        tts_voice = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)
    if vad is None:
        if 'VAD_AVAILABLE' in globals() and VAD_AVAILABLE:
            try:
                vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
            except Exception as e:
                print(f"WARNING: could not init webrtcvad: {e}")
                vad = None
        else:
            vad = None

def record_audio_until_silence(max_duration=15):
    """Record from mic until silence is detected.
    Uses webrtcvad if available, otherwise a simple numpy RMS energy fallback.
    """
    _ensure_models_loaded()
    print("🎤 Listening... (speak now)")

    frames = []
    silence_frames = 0
    max_silence_frames = int(1.0 / (FRAME_DURATION_MS / 1000)) * 2  # ~2 sec silence to stop

    # RMS energy threshold for fallback VAD (tuned for normal speech)
    ENERGY_THRESHOLD = 300
    SILENCE_COUNT_FOR_END = max_silence_frames

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='int16') as stream:
        start_time = time.time()
        while True:
            frame, _ = stream.read(int(SAMPLE_RATE * FRAME_DURATION_MS / 1000))
            frame = np.asarray(frame).flatten()  # ensure 1D, avoid 0-d or (n,1) issues
            frames.append(frame)

            if VAD_AVAILABLE and vad is not None:
                is_speech = vad.is_speech(frame.tobytes(), SAMPLE_RATE)
            else:
                # Simple energy-based fallback (works without webrtcvad)
                energy = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
                is_speech = energy > ENERGY_THRESHOLD

            if not is_speech:
                silence_frames += 1
            else:
                silence_frames = 0

            if silence_frames > max_silence_frames or (time.time() - start_time > max_duration):
                break

    if not frames:
        return np.array([], dtype=np.int16)
    audio = np.concatenate(frames, axis=0)
    return audio

def transcribe(audio):
    """STT with Whisper, optimized for Greek. Ensures float32 normalized input."""
    _ensure_models_loaded()
    audio = np.asarray(audio)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype != np.float32:
        audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    segments, info = stt_model.transcribe(
        audio,
        language="el",  # Greek
        beam_size=5,
        vad_filter=True,
    )
    text = " ".join([seg.text for seg in segments]).strip()
    return text

def speak(text):
    """TTS with Piper. Streams to speakers. Robust to generator/empty/0-d arrays."""
    _ensure_models_loaded()
    if not text or not text.strip():
        return
    print(f"🗣️ MOSKY: {text}")
    try:
        audio = tts_voice.synthesize(text)
        # Piper can return generator of chunks or array
        if not isinstance(audio, np.ndarray):
            chunks = list(audio)
            if not chunks:
                return
            # Filter valid 1D arrays
            valid_chunks = [c for c in chunks if isinstance(c, np.ndarray) and c.size > 0 and c.ndim == 1]
            if not valid_chunks:
                return
            audio = np.concatenate(valid_chunks)
        audio = np.asarray(audio, dtype=np.float32)
        if audio.size == 0:
            return
        if audio.ndim > 1:
            audio = audio.mean(axis=1)  # force mono
        if audio.ndim != 1 or audio.size == 0:
            return
        sd.play(audio, samplerate=tts_voice.config.sample_rate)
        sd.wait()
    except Exception as e:
        print(f"[WARN] TTS failed: {e}")

def format_spoken_response(cycle_result, user_query):
    """
    Uses the LLM (with full conversation history) to generate a natural, contextual Greek response as MOSKY.
    Injects the research result so facts + credibility analysis are accurate, but the dialogue feels human.
    """
    system_prompt = (
        "Είσαι ο MOSKY, ένας έξυπνος, επαγγελματικός και φιλικός self-improving AI agent/helper. "
        "Μιλάς φυσικά, ζεστά και καθαρά στα ελληνικά. Θυμάσαι την προηγούμενη συνομιλία. "
        "Όταν σου δίνουν αποτελέσματα έρευνας από GitHub και X, τα χρησιμοποιείς για να δώσεις ακριβή ανάλυση: "
        "τι βρέθηκε, credibility από τα σχόλια των χρηστών (αλήθεια vs hype/ωεμματα), fit για τον κώδικα του χρήστη, "
        "και αν αξίζει να προστεθεί ως νέο skill ή βελτίωση. "
        "Είσαι ειλικρινής, όχι υπερβολικά ενθουσιώδης. "
        "Αναφέρεις πάντα το system score όταν είναι διαθέσιμο. "
        "Απαντάς σύντομα και φυσικά, σαν να συζητάς με φίλο."
    )

    # Build a rich prompt that includes the tool result
    tool_context = json.dumps(cycle_result, ensure_ascii=False)[:2500]
    full_message = (
        f"Ο χρήστης είπε: {user_query}\n\n"
        f"Αποτελέσματα από το discovery cycle (GitHub + X credibility analysis + fit):\n{tool_context}\n\n"
        "Απάντησε φυσικά στα ελληνικά ως MOSKY, κρατώντας την συνομιλία."
    )

    spoken = chat_with_mosky(full_message, system_prompt=system_prompt, use_history=True)
    return spoken


def format_evaluation_response(eval_result, user_query):
    """
    Turns the raw run_system_evaluation() dict into a natural, conversational Greek reply
    from MOSKY, while keeping conversation history.
    """
    system_prompt = (
        "Είσαι ο MOSKY, ένας έξυπνος, επαγγελματικός και φιλικός self-improving AI agent. "
        "Μιλάς φυσικά και καθαρά στα ελληνικά. Όταν σου δίνουν αποτελέσματα system evaluation "
        "(system_improvement_score, blockchain intelligence, engineering/RSI κομμάτια κλπ.), "
        "τα παρουσιάζεις σύντομα, ειλικρινά και φιλικά, σαν να συζητάς με τον χρήστη. "
        "Αναφέρεις το συνολικό score και τα πιο σημαντικά νούμερα/σχόλια. "
        "Αν χρειάζεται, ρώτα αν θέλει να δούμε προτάσεις βελτίωσης ή discovery."
    )

    # Keep the payload reasonable size for the prompt
    try:
        tool_context = json.dumps(eval_result, ensure_ascii=False, default=str)[:2200]
    except Exception:
        tool_context = str(eval_result)[:2200]

    full_message = (
        f"Ο χρήστης ρώτησε για αξιολόγηση / score: {user_query}\n\n"
        f"Αποτελέσματα από run_system_evaluation():\n{tool_context}\n\n"
        "Απάντησε φυσικά στα ελληνικά ως MOSKY, χρησιμοποιώντας τα νούμερα και τα συμπεράσματα."
    )

    spoken = chat_with_mosky(full_message, system_prompt=system_prompt, use_history=True)
    return spoken


def main():
    print("=== MOSKY Voice Interface ===")
    print("Πες «γεια σου mosky» για να ξυπνήσεις (conversation memory is on).")
    print("Παράδειγμα: «τι νέο έχουμε σήμερα από github και x, ανάλυσε και πες μου αν μας ταιριάζει κάτι νέο σαν skill».")
    print("Πάτα Ctrl+C για έξοδο. (History clears on restart)\n")
    print("Θα ακούσεις αμέσως φωνητικό μήνυμα 'Έτοιμος'.\n")

    # Pre-load models early so the interface feels responsive.
    # You will see "Loading Whisper..." and "Loading Piper..." once.
    print("Φορτώνω μοντέλα (Whisper + Piper)... αυτό γίνεται μόνο την πρώτη φορά.")
    models_loaded = False
    try:
        _ensure_models_loaded()
        print("Μοντέλα έτοιμα.")
        models_loaded = True
    except Exception as load_err:
        print(f"Πρόβλημα φόρτωσης μοντέλων: {load_err}")
        print("Βεβαιώσου ότι το Greek Piper voice είναι κατεβασμένο (το bat προσπαθεί αυτόματα).")
        print("Το voice interface δεν μπορεί να ξεκινήσει χωρίς το TTS model.")

    # Speak the ready message immediately on startup (user request) - only if loaded
    if models_loaded:
        speak("Έτοιμος, πες γεια σου mosky.")
    else:
        print("Skipping initial voice prompt due to model load failure.")
        print("\nCannot continue without the Greek Piper model and Whisper.")
        input("Press Enter to close the window...")
        sys.exit(1)

    woken = False

    while True:
        try:
            audio = record_audio_until_silence(max_duration=15)
            if len(audio) < 2000:
                continue

            text = transcribe(audio)
            if not text:
                continue

            lowered = text.lower().strip()

            # Wake word
            if not woken:
                if any(phrase in lowered for phrase in ["γεια σου mosky", "γεια σου μόσκι", "mosky γεια σου", "γεια mosky"]):
                    woken = True
                    speak("Γεια σου! Είμαι ο MOSKY και θυμάμαι τη συζήτησή μας. Τι να ψάξω ή να αναλύσω;")
                    print("[MOSKY] Woken. Conversation memory active.")
                continue

            print(f"\n[Εσύ] {text}")
            CONVERSATION_HISTORY.append({"role": "user", "content": text})

            # End conversation
            if any(kw in lowered for kw in ["τέλος", "σταμάτα", "bye", "αντίο", "clear history"]):
                speak("Εντάξει. Η συζήτηση τελείωσε για τώρα. Πες «γεια σου mosky» όταν θες να συνεχίσουμε.")
                clear_history()
                woken = False
                continue

            # === Evaluation / System score (specific, comes before broad research keywords) ===
            eval_keywords = ["αξιολόγηση", "score", "πόσο καλά", "system", "αξιολόγησε", "system evaluation", "βαθμολογία", "πόσο καλό", "πόσο είναι το score"]
            if any(kw in lowered for kw in eval_keywords):
                print("[MOSKY] Τρέχω system evaluation...")
                try:
                    from openhands_skills.evaluation_harness import run_system_evaluation
                    eval_result = run_system_evaluation()
                    spoken = format_evaluation_response(eval_result, text)
                except Exception as eval_err:
                    spoken = f"Δεν μπόρεσα να τρέξω την αξιολόγηση του συστήματος: {eval_err}. Προσπάθησε ξανά αργότερα."

            # Detect research/discovery intent → use the powerful cycle, then natural LLM response
            elif any(kw in lowered for kw in ["νέο", "github", "x", "ανάλυσε", "ταιριάζει", "skill", "τεχνολογία", "νέα τεχνολογία", "ανακάλυψε", "νέα skills", "νέες τεχνολογίες"]):
                print("[MOSKY] Τρέχω πλήρη discovery & credibility analysis...")
                try:
                    from openhands_skills.langgraph_orchestrator import run_self_improvement_and_discovery_cycle
                    cycle_result = run_self_improvement_and_discovery_cycle(focus="new_skills_and_tech")
                    spoken = format_spoken_response(cycle_result, text)
                except Exception as cycle_err:
                    spoken = f"Δεν μπόρεσα να τρέξω το discovery cycle: {cycle_err}. Χρησιμοποίησε το chat κανονικά."
            else:
                # Pure natural dialogue with memory (no tool call)
                print("[MOSKY] Φυσική συνομιλία...")
                spoken = chat_with_mosky(text, use_history=True)

            speak(spoken)

        except KeyboardInterrupt:
            print("\nΈξοδος. Αντίο!")
            break
        except Exception as e:
            print(f"[MOSKY Error] {e}")
            try:
                speak("Υπήρξε ένα μικρό τεχνικό πρόβλημα. Προσπάθησε ξανά.")
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except Exception as fatal:
        print("\n[FATAL ERROR in MOSKY voice interface]")
        print(fatal)
        print("\nCommon fixes:")
        print("1. Run this AFTER start-ai.bat is fully up (primary LLM on http://localhost:8080 or legacy Ollama on 11434).")
        print("2. Double-click voice-chat.bat while inside the market-agent folder, or run it from cmd after cd there.")
        print("3. The bat tries ai-env first (both the one inside market-agent and C:\\AI\\ai-env). Make sure voice packages are installed in that python.")
        print("4. pip install faster-whisper piper-tts sounddevice webrtcvad numpy   (in the correct ai-env)")
        print("5. Download a Greek Piper voice (.onnx + .json) and either put it under ~/.piper/voices/ or set PIPER_GREEK_VOICE env var.")
        print("6. If you see 'Could not import custom agent logic' or openhands_skills errors: you are using a python that doesn't see the project.")
        input("\nPress Enter to close...")
        raise