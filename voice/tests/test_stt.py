"""
Tests for JARVIS Voice STT wrapper.

Tests verify:
  - STT loads model without error
  - Feeding silence produces empty/no partial text
  - FinalResult on silence returns empty text
  - PartialResult and FinalResult data classes work correctly
  - Reset clears state without reloading model
"""

from __future__ import annotations

import struct

import pytest

from src.stt import STT, PartialResult, FinalResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_silence_bytes(n_samples: int = 8192) -> bytes:
    """Return PCM16 silence."""
    return b"\x00\x00" * n_samples


# ── PartialResult tests ───────────────────────────────────────────────────────

class TestPartialResult:
    def test_is_final_false(self):
        pr = PartialResult(text="hello", is_final=False, words=[])
        assert pr.is_final is False

    def test_repr_contains_text(self):
        pr = PartialResult(text="world", is_final=False, words=[])
        assert "world" in repr(pr)

    def test_is_final_true(self):
        pr = PartialResult(text="done", is_final=True, words=[])
        assert pr.is_final is True


# ── FinalResult tests ─────────────────────────────────────────────────────────

class TestFinalResult:
    def test_is_empty_on_blank_text(self):
        fr = FinalResult(text="", words=[])
        assert fr.is_empty is True

    def test_is_empty_on_whitespace(self):
        fr = FinalResult(text="   ", words=[])
        assert fr.is_empty is True

    def test_not_empty_with_text(self):
        fr = FinalResult(text="hello jarvis", words=[])
        assert fr.is_empty is False

    def test_repr(self):
        fr = FinalResult(text="test", words=[{"word": "test"}])
        assert "test" in repr(fr)


# ── STT model integration tests ───────────────────────────────────────────────

class TestSTT:
    """Integration tests — load actual Vosk model."""

    @pytest.fixture(scope="class")
    def stt(self):
        return STT()

    def test_loads_without_error(self, stt):
        assert stt is not None

    def test_finalize_silence_returns_empty(self, stt):
        stt.reset()
        silence = make_silence_bytes(16000)  # 1 second of silence
        stt.feed(silence)
        result = stt.finalize()
        assert isinstance(result, FinalResult)
        assert result.is_empty

    def test_reset_does_not_raise(self, stt):
        stt.reset()  # Should not throw
        stt.reset()  # Idempotent

    def test_feed_returns_none_or_partial_on_silence(self, stt):
        stt.reset()
        silence = make_silence_bytes(512)
        result = stt.feed(silence)
        # Silence should return None or a PartialResult with empty text
        assert result is None or (
            isinstance(result, PartialResult) and result.text.strip() == ""
        )

    def test_final_result_has_words_list(self, stt):
        stt.reset()
        stt.feed(make_silence_bytes(8192))
        result = stt.finalize()
        assert isinstance(result.words, list)
