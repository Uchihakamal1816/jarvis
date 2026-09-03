"""
JARVIS Core — API Battery & Rate-Limit Tracker
Tracks sliding 60-second window API usage and remaining quota for Google Antigravity (Gemini) & Groq.
"""

import time
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

# Default Free Tier Limits per minute (60s sliding window)
GEMINI_MAX_RPM = 15
GEMINI_MAX_TPM = 1_000_000

GROQ_MAX_RPM = 30
GROQ_MAX_TPM = 14_400


class APIBatteryTracker:
    def __init__(self):
        # Timestamps of calls within the last 60 seconds
        self.gemini_calls: list[tuple[float, int]] = []  # (timestamp, tokens)
        self.groq_calls: list[tuple[float, int]] = []    # (timestamp, tokens)

    def _cleanup_expired(self, current_time: float) -> None:
        """Removes calls older than 60 seconds."""
        cutoff = current_time - 60.0
        self.gemini_calls = [c for c in self.gemini_calls if c[0] > cutoff]
        self.groq_calls = [c for c in self.groq_calls if c[0] > cutoff]

    def record_gemini_call(self, tokens: int = 1500) -> None:
        """Records a Gemini / Antigravity API invocation."""
        now = time.time()
        self._cleanup_expired(now)
        self.gemini_calls.append((now, tokens))

    def record_groq_call(self, tokens: int = 100) -> None:
        """Records a Groq API invocation."""
        now = time.time()
        self._cleanup_expired(now)
        self.groq_calls.append((now, tokens))

    def get_status(self) -> Dict[str, Any]:
        """Calculates current API usage, remaining quota, and overall battery percentage."""
        now = time.time()
        self._cleanup_expired(now)

        gemini_rpm_used = len(self.gemini_calls)
        gemini_tpm_used = sum(c[1] for c in self.gemini_calls)

        groq_rpm_used = len(self.groq_calls)
        groq_tpm_used = sum(c[1] for c in self.groq_calls)

        gemini_rpm_left = max(0, GEMINI_MAX_RPM - gemini_rpm_used)
        groq_rpm_left = max(0, GROQ_MAX_RPM - groq_rpm_used)

        # Calculate battery percentage based on call headroom
        gemini_pct = (gemini_rpm_left / GEMINI_MAX_RPM) * 100
        groq_pct = (groq_rpm_left / GROQ_MAX_RPM) * 100
        overall_battery_pct = round((gemini_pct + groq_pct) / 2)

        return {
            "battery_pct": overall_battery_pct,
            "gemini_rpm_left": gemini_rpm_left,
            "gemini_rpm_max": GEMINI_MAX_RPM,
            "groq_rpm_left": groq_rpm_left,
            "groq_rpm_max": GROQ_MAX_RPM,
            "gemini_tpm_used": gemini_tpm_used,
            "groq_tpm_used": groq_tpm_used,
        }

    def get_battery_speech_summary(self) -> str:
        """Generates a natural spoken summary for voice output."""
        st = self.get_status()
        return (
            f"API battery is at {st['battery_pct']} percent. "
            f"You have {st['gemini_rpm_left']} of {st['gemini_rpm_max']} Antigravity calls "
            f"and {st['groq_rpm_left']} of {st['groq_rpm_max']} Groq calls remaining for this minute."
        )


# Global singleton instance
api_battery = APIBatteryTracker()
