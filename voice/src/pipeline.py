"""
JARVIS Voice Layer — VAD + STT Pipeline (Optimized)

Three-thread architecture for zero dead-time between utterances:

    Thread 1 — Audio Capture (sounddevice callback, real-time)
        Mic → raw_queue

    Thread 2 — VAD Gate (main processing loop)
        raw_queue → [RMS fast-path] → [Silero VAD] → utterance_buffer
        On speech_end: pushes buffer to transcribe_queue, immediately returns to IDLE

    Thread 3 — STT Worker (dedicated transcription thread)
        transcribe_queue → [faster-whisper] → OutputHandler

State machine (Thread 2):
    IDLE  ──(speech_start)──►  SPEAKING  ──(speech_end)──►  IDLE  (immediately)
                                                │
                                                ▼  (non-blocking push)
                                        transcribe_queue
                                                │
                                          [Thread 3 picks up]
                                                ▼
                                         emit transcript

Key benefit: Thread 2 is back in IDLE the instant you stop speaking.
Thread 3 transcribes in parallel — so you can start your next utterance
while the previous one is still being processed.
"""

from __future__ import annotations

import collections
import queue
import threading
import time

from .audio_capture import AudioCapture
from .vad import VAD, pcm16_bytes_to_float_tensor, rms_int16
from .wakeword import WakeWordEngine
from .stt import STT
from .output import OutputHandler
from . import config
from .logger import get_logger

log = get_logger(__name__)

# Pipeline states
_SLEEPING = "SLEEPING"
_IDLE = "IDLE"
_SPEAKING = "SPEAKING"


