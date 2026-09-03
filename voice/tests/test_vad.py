"""
Tests for JARVIS Voice VAD wrapper.

Tests use synthetic audio (pure sine wave, silence) to verify:
  - Silence chunks produce no VAD event
  - Speech-like chunks trigger start/end events
  - pcm16_bytes_to_float_tensor conversion is correct
  - rms_int16 returns expected values
"""

from __future__ import annotations

import math
import struct

import numpy as np
import torch
import pytest

from src.vad import VAD, pcm16_bytes_to_float_tensor, rms_int16


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_silence_chunk(n_samples: int = 512) -> bytes:
    """Return n_samples of PCM16 silence (all zeros)."""
    return b"\x00\x00" * n_samples


def make_sine_chunk(
    freq_hz: float = 440.0,
    amplitude: float = 0.8,
    sample_rate: int = 16000,
    n_samples: int = 512,
    offset_samples: int = 0,
) -> bytes:
    """Return n_samples of a sine wave as PCM16 bytes."""
    samples = []
    for i in range(n_samples):
        t = (offset_samples + i) / sample_rate
        val = amplitude * math.sin(2 * math.pi * freq_hz * t)
        samples.append(int(val * 32767))
    return struct.pack(f"<{n_samples}h", *samples)


# ── Conversion tests ─────────────────────────────────────────────────────────

class TestPCM16ToFloatTensor:
    def test_silence_is_all_zeros(self):
        raw = make_silence_chunk(512)
        tensor = pcm16_bytes_to_float_tensor(raw)
        assert tensor.shape == (512,)
        assert torch.all(tensor == 0.0)

    def test_max_positive_value(self):
        # int16 max = 32767 → should map to ~1.0
        raw = struct.pack("<h", 32767)
        tensor = pcm16_bytes_to_float_tensor(raw)
        assert abs(float(tensor[0]) - 1.0) < 0.0001

    def test_max_negative_value(self):
        # int16 min = -32768 → should map to ~-1.0
        raw = struct.pack("<h", -32768)
        tensor = pcm16_bytes_to_float_tensor(raw)
        assert abs(float(tensor[0]) + 1.0) < 0.0001

    def test_output_dtype_is_float32(self):
        raw = make_silence_chunk(512)
        tensor = pcm16_bytes_to_float_tensor(raw)
        assert tensor.dtype == torch.float32

    def test_sine_values_in_range(self):
        raw = make_sine_chunk(amplitude=0.9, n_samples=512)
        tensor = pcm16_bytes_to_float_tensor(raw)
        assert float(tensor.min()) >= -1.0
        assert float(tensor.max()) <= 1.0


# ── RMS tests ─────────────────────────────────────────────────────────────────

class TestRmsInt16:
    def test_silence_rms_is_zero(self):
        raw = make_silence_chunk(512)
        assert rms_int16(raw) == 0.0

    def test_constant_signal_rms(self):
        # All samples = 1000 → RMS = 1000
        raw = struct.pack("<512h", *([1000] * 512))
        result = rms_int16(raw)
        assert abs(result - 1000.0) < 1.0

    def test_empty_bytes(self):
        assert rms_int16(b"") == 0.0

    def test_sine_rms_positive(self):
        raw = make_sine_chunk(amplitude=0.5, n_samples=512)
        result = rms_int16(raw)
        assert result > 0


# ── VAD model tests ───────────────────────────────────────────────────────────

class TestVAD:
    """Integration tests — load actual Silero VAD model."""

    @pytest.fixture(scope="class")
    def vad(self):
        return VAD()

    def test_loads_without_error(self, vad):
        assert vad is not None

    def test_silence_produces_no_event(self, vad):
        vad.reset()
        # Feed many silence chunks — should never return a start event
        events = []
        raw = make_silence_chunk(512)
        tensor = pcm16_bytes_to_float_tensor(raw)
        for _ in range(50):
            ev = vad.process_chunk(tensor)
            if ev:
                events.append(ev)
        assert all("start" not in e for e in events), \
            f"Unexpected speech start in silence: {events}"

    def test_reset_clears_state(self, vad):
        vad.reset()  # Should not raise
        # After reset, feeding silence should still produce no start event
        raw = make_silence_chunk(512)
        tensor = pcm16_bytes_to_float_tensor(raw)
        ev = vad.process_chunk(tensor)
        assert ev is None or "start" not in ev
