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

    def route_brain_intent(self, user_input: str) -> tuple[str, str | None]:
        """
        Uses Groq LLM as the primary brain to analyze the query.
        Returns ("DIRECT", response_text) for casual conversation / general knowledge,
        or ("HERMES", None) for complex tasks requiring Hermes subagents / system tools.
        """
        if not self.client:
            return ("HERMES", None)

        system_prompt = (
            "You are the primary brain and intent router for JARVIS. Analyze the user prompt.\n"
            "Handle ALL facts, news, new topics, general knowledge, explanations, science, history, and casual conversation DIRECTLY.\n"
            "ONLY delegate to HERMES if the prompt explicitly requires local PC system commands (CPU/RAM/disk metrics, SSH health) "
            "or local PC folder/file code searching.\n\n"
            "Respond in EXACTLY one of two formats:\n\n"
            "Format 1 (For facts, news, new topics, general knowledge, explanations, and casual conversation):\n"
            "ACTION: DIRECT\n"
            "RESPONSE: <your concise, 1-2 sentence spoken response>\n\n"
            "Format 2 (ONLY for local PC system metrics, SSH checks, local folder search, or reading local PC code files):\n"
            "ACTION: HERMES"
        )

        try:
            completion = self.client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=120,
                temperature=0.1,
            )
            # Track Groq API call
            try:
                from .api_battery_tracker import api_battery
                api_battery.record_groq_call()
            except ImportError:
                pass

            content = (completion.choices[0].message.content or "").strip()
            log.info("Groq Brain Router decision: '%s'", content)

            if "ACTION: DIRECT" in content and "RESPONSE:" in content:
                response = content.split("RESPONSE:", 1)[1].strip()
                response = response.replace("*", "").replace("#", "")
                return ("DIRECT", response)

            return ("HERMES", None)

        except Exception as exc:
            log.error("Groq Brain Router failed: %s. Falling back to HERMES.", exc)
            return ("HERMES", None)

    def generate_direct_answer(self, user_input: str) -> str:
        """
        Uses Groq LLM to generate a direct 1-2 sentence spoken answer when primary agents are unavailable.
        """
        if not self.client:
            return "I am currently unable to reach the subagent network. Please try again."

        system_prompt = (
            "You are JARVIS. Answer the user prompt directly in 1 or 2 concise, confident spoken sentences "
            "suitable for text-to-speech. Omit markdown formatting, bullet points, and headers."
        )

        try:
            completion = self.client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                max_tokens=150,
                temperature=0.3,
            )
            # Track Groq API call
            try:
                from .api_battery_tracker import api_battery
                api_battery.record_groq_call()
            except ImportError:
                pass

            res = (completion.choices[0].message.content or "").strip()
            return res.replace("*", "").replace("#", "")
        except Exception as exc:
            log.error("Groq fallback generation failed: %s", exc)
            return "I am experiencing temporary network issues. Please try again shortly."


# Global singleton instance
groq_summarizer = GroqSummarizer()

