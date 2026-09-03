"""
JARVIS Core — Intent Router
Takes raw text, routes it to Hermes Orchestration Layer (Google Antigravity SDK),
and improvises/condenses responses using Groq LLM for ultra-crisp voice output.
Contains fast-path detection for API battery & quota limit checks.
"""

import logging
import asyncio
from .session import Session
from .groq_summarizer import groq_summarizer
from .api_battery_tracker import api_battery

try:
    from hermes_orchestrator import process_with_agents
except ImportError:
    from ..agents.hermes_orchestrator import process_with_agents

log = logging.getLogger(__name__)


class IntentRouter:
    def __init__(self):
        log.info("IntentRouter initialized with Hermes Orchestrator engine & Groq Summarizer.")

    def route_intent(self, user_input: str, session: Session) -> str:
        """
        Process raw user transcribed voice input using Hermes, then condense with Groq LLM.
        Fast-paths API battery & quota queries instantly.
        """
        log.info("Routing intent: '%s'", user_input)
        session.add_interaction("user", user_input)

        lowered = user_input.lower()

        # Fast-path: API Battery & Quota check
        if any(kw in lowered for kw in ["battery", "api limit", "api count", "calls left", "quota left", "api status", "limits left"]):
            response = api_battery.get_battery_speech_summary()
            log.info("API Battery fast-path triggered: '%s'", response)
            session.add_interaction("assistant", response)
            return response

        try:
            # Synchronously execute the async Hermes process_with_agents function
            raw_response = asyncio.run(process_with_agents(user_input))

            # Condense raw agent response into a short, crisp, spoken statement using Groq LLM
            response = groq_summarizer.condense_response(raw_response)
        except Exception as exc:
            log.error("Hermes Orchestrator error: %s", exc)
            response = f"I encountered an error processing your request: {exc}"

        # Add response to session history
        session.add_interaction("assistant", response)
        return response
