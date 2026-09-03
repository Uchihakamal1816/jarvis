"""
JARVIS Voice Layer — Configuration
All settings are driven by environment variables with sensible defaults.
"""

import os


# ── Audio ─────────────────────────────────────────────────────────────────────
SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
VAD_CHUNK_SAMPLES: int = 512          # MUST be 512 at 16 kHz for Silero VAD
VAD_CHUNK_BYTES: int = VAD_CHUNK_SAMPLES * 2   # int16 = 2 bytes/sample
PRE_ROLL_CHUNKS: int = int(
    int(os.getenv("VAD_PADDING_MS", "100")) / 1000 * SAMPLE_RATE / VAD_CHUNK_SAMPLES
)   # ~100 ms pre-roll (reduced from 200ms — saves Whisper processing time)

# ── Silero VAD ────────────────────────────────────────────────────────────────
VAD_THRESHOLD: float = float(os.getenv("VAD_THRESHOLD", "0.5"))
VAD_MIN_SILENCE_MS: int = int(os.getenv("VAD_MIN_SILENCE_MS", "900"))  # 900ms silence threshold allows natural mid-sentence pauses
VAD_SPEECH_PAD_MS: int = int(os.getenv("VAD_SPEECH_PAD_MS", "100"))
VAD_USE_ONNX: bool = os.getenv("VAD_USE_ONNX", "true").lower() == "true"

# ── Wake Word (openwakeword) ──────────────────────────────────────────────────
WAKE_WORD_ENABLED: bool = os.getenv("WAKE_WORD_ENABLED", "true").lower() == "true"
WAKE_WORD_MODEL: str = os.getenv("WAKE_WORD_MODEL", "hey_jarvis") # e.g. hey_jarvis, alexa, hey_mycroft
WAKE_WORD_THRESHOLD: float = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))

# ── Text-to-Speech (edge-tts) ─────────────────────────────────────────────────
TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() == "true"
# Default to a nice British male voice (Christopher), or "en-US-GuyNeural"
TTS_VOICE: str = os.getenv("TTS_VOICE", "en-GB-ThomasNeural") 
TTS_RATE: str = os.getenv("TTS_RATE", "+0%") # e.g., "+10%" for faster, "-10%" for slower

# ── Whisper STT (faster-whisper) ──────────────────────────────────────────────
WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "small")
WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "en")           # skip language detection
WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "1"))     # greedy decode — fastest
WHISPER_NO_SPEECH_THRESHOLD: float = float(os.getenv("WHISPER_NO_SPEECH_THRESHOLD", "0.6"))
# Number of CPU threads for CTranslate2 (0 = auto-detect based on CPU count)
WHISPER_CPU_THREADS: int = int(os.getenv("WHISPER_CPU_THREADS", "4"))
# Max utterance length before force-cutting (avoids slow transcription of very long audio)
MAX_UTTERANCE_MS: int = int(os.getenv("MAX_UTTERANCE_MS", "15000"))

# ── Audio Input ───────────────────────────────────────────────────────────────
AUDIO_DEVICE_INDEX: int | None = (
    int(os.getenv("AUDIO_DEVICE_INDEX"))
    if os.getenv("AUDIO_DEVICE_INDEX")
    else None
)
# Silence threshold (int16 RMS) below which we skip VAD to save CPU
AUDIO_SILENCE_SKIP_RMS: int = int(os.getenv("AUDIO_SILENCE_SKIP_RMS", "50"))

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_MODE: str = os.getenv("OUTPUT_MODE", "stdout")   # stdout | webhook
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
WEBHOOK_TIMEOUT_S: float = float(os.getenv("WEBHOOK_TIMEOUT_S", "5.0"))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_JSON: bool = os.getenv("LOG_JSON", "false").lower() == "true"
