"""Listening. The headset mic, gated by Silero VAD into utterances.

`Listener.listen()` blocks until the owner has spoken and then paused, and
returns the utterance as 16 kHz int16 mono. It also exposes `speech_started`,
an Event the speaker watches for barge-in: when the owner talks over the
agent, playback stops within a frame.

Silero VAD runs as ONNX on the CPU; it needs no torch and ships with
faster-whisper. The thresholds are in config.py.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Optional

import numpy as np

from . import config


class _SileroVad:
    """Silero VAD v6, streamed frame by frame through onnxruntime on one CPU
    core. The model ships inside faster-whisper (assets/silero_vad_v6.onnx),
    so it costs no download; faster-whisper's own wrapper resets the LSTM
    state on every call, which is right for files and wrong for a live mic,
    hence this one carries h, c and the 64-sample context between frames.

    MEASURED 2026-09-11, 512-sample frames: 0.06 ms per frame; silence 0.00,
    white noise 0.04 (webrtcvad, which this replaced, called that speech),
    Piper-spoken Greek 0.74 mean with 0.99 peaks. Published ROC-AUC is 0.97
    against webrtcvad's 0.73 (snakers4/silero-vad wiki, Quality Metrics)."""

    def __init__(self, threshold: float):
        import os
        import onnxruntime as ort
        from faster_whisper.vad import get_assets_path
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = opts.intra_op_num_threads = 1
        opts.log_severity_level = 4
        self._s = ort.InferenceSession(os.path.join(get_assets_path(), "silero_vad_v6.onnx"),
                                       providers=["CPUExecutionProvider"], sess_options=opts)
        self._threshold = threshold
        self.reset()

    def reset(self) -> None:
        self._h = np.zeros((1, 1, 128), np.float32)
        self._c = np.zeros((1, 1, 128), np.float32)
        self._ctx = np.zeros(64, np.float32)

    def prob(self, frame: np.ndarray) -> float:
        x = frame.astype(np.float32) / 32768.0
        out, self._h, self._c = self._s.run(None, {"input": np.concatenate([self._ctx, x])[None, :],
                                                    "h": self._h, "c": self._c})
        self._ctx = x[-64:]
        return float(np.asarray(out).reshape(-1)[0])

    def is_speech(self, frame: np.ndarray) -> bool:
        return self.prob(frame) >= self._threshold


class Listener:
    def __init__(self, input_device: Optional[str] = None):
        self._vad = _SileroVad(config.VAD_THRESHOLD)
        self._device = input_device
        self._frame = config.AUDIO_FRAME_SAMPLES
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream = None
        self.speech_started = threading.Event()
        self._muted = threading.Event()

    # ---- stream lifecycle ----------------------------------------------
    def start(self) -> None:
        import sounddevice as sd
        dev = self._device
        if dev is not None and dev.isdigit():
            dev = int(dev)
        self._stream = sd.InputStream(samplerate=config.AUDIO_RATE, channels=1, dtype="int16",
                                      blocksize=self._frame, device=dev, callback=self._on_audio)
        self._stream.start()

    def stop(self) -> None:
        if self._stream:
            self._stream.stop(); self._stream.close(); self._stream = None

    def _on_audio(self, indata, frames, t, status) -> None:
        if self._muted.is_set():
            return
        self._q.put(indata[:, 0].copy())

    def mute(self, on: bool) -> None:
        """While the agent speaks through open speakers, its own voice would
        trigger the VAD. A headset makes this unnecessary; it is here for
        anyone on speakers, and it is what disables barge-in when set."""
        if on:
            self._muted.set()
            with self._q.mutex:
                self._q.queue.clear()
        else:
            self._muted.clear()

    # ---- the utterance ---------------------------------------------------
    def listen(self, timeout_s: Optional[float] = None) -> Optional[np.ndarray]:
        """Wait for speech, capture until a pause, return it. None on timeout."""
        self.speech_started.clear()
        end_frames = int(config.VAD_END_SILENCE_MS / config.AUDIO_FRAME_MS)
        self._vad.reset()
        max_frames = int(config.VAD_MAX_UTTERANCE_S * 1000 / config.AUDIO_FRAME_MS)
        pre = []                    # ring of the last few frames before speech
        voiced: list[np.ndarray] = []
        run = 0                     # consecutive speech frames before speech
        silence = 0
        started = False
        t_end = time.monotonic() + timeout_s if timeout_s else None

        while True:
            if t_end and not started and time.monotonic() > t_end:
                return None
            try:
                frame = self._q.get(timeout=0.25)
            except queue.Empty:
                continue
            if len(frame) != self._frame:
                continue
            is_speech = self._vad.is_speech(frame)

            if not started:
                pre.append(frame); pre = pre[-10:]
                run = run + 1 if is_speech else 0
                if run >= config.VAD_START_FRAMES:
                    started = True
                    self.speech_started.set()
                    voiced = list(pre)
                continue

            voiced.append(frame)
            silence = 0 if is_speech else silence + 1
            if silence >= end_frames or len(voiced) >= max_frames:
                # drop the trailing silence frames except a little tail
                keep = max(0, len(voiced) - silence + 3)
                return np.concatenate(voiced[:keep])
