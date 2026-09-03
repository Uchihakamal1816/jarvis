"""
JARVIS Voice Layer — Silero VAD Wrapper

Wraps the Silero VAD model (ONNX-backed by default, no PyTorch GPU bloat)
and exposes a simple streaming interface.

Audio contract (per chunk fed to `process_chunk`):
  - Exactly 512 samples at 16 kHz  →  32 ms per chunk
  - dtype: float32 in [-1.0, 1.0]  (NOT int16)
  - Shape: [512]  (1-D, mono)

VADIterator emits two events:
  - {'start': seconds}  when speech onset detected
  - {'end':   seconds}  when silence long enough after speech
"""

from __future__ import annotations

import numpy as np
import torch

try:
    from silero_vad import load_silero_vad, VADIterator
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "silero-vad is not installed. Run: pip install silero-vad"
    ) from exc

from . import config
from .logger import get_logger

log = get_logger(__name__)

# Reduce torch CPU thread contention when running alongside other threads
torch.set_num_threads(1)


class VAD:
    """
    Stateful Silero VAD wrapper for chunk-by-chunk streaming.

    Usage::

        vad = VAD()
        event = vad.process_chunk(float32_tensor_of_512_samples)
        if event and 'start' in event:
            ...  # speech started
        if event and 'end' in event:
            ...  # speech ended
    """

    def __init__(self) -> None:
        log.info(
            "Loading Silero VAD (onnx=%s, threshold=%.2f)",
            config.VAD_USE_ONNX,
            config.VAD_THRESHOLD,
        )
        self._model = load_silero_vad(onnx=config.VAD_USE_ONNX)
        self._iterator = VADIterator(
            self._model,
            threshold=config.VAD_THRESHOLD,
            sampling_rate=config.SAMPLE_RATE,
            min_silence_duration_ms=config.VAD_MIN_SILENCE_MS,
            speech_pad_ms=config.VAD_SPEECH_PAD_MS,
        )
        log.info("Silero VAD ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_chunk(
        self, audio_float32: torch.Tensor
    ) -> dict | None:
        """
        Feed one 512-sample float32 chunk through the VAD.

        Returns:
            {'start': float} — speech onset (seconds since stream start)
            {'end':   float} — speech ended (seconds since stream start)
            None             — no event (mid-speech or mid-silence)
        """
        return self._iterator(audio_float32, return_seconds=True)

    def reset(self) -> None:
        """Must be called between separate audio streams / sessions."""
        self._iterator.reset_states()
        log.debug("VAD state reset.")


# ------------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------------

def pcm16_bytes_to_float_tensor(raw: bytes) -> torch.Tensor:
    """
    Convert raw PCM int16 bytes (mono, 16 kHz) → float32 tensor in [-1, 1].

    This is the conversion that bridges pyaudio/sounddevice (int16 bytes)
    with Silero VAD (float32 tensor).
    """
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return torch.from_numpy(arr)


def rms_int16(raw: bytes) -> float:
    """
    Compute the Root-Mean-Square amplitude of a PCM int16 buffer.
    Used for fast silence skipping before bothering the VAD model.
    """
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(arr ** 2))) if len(arr) > 0 else 0.0