class Pipeline:
    """
    Optimized JARVIS voice pipeline.

    Three-thread design eliminates dead-time between utterances:
      - Audio capture runs continuously on its own thread.
      - VAD processes chunks and immediately returns to IDLE after speech ends.
      - STT transcribes previous utterance in parallel on a dedicated thread.

    Usage::

        pipeline = Pipeline()
        pipeline.run()         # blocks; press Ctrl-C to stop
    """

    def __init__(self) -> None:
        # Audio → VAD queue (bounded to prevent memory growth)
        self._raw_queue: queue.Queue[bytes | None] = queue.Queue(maxsize=300)

        # VAD → STT handoff queue
        # Each item: (audio_bytes, speech_start_time)
        self._transcribe_queue: queue.Queue[tuple[bytes, float] | None] = queue.Queue()

        self._capture = AudioCapture(out_queue=self._raw_queue)
        self._wakeword = WakeWordEngine()
        self._vad = VAD()
        self._stt = STT()
        self._output = OutputHandler()

        # Pre-roll ring buffer: keeps last N chunks before speech detected
        # Reduced to 100ms (from 200ms) — trims Whisper input size
        self._pre_roll: collections.deque[bytes] = collections.deque(
            maxlen=config.PRE_ROLL_CHUNKS
        )

        self._state: str = _SLEEPING if config.WAKE_WORD_ENABLED else _IDLE
        self._speech_start_time: float = 0.0
        self._utterance_buffer = bytearray()
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the pipeline and block until stopped (Ctrl-C)."""
        self._capture.start()

        # Thread 2: VAD processing loop
        vad_thread = threading.Thread(
            target=self._vad_loop, name="jarvis-vad", daemon=True
        )
        vad_thread.start()

        # Thread 3: STT transcription loop (runs in parallel with VAD)
        stt_thread = threading.Thread(
            target=self._stt_loop, name="jarvis-stt", daemon=True
        )
        stt_thread.start()

        log.info("═══════════════════════════════════════════════")
        log.info("  JARVIS Voice Layer — Listening (optimized)  ")
        log.info("  VAD silence: %dms | Beam: %d | Lang: %s      ",
                 config.VAD_MIN_SILENCE_MS,
                 config.WHISPER_BEAM_SIZE,
                 config.WHISPER_LANGUAGE)
        log.info("  Ctrl-C to stop                               ")
        log.info("═══════════════════════════════════════════════")

        try:
            vad_thread.join()
        except KeyboardInterrupt:
            log.info("Interrupted — shutting down.")
            self.stop()
            vad_thread.join(timeout=3)
            # Signal STT thread to stop
            self._transcribe_queue.put(None)
            stt_thread.join(timeout=10)

    def stop(self) -> None:
        """Signal the pipeline to stop gracefully."""
        self._stop_event.set()
        self._capture.stop()

    # ------------------------------------------------------------------
    # Thread 2: VAD loop — fast, never blocks on STT
    # ------------------------------------------------------------------

    def _vad_loop(self) -> None:
        """VAD processing loop. Never blocks on STT — just pushes to transcribe_queue."""
        log.debug("VAD thread started.")
        from .tts import tts_engine
        try:
            while not self._stop_event.is_set():
                try:
                    chunk = self._raw_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if chunk is None:
                    break  # stop sentinel
                    
                if tts_engine.is_playing:
                    # Drop audio chunks while TTS is active to avoid echo loops
                    if self._state == _SPEAKING:
                        log.debug("TTS playing mid-utterance. Force-ending utterance.")
                        self._on_speech_end()
                    self._pre_roll.clear()
                    continue

                self._process_chunk(chunk)

        except Exception as exc:
            log.exception("Fatal error in VAD loop: %s", exc)
        finally:
            # Flush any in-progress utterance
            if self._state == _SPEAKING and self._utterance_buffer:
                self._push_to_stt()
            # Signal STT thread to stop
            self._transcribe_queue.put(None)
            log.debug("VAD thread stopped.")

    def _process_chunk(self, raw_bytes: bytes) -> None:
        """Process one 512-sample PCM16 chunk through VAD."""

        # Fast path: skip VAD entirely for very quiet chunks in IDLE state
        if rms_int16(raw_bytes) < config.AUDIO_SILENCE_SKIP_RMS and self._state == _IDLE:
            self._pre_roll.append(raw_bytes)
            return

        # Convert to float32 tensor for Silero VAD
        chunk_tensor = pcm16_bytes_to_float_tensor(raw_bytes)
        vad_event = self._vad.process_chunk(chunk_tensor)

        # ── SLEEPING ──────────────────────────────────────────────────
        if self._state == _SLEEPING:
            # Drop pre-roll in sleeping mode
            self._pre_roll.clear()
            if self._wakeword.process_chunk(raw_bytes):
                log.info("Wake word triggered! Transitioning to IDLE.")
                print("\n[JARVIS] Hi Kamal, I am listening...")
                
                # Speak greeting in a background thread so we don't block audio capture
                import threading
                from .tts import tts_engine
                threading.Thread(target=tts_engine.speak, args=("Hi Kamal, I am listening",), daemon=True).start()
                
                self._state = _IDLE
            return

        # ── IDLE ──────────────────────────────────────────────────────
        elif self._state == _IDLE:
            self._pre_roll.append(raw_bytes)

            if vad_event and "start" in vad_event:
                self._on_speech_start(raw_bytes)

        # ── SPEAKING ──────────────────────────────────────────────────
        elif self._state == _SPEAKING:
            self._utterance_buffer.extend(raw_bytes)

            # Force-cut if utterance exceeds max duration (avoids runaway long audio)
            elapsed_ms = (time.time() - self._speech_start_time) * 1000
            if elapsed_ms > config.MAX_UTTERANCE_MS:
                log.debug("Max utterance length reached — force-ending.")
                self._on_speech_end()
            elif vad_event and "end" in vad_event:
                self._on_speech_end()

    # ------------------------------------------------------------------
    # State transitions (run in VAD thread — must not block)
    # ------------------------------------------------------------------

    def _on_speech_start(self, triggering_chunk: bytes) -> None:
        """Transition IDLE → SPEAKING."""
        self._state = _SPEAKING
        self._speech_start_time = time.time()
        log.debug("▶ Speech start.")
        self._output.emit_speech_start()

        # Flush pre-roll into utterance buffer (preserve speech onset)
        for buffered in self._pre_roll:
            self._utterance_buffer.extend(buffered)
        self._pre_roll.clear()
        self._utterance_buffer.extend(triggering_chunk)

    def _on_speech_end(self) -> None:
        """Transition SPEAKING → IDLE. Non-blocking — STT runs in Thread 3."""
        log.debug("◼ Speech end — pushing to STT queue.")
        self._output.emit_speech_end()
        self._push_to_stt()
        # Keep the session live by returning to IDLE instead of SLEEPING
        self._state = _IDLE
        self._vad.reset()

    def _push_to_stt(self) -> None:
        """Snapshot the utterance buffer and enqueue for async transcription."""
        audio_snapshot = bytes(self._utterance_buffer)
        speech_start = self._speech_start_time
        self._utterance_buffer.clear()
        self._transcribe_queue.put((audio_snapshot, speech_start))

    # ------------------------------------------------------------------
    # Thread 3: STT loop — runs faster-whisper, emits transcripts
    # ------------------------------------------------------------------

    def _stt_loop(self) -> None:
        """
        Dedicated transcription thread.
        Drains the transcribe_queue independently of the VAD loop.
        This means the mic is always listening — even while Whisper is running.
        """
        log.debug("STT thread started.")
        while True:
            try:
                item = self._transcribe_queue.get(timeout=1.0)
            except queue.Empty:
                if self._stop_event.is_set():
                    break
                continue

            if item is None:
                break  # shutdown sentinel

            audio_bytes, speech_start_time = item
            duration_ms = int((time.time() - speech_start_time) * 1000)

            result = self._stt.transcribe(audio_bytes)

            if result.is_empty:
                log.debug("Empty transcript — skipping emit.")
            else:
                self._output.emit_transcript(
                    text=result.text,
                    words=result.words,
                    duration_ms=duration_ms,
                )

        log.debug("STT thread stopped.")
