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
        log.info("IntentRouter initialized with Groq LPU Brain Router & Hermes Orchestrator.")

    def decide_intent(self, user_input: str) -> tuple[str, str | None]:
        """
        Uses Groq LLM as the primary brain router to decide if the query can be dealt with
        directly by Groq ("DIRECT") or requires Hermes Antigravity subagents ("HERMES").
        """
        return groq_summarizer.route_brain_intent(user_input)

    def execute_hermes(self, user_input: str, session: Session) -> str:
        """
        Executes Hermes Antigravity subagents for complex tasks requiring system tools / search,
        then condenses output using Groq.
        """
        log.info("Executing Hermes Orchestrator for prompt: '%s'", user_input)
        session.add_interaction("user", user_input)
        try:
            raw_response = asyncio.run(process_with_agents(user_input))
            response = groq_summarizer.condense_response(raw_response)
        except Exception as exc:
            log.error("Hermes Orchestrator error: %s", exc)
            response = f"I encountered an error processing your request: {exc}"

        session.add_interaction("assistant", response)
        return response

    def route_intent(self, user_input: str, session: Session) -> str:
        """
        Process raw user transcribed voice input. Uses Groq Brain decision first.
        """
        log.info("Routing intent: '%s'", user_input)

        lowered = user_input.lower()
        if any(kw in lowered for kw in ["battery", "api limit", "api count", "calls left", "quota left", "api status", "limits left"]):
            response = api_battery.get_battery_speech_summary()
            log.info("API Battery fast-path triggered: '%s'", response)
            session.add_interaction("assistant", response)
            return response

        action, direct_res = self.decide_intent(user_input)
        if action == "DIRECT" and direct_res:
            session.add_interaction("user", user_input)
            session.add_interaction("assistant", direct_res)
            return direct_res

        return self.execute_hermes(user_input, session)

