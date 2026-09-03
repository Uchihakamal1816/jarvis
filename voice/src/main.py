"""
JARVIS Voice Layer — Main Entrypoint

Usage:
    python -m src.main                    # live microphone (default)
    python -m src.main --list-devices     # list available audio devices
    python -m src.main --check            # health check (model load test)
"""

from __future__ import annotations

import argparse
import sys

from .logger import get_logger
from . import config

log = get_logger("jarvis.voice")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jarvis-voice",
        description="JARVIS Voice Layer — Silero VAD + faster-whisper STT",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Health check: load VAD + STT models and exit with code 0 if OK.",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio device index (overrides AUDIO_DEVICE_INDEX env var).",
    )
    return parser.parse_args()


def cmd_list_devices() -> None:
    """Print available audio devices."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        print("\nAvailable audio devices:")
        print("─" * 60)
        print(devices)
        print("─" * 60)
        default_in = sd.query_devices(kind="input")
        print(f"\nDefault input: {default_in['name']}")
    except Exception as exc:
        print(f"Error listing devices: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_health_check() -> None:
    """Load both models and verify they are functional."""
    import time
    log.info("Running health check...")

    t0 = time.time()
    try:
        from .vad import VAD
        vad = VAD()
        log.info("✓ Silero VAD loaded (%.1fs)", time.time() - t0)
    except Exception as exc:
        log.error("✗ Silero VAD failed: %s", exc)
        sys.exit(1)

    t1 = time.time()
    try:
        from .stt import STT
        start_t = time.time()
        _ = STT()
        log.info("✓ Whisper STT loaded (%.1fs)", time.time() - start_t)
    except Exception as exc:
        log.error("✗ Whisper STT failed: %s", exc)
        sys.exit(1)

    log.info("✓ Health check passed (total %.1fs)", time.time() - t0)
    sys.exit(0)


def main() -> None:
    args = parse_args()

    # Apply CLI overrides
    if args.device is not None:
        import os
        os.environ["AUDIO_DEVICE_INDEX"] = str(args.device)

    if args.list_devices:
        cmd_list_devices()
        return

    if args.check:
        cmd_health_check()
        return

    # ── Normal run: start the live pipeline ──────────────────────────
    log.info("Starting JARVIS Voice Layer")
    log.info("  VAD       : Silero VAD (onnx=%s, threshold=%.2f)",
             config.VAD_USE_ONNX, config.VAD_THRESHOLD)
    log.info("  STT       : Whisper (%s)", config.WHISPER_MODEL_NAME)
    log.info("  Output    : %s", config.OUTPUT_MODE)
    log.info("  Sample rate: %d Hz", config.SAMPLE_RATE)

    from .pipeline import Pipeline
    pipeline = Pipeline()

    try:
        pipeline.run()
    except KeyboardInterrupt:
        log.info("Goodbye.")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
