"""
JARVIS Core — Groq Response Summarizer / Improviser
Uses Groq LLM (e.g. qwen/qwen3.8-27b or groq/compound-mini) to condense raw Hermes agent outputs
into ultra-crisp, 1-2 sentence spoken responses for voice output.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

try:
    from groq import Groq
except ImportError:
    Groq = None


class GroqSummarizer:
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key and Groq else None
        if self.client:
            log.info("GroqSummarizer connected successfully.")
        else:
            log.warning("GROQ_API_KEY missing or groq library not installed. Summarizer in bypass mode.")

    def condense_response(self, raw_response: str) -> str:
        """
        Uses Groq LLM to rewrite and improvise raw agent responses into concise, spoken 1-2 sentence statements.
        """
        if not self.client or not raw_response.strip():
            return raw_response

        # Skip summarization if response is already very short (under 120 chars)
        if len(raw_response) < 120:
            return raw_response

        system_prompt = (
            "You are JARVIS's voice improviser. Rewrite raw technical outputs into 1 or 2 short, crisp, "
            "confident spoken sentences for direct voice delivery. Omit bullet points, markdown formatting, "
            "asterisks, and redundant headers. State key facts directly and naturally."
        )

        try:
            completion = self.client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_response},
                ],
                max_tokens=100,
                temperature=0.2,
            )
            # Track Groq API call
            try:
                from .api_battery_tracker import api_battery
                api_battery.record_groq_call()
            except ImportError:
                pass

            condensed = completion.choices[0].message.content or raw_response
            condensed = condensed.strip().replace("*", "").replace("#", "")
            if condensed:
                log.info("Groq condensed response: '%s'", condensed)
                return condensed
        except Exception as exc:
            log.error("Groq summarization failed, returning raw response: %s", exc)

        return raw_response


# Global singleton instance
groq_summarizer = GroqSummarizer()
