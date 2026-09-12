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

# Private mode for the whole process: kill-switches + the socket guard,
# before whisper/Piper/fastmcp are imported. lpai_private.py lives at the
# repo root; python -m voice_agent from the repo dir finds it.
import sys as _sys
if str(REPO) not in _sys.path:
    _sys.path.insert(0, str(REPO))
import lpai_private as _lp
_lp.activate()


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
LLM_BASE_URL = _lp.require_local_endpoint(_env("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1").rstrip("/"))
LLM_MODEL = _env("VOICE_LLM_MODEL", "gemma-4-26b-qat")
LLM_API_KEY = _env("OPENAI_API_KEY", "sk-dummy-local")
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 600
LLM_THINKING = False
LLM_TIMEOUT_S = 120
# Spoken once when a reply takes this long. MEASURED 2026-09-11: warm turns
# 1.5-2.0 s; the FIRST turn 9.4 s because the 2150-token prefix is
# processed cold (prompt_ms 4500). The prefix is now warmed at startup, so
# anything past this is a queued request behind another client.
LLM_SLOW_NOTICE_S = 12

# --------------------------------------------------------------------------- #
# Ears. faster-whisper large-v3-turbo on CPU.
#
# MEASURED (Piper-generated clean Greek -> whisper): 0.0% character error on
# correctly pronounced sentences; language detected el/en at 0.99-1.00.
# MEASURED speed, int8, 16 threads, beam_size=1: 5.5 s clip in 3.1 s (0.57x
# real time); model load 2 s once cached. small was 0.20x but mangled Greek
# ("εντολίδα"); medium 0.52x. turbo is the accuracy/speed point.
# MEASURED 2026-09-12 (machine at 33% background load): the library's
# transcribe() encodes every clip twice, 6.0-6.3 s per utterance; stt.py
# encodes once and reuses it, 3.1-3.2 s, identical text, on 1.2 s and 4.6 s
# clips alike. Whisper always encodes a 30 s window, so a short "ναι,
# συνέχισε" costs the same as a long sentence: the encoder IS the cost.
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
# ...except that the agent's own confirmation phrases and exit words are
# shorter than that at Piper's pace (MEASURED: "Ναι, κάντο" 1.0 s, "No, stop"
# 1.15 s, "Τέλος." 0.6 s), and whisper returned them at 0% CER with high
# confidence. A short clip is accepted only when whisper is sure of it:
# two or more words, language el/en at >= 0.95, avg_logprob >= -0.6.
STT_SHORT_MIN_WORDS = 2
STT_SHORT_MIN_LANG_PROB = 0.95
STT_SHORT_MIN_AVG_LOGPROB = -0.6
# Whisper's language guess is adopted only above this; below it the reply
# language stays what it was (MEASURED: a 1.5 s Greek clip came back as
# Swedish at 0.52, Romanian at 0.32).
STT_LANG_ADOPT_PROB = 0.8
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
# The mic queue is bounded: while a tool runs for a minute nobody is
# listening, and an unbounded queue then replayed that minute as the next
# command (MEASURED: 93 stale frames returned as a 1.6 s "utterance").
AUDIO_QUEUE_MAX_FRAMES = int(60 * 1000 / AUDIO_FRAME_MS)
# On open speakers the agent hears itself; its own destructive announcement
# contains "όχι, ακύρωσέ το" and scored as a NO (0.99), auto-cancelling every
# action. With this set the mic is muted while the agent speaks, which also
# disables barge-in. A headset needs neither.
SPEAKERS = _env("VOICE_SPEAKERS", "0") not in ("0", "false", "no")
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
# Ending the session by voice. Two words or more, like everything else the
# agent must hear reliably; matched fuzzily with the confirmation machinery.
EXIT_PHRASES = {
    "el": ["τέλος για σήμερα", "τέλος τα λέμε", "εντάξει τέλος", "αντίο τα λέμε", "αυτά για τώρα", "κλείσε τώρα"],
    "en": ["that is all goodbye", "we are done bye", "okay goodbye", "that is all for now", "exit now"],
}
EXIT_MATCH_THRESHOLD = 0.72

# --------------------------------------------------------------------------- #
# Tools that live in the MCP server on :8765 (35 of them) plus the local ones.
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Privacy. PRIVATE (the default) means: no tool the voice assistant can call
# sends anything off this machine. The MCP tools that reach the internet
# (wallet forensics, market data, web pages, research) are not even offered
# to the model. Set VOICE_PRIVATE=0 to offer them; each one is then
# announced with its destination and the exact text before it runs, and can
# be interrupted. The owner asked for this in so many words.
# --------------------------------------------------------------------------- #
PRIVATE = (_env("VOICE_PRIVATE", "1") not in ("0", "false", "no")) if _env("VOICE_PRIVATE") else _lp.is_private()

# Where the assistant writes: dictated notes and the per-turn log. Tests
# point this at a temp dir; the real files are git-ignored.
MEMORY_DIR = Path(_env("VOICE_MEMORY_DIR", REPO / "memory"))
NOTES_FILE = MEMORY_DIR / "voice_notes.md"
LOG_FILE = MEMORY_DIR / "voice_log.jsonl"

MCP_URL = _env("VOICE_MCP_URL", "http://127.0.0.1:8765/mcp")
MCP_TOKEN = _lp.mcp_token(create=False)        # the server requires it in private mode
# When the tool server is down at start, try again in the background at
# this interval for this long. MEASURED: a failed discovery costs 2 s (port
# closed) to 8 s (port open, not serving), so it must never sit on the
# turn path.
MCP_RETRY_S = 15
MCP_RETRY_FOR_S = 120
MCP_CONNECT_TIMEOUT_S = 8
# A research/self-improvement tool can run for minutes; the voice loop must
# not sit silent that long. Discovery had a timeout, calls did not.
MCP_CALL_TIMEOUT_S = 90
# Every tool result the model sees is cut here WITH a marker. The system
# prompt + 42 schemas already cost ~4200 of the 16384-token context
# (MEASURED: cache_n 4203), and history keeps the last 24 messages.
TOOL_RESULT_MAX_CHARS = 8000
