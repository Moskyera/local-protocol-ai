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
        return self.why_unusable == ""

    @property
    def why_unusable(self) -> str:
        if not self.text.strip():
            return "empty"
        if self.lang not in ("el", "en"):
            # MEASURED: 1.5 s Greek clips came back as Swedish/Spanish/Romanian
            # text at 0.3-0.5; feeding that to the model is worse than asking again
            return f"language {self.lang} ({self.lang_prob:.2f})"
        if self.seconds_audio < config.STT_MIN_UTTERANCE_S and not self._confident_short:
            return f"too short ({self.seconds_audio:.1f}s)"
        if self.avg_logprob < config.STT_MIN_AVG_LOGPROB:
            return f"low confidence ({self.avg_logprob:.2f})"
        if self.no_speech > config.STT_MAX_NO_SPEECH:
            return f"probably not speech ({self.no_speech:.2f})"
        return ""

    @property
    def _confident_short(self) -> bool:
        """A clip under the length gate is kept only when whisper is sure of
        it: the phrases the agent itself asks for are that short."""
        return (len(self.text.split()) >= config.STT_SHORT_MIN_WORDS
                and self.lang_prob >= config.STT_SHORT_MIN_LANG_PROB
                and self.avg_logprob >= config.STT_SHORT_MIN_AVG_LOGPROB)


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
        segs, lang, prob = self._one_pass(model, audio, language)
        dt = time.perf_counter() - t0
        text = " ".join(s.text.strip() for s in segs).strip()
        lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -9.0
        ns = float(np.mean([s.no_speech_prob for s in segs])) if segs else 1.0
        return Heard(text, lang, prob, lp, ns, secs, dt)

    @staticmethod
    def _one_pass(model, audio: np.ndarray, language: Optional[str]):
        """Encode once, detect the language on that encoder output, decode
        with it. faster-whisper 1.2.1's transcribe(language=None) encodes
        the 30 s window in detect_language() and AGAIN in generate_segments()
        (transcribe.py:918 sets encoder_output=None and never reuses the
        first). MEASURED: the encoder is 73-92% of STT time here, and this
        path gives byte-identical text, avg_logprob and no_speech on Greek,
        English and a 1.3 s confirmation clip with encodes 2 -> 1. This
        touches semi-private API, hence the version pin in requirements."""
        from faster_whisper.audio import pad_or_trim
        from faster_whisper.tokenizer import Tokenizer
        from faster_whisper.transcribe import TranscriptionOptions, get_suppressed_tokens
        feats = model.feature_extractor(audio)
        enc = model.encode(pad_or_trim(feats[:, : feats.shape[-1] - 1]))
        if language:
            lang, prob = language, 1.0
        else:
            token, prob = model.model.detect_language(enc)[0][0]
            lang, prob = token[2:-2], float(prob)
        tokenizer = Tokenizer(model.hf_tokenizer, model.model.is_multilingual, task="transcribe", language=lang)
        options = TranscriptionOptions(
            beam_size=config.STT_BEAM, best_of=5, patience=1, length_penalty=1, repetition_penalty=1,
            no_repeat_ngram_size=0, log_prob_threshold=-1.0, no_speech_threshold=0.6,
            compression_ratio_threshold=2.4, condition_on_previous_text=False,
            prompt_reset_on_temperature=0.5, temperatures=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            initial_prompt=None, prefix=None, suppress_blank=True,
            suppress_tokens=get_suppressed_tokens(tokenizer, [-1]), without_timestamps=False,
            max_initial_timestamp=1.0, word_timestamps=False,
            prepend_punctuations="\"'“¿([{-", append_punctuations="\"'.。,，!！?？:：”)]}、",
            multilingual=False, max_new_tokens=None, clip_timestamps="0",
            hallucination_silence_threshold=None, hotwords=None)
        segs = list(model.generate_segments(feats, tokenizer, options, False, enc))
        return segs, lang, prob


def _resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    """Linear resample; fine for speech going into whisper's 16 kHz mel."""
    if src == dst:
        return x
    n = int(round(len(x) * dst / src))
    xp = np.linspace(0, len(x) - 1, num=n)
    return np.interp(xp, np.arange(len(x)), x).astype(np.float32)
