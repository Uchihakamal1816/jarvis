"""
JARVIS Voice Layer — Audio Capture

Captures raw PCM16 audio from the system microphone using sounddevice.
Runs in its own thread and pushes chunks into a queue consumed by the pipeline.

Audio format contract:
  - Sample rate: 16000 Hz (SAMPLE_RATE)
  - Channels: 1 (mono)
  - dtype: int16 (paInt16 equivalent)
  - Chunk size: VAD_CHUNK_SAMPLES = 512 samples = 1024 bytes = ~32ms
"""

from __future__ import annotations

import queue
import threading
import time

import numpy as np

try:
    import sounddevice as sd
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "sounddevice is not installed. Run: pip install sounddevice"
    ) from exc

from . import config
from .logger import get_logger

log = get_logger(__name__)

# Sentinel object to signal the audio thread has stopped
_STOP_SENTINEL = object()


class AudioCapture:
    """
    Microphone audio capture using sounddevice.

    Puts raw PCM int16 byte chunks into `out_queue`.
    Each chunk is exactly VAD_CHUNK_BYTES (1024 bytes / 512 samples / ~32ms).

    Usage::

        q = queue.Queue()
        capture = AudioCapture(out_queue=q)
        capture.start()

        while True:
            chunk = q.get()
            if chunk is None:
                break  # stopped
            process(chunk)  # bytes

        capture.stop()
    """

    def __init__(
        self,
        out_queue: queue.Queue,
        device_index: int | None = None,
    ) -> None:
        self._queue = out_queue
        self._device = device_index if device_index is not None else config.AUDIO_DEVICE_INDEX
        self._stream: sd.RawInputStream | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open the microphone stream and start capturing."""
        device_info = self._get_device_info()
        log.info(
            "Opening mic: device=%s, rate=%d Hz, chunk=%d samples (~%dms)",
            device_info,
            config.SAMPLE_RATE,
            config.VAD_CHUNK_SAMPLES,
            int(config.VAD_CHUNK_SAMPLES / config.SAMPLE_RATE * 1000),
        )
        self._stop_event.clear()
        self._stream = sd.RawInputStream(
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=config.VAD_CHUNK_SAMPLES,
            device=self._device,
            callback=self._audio_callback,
        )
        self._stream.start()
        log.info("Microphone capture started. Listening...")

    def stop(self) -> None:
        """Stop the microphone stream and push a stop sentinel into the queue."""
        self._stop_event.set()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._queue.put(None)  # signal consumers to stop
        log.info("Microphone capture stopped.")

    def list_devices(self) -> None:
        """Print available audio devices (useful for debugging in Docker)."""
        print(sd.query_devices())

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _audio_callback(
        self,
        indata: bytes,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """sounddevice callback — called from a C thread, must be fast."""
        if status:
            log.warning("Audio callback status: %s", status)
        if self._stop_event.is_set():
            raise sd.CallbackStop()
        # indata is a memoryview; copy to bytes before queueing
        self._queue.put(bytes(indata), block=False)

    def _get_device_info(self) -> str:
        if self._device is None:
            try:
                info = sd.query_devices(kind="input")
                return f"{info.get('name', 'default')} (default)"
            except Exception:
                return "default"
        try:
            info = sd.query_devices(self._device)
            return f"{info.get('name', 'unknown')} (idx={self._device})"
        except Exception:
            return f"device #{self._device}"
