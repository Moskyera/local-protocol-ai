"""Hearing. faster-whisper on CPU, with the honesty the measurements demand.

`Transcriber.transcribe()` returns text plus the language whisper detected
and a confidence. The caller refuses low-confidence results and asks the
owner to repeat, instead of feeding noise to the model - a measured failure
mode: whisper on clips under ~1.2 s returned confident nonsense.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from . import config


@dataclass
class Heard:
    text: str
    lang: str            # "el", "en", ... as whisper reports
    lang_prob: float
    avg_logprob: float   # whisper's own confidence; more negative = worse
    no_speech: float     # probability the clip has no speech at all
    seconds_audio: float
    seconds_stt: float

    @property
    def usable(self) -> bool:
        if not self.text.strip():
            return False
        if self.seconds_audio < config.STT_MIN_UTTERANCE_S:
            return False
        if self.avg_logprob < config.STT_MIN_AVG_LOGPROB:
            return False
        if self.no_speech > config.STT_MAX_NO_SPEECH:
            return False
        return True

    @property
    def why_unusable(self) -> str:
        if not self.text.strip():
            return "empty"
        if self.seconds_audio < config.STT_MIN_UTTERANCE_S:
            return f"too short ({self.seconds_audio:.1f}s)"
        if self.avg_logprob < config.STT_MIN_AVG_LOGPROB:
            return f"low confidence ({self.avg_logprob:.2f})"
        if self.no_speech > config.STT_MAX_NO_SPEECH:
            return f"probably not speech ({self.no_speech:.2f})"
        return ""


class Transcriber:
    def __init__(self):
        self._model = None

    def load(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            t0 = time.perf_counter()
            self._model = WhisperModel(config.STT_MODEL, device="cpu",
                                       compute_type=config.STT_COMPUTE, cpu_threads=config.STT_THREADS)
            self.load_seconds = time.perf_counter() - t0
        return self._model

    def transcribe(self, audio: np.ndarray, rate: int = config.AUDIO_RATE,
                   language: Optional[str] = None) -> Heard:
        """audio: int16 or float32 mono at `rate`. Language None = detect."""
        model = self.load()
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        if rate != 16000:
            audio = _resample(audio, rate, 16000)
        secs = len(audio) / 16000.0
        t0 = time.perf_counter()
        segments, info = model.transcribe(audio, language=language, beam_size=config.STT_BEAM,
                                          vad_filter=False, condition_on_previous_text=False)
        segs = list(segments)
        dt = time.perf_counter() - t0
        text = " ".join(s.text.strip() for s in segs).strip()
        lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -9.0
        ns = float(np.mean([s.no_speech_prob for s in segs])) if segs else 1.0
        return Heard(text, info.language or "el", float(info.language_probability or 0.0),
                     lp, ns, secs, dt)


def _resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    """Linear resample; fine for speech going into whisper's 16 kHz mel."""
    if src == dst:
        return x
    n = int(round(len(x) * dst / src))
    xp = np.linspace(0, len(x) - 1, num=n)
    return np.interp(xp, np.arange(len(x)), x).astype(np.float32)
