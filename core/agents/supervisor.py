"""
JARVIS Core — Supervisor Agent
The primary orchestration intelligence that plans and delegates tasks.
"""

import os
import logging
from typing import Any
try:
    from groq import Groq
except ImportError:
    Groq = None

log = logging.getLogger(__name__)

# Basic system prompt for the Supervisor
SUPERVISOR_SYSTEM_PROMPT = """You are the JARVIS Supervisor Agent. 
Your job is to understand the user's objective, break it down into a logical plan, 
and eventually delegate tasks to specialized agents (e.g., Research Agent, Coding Agent).

For now, since the multi-agent system (Hermes) is not fully built, you should simply:
1. Acknowledge the user's request.
2. Output a structured, high-level plan of how you *would* accomplish this using specialized agents.
3. Keep your response concise and professional.
"""

class SupervisorAgent:
    def __init__(self):
        # We expect GROQ_API_KEY to be set in the environment
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key and Groq else None
        
        if not self.client:
            log.warning("GROQ_API_KEY not found or groq library not installed. Supervisor will run in mock mode.")
            
    def execute(self, user_intent: str, session: Any) -> str:
        """
        Takes the user intent and returns a plan/response.
        """
        log.info("Supervisor Agent analyzing intent: '%s'", user_intent)
        
        if not self.client:
            return f"[MOCK MODE] I understood your intent: '{user_intent}'. I will plan the execution shortly once my AI is connected."
            
        try:
            response = self.client.chat.completions.create(
                model='openai/gpt-oss-20b',
                messages=[
                    {"role": "system", "content": SUPERVISOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_intent}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            log.error("Error generating supervisor response: %s", e)
            return f"I encountered an error while trying to process your request: {str(e)}"

###