"""Speaking. Piper, one voice per language, with barge-in.

The voice is chosen by the language of the text being spoken, not by what
the owner said: a Greek question may get an English word in the answer and
vice versa. Playback runs on its own thread so the mic can keep listening;
`stop()` cuts it the moment the owner starts talking over it.

Voices and their measured accuracy are in config.py. If a voice file is
missing the error names the exact download, because "TTS failed" helps
nobody.
"""

from __future__ import annotations

import contextlib
import io
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from . import config

_VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{name}"


class VoiceMissing(FileNotFoundError):
    pass


def _voice_path(lang: str) -> Path:
    name = config.TTS_VOICES.get(lang, config.TTS_VOICES[config.TTS_DEFAULT_LANG])
    p = config.PIPER_DIR / f"{name}.onnx"
    if not p.is_file() or not p.with_suffix(".onnx.json").is_file():
        # e.g. el_GR-joy-medium -> el/el_GR/joy/medium/el_GR-joy-medium.onnx
        loc, voice, quality = name.split("-")
        sub = f"{loc.split('_')[0]}/{loc}/{voice}/{quality}/{name}"
        raise VoiceMissing(
            f"Piper voice {name} not found in {config.PIPER_DIR}.\n"
            f"  download both files:\n"
            f"    {_VOICE_URL.format(lang='', name=sub)}.onnx\n"
            f"    {_VOICE_URL.format(lang='', name=sub)}.onnx.json".replace("main//", "main/"))
    return p


class Speaker:
    def __init__(self, output_device: Optional[str] = None):
        self._voices: dict[str, object] = {}
        self._rates: dict[str, int] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._device = output_device

    def load(self, lang: str):
        if lang in self._voices:
            return self._voices[lang]
        from piper import PiperVoice
        p = _voice_path(lang)
        v = PiperVoice.load(str(p), config_path=str(p.with_suffix(".onnx.json")))
        self._voices[lang] = v
        self._rates[lang] = int(v.config.sample_rate)
        return v

    def synthesize(self, text: str, lang: str) -> tuple[np.ndarray, int]:
        v = self.load(lang)
        chunks = []
        # piper prints "Missing phoneme" to stderr for a stray combining mark;
        # measured harmless (0% CER on the sentences that trigger it).
        with contextlib.redirect_stderr(io.StringIO()):
            for ch in v.synthesize(text):
                b = ch.audio_int16_bytes if hasattr(ch, "audio_int16_bytes") else ch
                chunks.append(np.frombuffer(b, dtype=np.int16))
        audio = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)
        return audio, self._rates[lang]

    def say(self, text: str, lang: str, block: bool = True) -> None:
        """Speak, interruptibly. A second call while speaking cuts the first."""
        self.stop()
        audio, rate = self.synthesize(text, lang)
        if audio.size == 0:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._play, args=(audio, rate), daemon=True)
        self._thread.start()
        if block:
            self._thread.join()

    def _play(self, audio: np.ndarray, rate: int) -> None:
        import sounddevice as sd
        # small blocks so stop() takes effect within ~50 ms
        block = int(rate * 0.05)
        with self._lock:
            with sd.OutputStream(samplerate=rate, channels=1, dtype="int16",
                                 device=self._device, blocksize=block) as out:
                for i in range(0, len(audio), block):
                    if self._stop.is_set():
                        break
                    out.write(audio[i:i + block])

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1.0)

    @property
    def speaking(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())
