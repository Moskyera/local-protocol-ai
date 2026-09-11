"""Every tunable of the voice agent, with where its value came from.

Nothing here is a guess. A number without a provenance line is a bug: this
machine has hard-crashed under GPU load and the whole stack has spent months
removing code that claimed things it had not measured. Measured 2026-09-11 on
the reference machine (Windows 11, Ryzen 9950X, RX 9070 XT 16 GB, Logitech
PRO X headset) unless a line says otherwise.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _env(name: str, default=None):
    """os.getenv, except that an EMPTY value counts as unset. .env.example
    ships these keys blank so they are easy to find; a blank must not turn
    into Path("") or a device called ""."""
    v = os.getenv(name)
    return default if v is None or not v.strip() else v.strip()

# --------------------------------------------------------------------------- #
# The model that thinks. gemma-4-26B-A4B through llama.cpp.
#
# MEASURED: with --jinja, llama.cpp b9587 parses gemma-4's native
# <|tool_call> syntax into structured tool_calls (Greek request ->
# get_weather{city:"Thessaloniki"}, mixed EN/EL -> delete_folder{path}).
# MEASURED: with thinking ON the model spent its whole 400-token budget in
# reasoning_content and the visible answer was cut to seven words (16.6 s).
# With enable_thinking=False: 3.7 s, 82 tokens, a complete native-Greek
# answer. Thinking stays OFF for conversation.
# --------------------------------------------------------------------------- #
LLM_BASE_URL = _env("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/")
LLM_MODEL = _env("VOICE_LLM_MODEL", "gemma-4-26b-qat")
LLM_API_KEY = _env("OPENAI_API_KEY", "sk-dummy-local")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 600
LLM_THINKING = False
LLM_TIMEOUT_S = 120

# --------------------------------------------------------------------------- #
# Ears. faster-whisper large-v3-turbo on CPU.
#
# MEASURED (Piper-generated clean Greek -> whisper): 0.0% character error on
# correctly pronounced sentences; language detected el/en at 0.99-1.00.
# MEASURED speed, int8, 16 threads, beam_size=1: 5.5 s clip in 3.1 s (0.57x
# real time); model load 2 s once cached. small was 0.20x but mangled Greek
# ("εντολίδα"); medium 0.52x. turbo is the accuracy/speed point.
# NOT on the GPU: ctranslate2 has no CUDA here and whisper.cpp ships no
# Windows Vulkan binary; a source build needs MSVC + Vulkan SDK, which are not
# installed. CPU is the honest path today.
# --------------------------------------------------------------------------- #
STT_MODEL = _env("VOICE_STT_MODEL", "large-v3-turbo")
STT_COMPUTE = "int8"
STT_THREADS = int(_env("VOICE_STT_THREADS", "16"))
STT_BEAM = 1
# MEASURED: whisper on clips under ~1.2 s is unreliable regardless of padding
# or prompting ("Ναι" -> "Ευχαριστώ", "Όχι" -> "Ποια"); at >= 1.5 s it was
# 0% on every trial. Anything shorter is asked to be repeated, not guessed.
STT_MIN_UTTERANCE_S = 1.2
# Whisper's own confidence. Below these the transcript is treated as noise.
STT_MIN_AVG_LOGPROB = -1.0
STT_MAX_NO_SPEECH = 0.6

# --------------------------------------------------------------------------- #
# Mouth. Piper, one voice per language.
#
# MEASURED round trip (Piper -> whisper, 3 Greek sentences):
#   el_GR-rapunzelina-low     8.9% CER   the voice that shipped; mispronounces
#   el_GR-rapunzelina-medium  5.6% CER
#   el_GR-joy-medium          1.8% CER   two of three sentences word-perfect
#   en_US-lessac-medium       0.0% CER
#   en_US-ryan-high           0.0% CER   richer; 0.25 s per sentence
# Synthesis is ~0.1 s per sentence for all of them.
# Whether Piper SOUNDS natural enough is the owner's ear to judge; these are
# the most accurate voices available in the format installed today.
# --------------------------------------------------------------------------- #
PIPER_DIR = Path(_env("PIPER_VOICES_DIR", Path.home() / ".piper" / "voices"))
TTS_VOICES = {
    "el": _env("VOICE_TTS_EL", "el_GR-joy-medium"),
    "en": _env("VOICE_TTS_EN", "en_US-ryan-high"),
}
TTS_DEFAULT_LANG = "el"

# --------------------------------------------------------------------------- #
# Turn-taking. Silero VAD v6 (ONNX, CPU) on the headset mic.
# 16 kHz mono is what both Silero and whisper want; the PRO X mic reports
# 44.1 kHz and is resampled. Silero works on 512-sample frames (32 ms).
# MEASURED 2026-09-11: 0.06 ms per frame; silence 0.00, white noise 0.04,
# Piper-spoken Greek 0.74 mean / 0.99 peak, so 0.5 sits well clear of both.
# --------------------------------------------------------------------------- #
AUDIO_RATE = 16000
AUDIO_FRAME_SAMPLES = 512
AUDIO_FRAME_MS = AUDIO_FRAME_SAMPLES * 1000 / AUDIO_RATE     # 32
VAD_THRESHOLD = 0.5
VAD_START_FRAMES = 6         # ~190 ms of speech before we count it as speech
VAD_END_SILENCE_MS = 800     # the pause that ends an utterance
VAD_MAX_UTTERANCE_S = 30
INPUT_DEVICE = _env("VOICE_INPUT_DEVICE")     # None = system default
OUTPUT_DEVICE = _env("VOICE_OUTPUT_DEVICE")

# --------------------------------------------------------------------------- #
# The safety gate. See guard.py for the classes; these are the spoken
# confirmation phrases. Every phrase is >= 2 words on purpose (the whisper
# finding above). Matched fuzzily; one-word answers are never accepted.
# --------------------------------------------------------------------------- #
CONFIRM_PHRASES = {
    "el": ["ναι συνέχισε", "ναι προχώρα", "ναι κάντο", "ναι είμαι σίγουρος", "ναι είμαι σίγουρη", "συνέχισε κανονικά"],
    "en": ["yes go ahead", "yes do it", "yes continue", "yes i am sure", "go ahead and do it"],
}
DENY_PHRASES = {
    "el": ["όχι ακύρωσέ το", "όχι σταμάτα", "όχι μην το κάνεις", "ακύρωσε το", "άσ' το"],
    "en": ["no cancel it", "no stop", "no do not", "cancel that", "never mind"],
}
CONFIRM_MATCH_THRESHOLD = 0.72   # difflib ratio; below this we ask again
CONFIRM_TIMEOUT_S = 20           # no answer = cancelled, never = proceed

# --------------------------------------------------------------------------- #
# Tools that live in the MCP server on :8765 (35 of them) plus the local ones.
# --------------------------------------------------------------------------- #
MCP_URL = _env("VOICE_MCP_URL", "http://127.0.0.1:8765/mcp")
MCP_CONNECT_TIMEOUT_S = 8
