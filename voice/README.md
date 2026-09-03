# JARVIS Voice Layer

> **Phase 1 of JARVIS** — Voice Activity Detection + Speech-to-Text  
> `Listen. Understand. Plan. Delegate. Act.`

## What This Does

Streams live microphone audio → detects speech with **Silero VAD** → transcribes with **Vosk STT** → emits structured JSON events.

```
Microphone
    │
    ▼ (PCM 16kHz mono int16)
Silero VAD  ──silence──►  [skip]
    │
    └──speech──►  Pre-roll buffer flush
                       │
                       ▼
                  Vosk KaldiRecognizer
                       │
                       ▼
              {"event": "transcript", "text": "...", ...}
```

## Stack

| Component | Library | Why |
|-----------|---------|-----|
| VAD | `silero-vad 6.2.1` (ONNX) | Fastest CPU VAD, stateful streaming |
| STT | `openai-whisper` | Highly accurate offline STT (small model) |
| Audio | `sounddevice` | Clean Python mic capture |
| Runtime | `onnxruntime` | Replaces full PyTorch for VAD |

## Quick Start (Native)

Since direct microphone access is best handled outside virtualization layers, we run this natively in a Python virtual environment.

### 1. Install System Dependencies (Linux)

You need PortAudio development headers for `sounddevice` to compile:

```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3.11-venv
```

### 2. Setup Python Environment

```bash
cd voice/

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install CPU-only torch first (avoids massive GPU downloads)
pip install --index-url https://download.pytorch.org/whl/cpu torch==2.3.1+cpu torchaudio==2.3.1+cpu

# Install the rest of the dependencies
pip install -r requirements.txt
```

### 3. Download the Model

We use the small Whisper model by default (downloads automatically to `~/.cache/whisper/`).

```bash
./download_models.sh small
```

### 4. Run the Pipeline

```bash
python -m src.main
```

## Configuration

Copy `.env.example` to `.env` and adjust settings. All configuration is loaded from environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `VAD_THRESHOLD` | `0.5` | VAD sensitivity. Raise (0.6–0.8) in noisy rooms |
| `VAD_MIN_SILENCE_MS` | `500` | ms of silence before utterance ends |
| `VAD_USE_ONNX` | `true` | Use ONNX runtime (faster, no full torch needed) |
| `WHISPER_MODEL_NAME`| `small` | Which Whisper model to use (tiny, base, small) |
| `OUTPUT_MODE` | `stdout` | `stdout` or `webhook` |
| `WEBHOOK_URL` | `` | Target URL for webhook mode |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_JSON` | `false` | Emit structured JSON logs |
| `AUDIO_DEVICE_INDEX` | _(default mic)_ | Force specific device index if multiple mics exist |

## Output Events

All events are emitted as JSON on stdout (one per line):

```json
// Speech onset detected
{"event": "speech_start", "timestamp": 1724408340.0}

// Speech ended (Whisper starts transcribing)
{"event": "speech_end", "timestamp": 1724408341.2}

// Final transcript for this utterance
{
  "event": "transcript",
  "text": "hello jarvis",
  "is_final": true,
  "confidence": 0.96,
  "duration_ms": 1200,
  "timestamp": 1724408341.2,
  "words": []
}
```

## Running Tests

```bash
# Inside the activated virtual environment
python -m pytest tests/ -v
```

## Architecture Notes

- **Pre-roll buffer**: 200ms of audio is buffered before VAD triggers. When speech is detected, the buffer is saved to avoid missing speech onset.
- **ONNX VAD**: Silero VAD runs via `onnxruntime` instead of full PyTorch. Identical accuracy, ~3x faster inference.
- **Offline Whisper**: Whisper model is loaded once at startup. When speech ends, the complete utterance buffer is passed for transcription.
- **RMS fast-path**: Chunks below `AUDIO_SILENCE_SKIP_RMS` RMS skip VAD entirely when in IDLE state — saves CPU during long silences.
- **Thread model**: Single processing thread with a bounded queue (200 chunks) prevents memory growth during busy periods.

---

*Part of [JARVIS](../JARVIS_PROJECT_SPEC.md) — Voice-First Multi-Agent AI Operating System*
