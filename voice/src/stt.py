"""
JARVIS Voice Layer — Whisper STT Wrapper (faster-whisper backend)

Uses faster-whisper (CTranslate2) for 4-8x faster CPU inference vs openai-whisper.

Key optimizations:
  - int8 quantization: halves memory, speeds up CPU math kernels
  - beam_size=1: greedy decoding — fastest path, negligible accuracy drop
  - language="en": skips language detection step (~50ms saved per call)
  - condition_on_previous_text=False: no cross-utterance context carry-over
  - Model pre-warmed on __init__: first utterance is as fast as subsequent ones

Audio contract:
  - PCM int16, mono, 16 kHz bytes
  - Converted internally to float32 normalized [-1.0, 1.0]
"""

from __future__ import annotations

import time
import numpy as np

try:
    from faster_whisper import WhisperModel
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "faster-whisper is not installed. Run: pip install faster-whisper"
    ) from exc

from . import config
from .logger import get_logger

log = get_logger(__name__)


class STT:
    """
    faster-whisper STT wrapper.

    Loads the model once, pre-warms it, and exposes a single
    `transcribe(pcm16_bytes)` method for whole-utterance transcription.
    """

    def __init__(self) -> None:
        log.info(
            "Loading Whisper '%s' via faster-whisper (device=cpu, compute=int8, threads=%d)...",
            config.WHISPER_MODEL_NAME,
            config.WHISPER_CPU_THREADS,
        )
        self._model = WhisperModel(
            config.WHISPER_MODEL_NAME,
            device="cpu",
            compute_type="int8",
            cpu_threads=config.WHISPER_CPU_THREADS,
        )

        # Pre-warm: first CTranslate2 call initialises JIT kernels.
        # Sending a 0.5s silent dummy eliminates cold-start latency on the
        # first real utterance.
        log.info("Pre-warming Whisper model...")
        dummy = np.zeros(int(config.SAMPLE_RATE * 0.5), dtype=np.float32)
        list(self._model.transcribe(
            dummy,
            language=config.WHISPER_LANGUAGE,
            beam_size=config.WHISPER_BEAM_SIZE,
        )[0])  # consume generator to actually run inference
        log.info("Whisper STT ready.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transcribe(self, pcm16_bytes: bytes) -> FinalResult:
        """
        Transcribe a complete speech utterance.

        Args:
            pcm16_bytes: Raw PCM16 audio bytes (mono, 16 kHz).

        Returns:
            FinalResult with transcribed text.
        """
        if not pcm16_bytes:
            return FinalResult(text="")

        # Convert raw PCM16 → float32 in [-1.0, 1.0] (Whisper's expected format)
        audio_np = (
            np.frombuffer(pcm16_bytes, dtype=np.int16)
            .astype(np.float32) / 32768.0
        )

        t0 = time.perf_counter()
        segments, _ = self._model.transcribe(
            audio_np,
            language=config.WHISPER_LANGUAGE,
            beam_size=config.WHISPER_BEAM_SIZE,
            condition_on_previous_text=False,  # no cross-utterance context
            no_speech_threshold=config.WHISPER_NO_SPEECH_THRESHOLD,
            temperature=0.0,                   # deterministic, no sampling
        )

        # `segments` is a lazy generator — consume it fully to get all text
        text = " ".join(s.text.strip() for s in segments).strip()
        elapsed = time.perf_counter() - t0
        audio_duration = len(audio_np) / config.SAMPLE_RATE

        log.info(
            "STT [%.2fs audio → %.2fs transcribe, RTF=%.2f]: '%s'",
            audio_duration, elapsed,
            elapsed / max(audio_duration, 0.001),
            text,
        )
        return FinalResult(text=text)

    def reset(self) -> None:
        """No state to reset — faster-whisper is stateless per call."""
        pass


# ------------------------------------------------------------------
# Result data class
# ------------------------------------------------------------------

class FinalResult:
    """Complete recognition result for a full utterance."""

    __slots__ = ("text", "words")

    def __init__(self, text: str, words: list | None = None) -> None:
        self.text = text
        self.words = words or []

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    def __repr__(self) -> str:
        return f"FinalResult(text={self.text!r})"
