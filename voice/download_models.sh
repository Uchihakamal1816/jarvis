#!/usr/bin/env bash
# JARVIS Voice Layer — Download Models
#
# Pre-downloads the required models (Silero VAD ONNX + Whisper STT)
# so they are cached locally and don't delay the first startup.

set -e

# Default to the small model if not specified
WHISPER_MODEL=${1:-small}

echo "==========================================="
echo " JARVIS Model Downloader (Whisper & VAD)   "
echo "==========================================="

# Ensure we're in the virtual environment if it exists locally
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

echo "1. Downloading Silero VAD (ONNX)..."
python -c "
from silero_vad import load_silero_vad
load_silero_vad(onnx=True)
print('✓ Silero VAD downloaded/cached.')
"

echo "-------------------------------------------"
echo "2. Downloading Whisper model: $WHISPER_MODEL ..."
python -c "
import whisper
whisper.load_model('$WHISPER_MODEL')
print('✓ Whisper model ($WHISPER_MODEL) downloaded/cached.')
"

echo "==========================================="
echo " All models downloaded successfully!       "
echo "==========================================="
