"""
hermes_orchestrator.py - Hermes Orchestration Layer for Project JARVIS.

This module integrates the Google Antigravity (AGY) Python SDK to provide
the intelligence engine for Project JARVIS. It configures a root Supervisor Agent
that orchestrates specialized subagents: Research, Coding, Browser, and System Admin.
"""

import logging
import asyncio
import re
from dotenv import load_dotenv
from google.antigravity import Agent, LocalAgentConfig, types
from google.antigravity.hooks import policy

# Load environment variables from .env if present
load_dotenv()

# Standard SDK Logging Configuration
logging.basicConfig(level=logging.INFO)
logging.getLogger("google.antigravity").setLevel(logging.INFO)
logger = logging.getLogger("hermes_orchestrator")


def build_orchestrator_config() -> LocalAgentConfig:
    """
    Constructs and returns the optimized LocalAgentConfig for the Hermes Supervisor
    and its nested subagent hierarchy using the active lightweight model (gemini-3.5-flash-lite).
    """

    # 1. Research Agent Config - Explicit tool restriction to SEARCH_WEB only
    research_agent = types.SubagentConfig(
        name="research_agent",
        description="Expert at finding and summarizing web information.",
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[types.BuiltinTools.SEARCH_WEB],
        ),
    )

    # 2. Coding Agent Config - Explicit tool restriction to VIEW_FILE only
    coding_agent = types.SubagentConfig(
        name="coding_agent",
        description="Expert at inspecting and reading code files.",
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[types.BuiltinTools.VIEW_FILE],
        ),
    )

    # 3. Browser Agent Config - Explicitly empty tool list
    browser_agent = types.SubagentConfig(
        name="browser_agent",
        description="Expert at navigating web interfaces.",
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[],
        ),
    )

    # 4. System Admin & Health Agent Config - Root PC access, metrics, SSH health, Folder Search & Code Reading
    sys_admin_agent = types.SubagentConfig(
        name="sys_admin_agent",
        description="Expert at checking PC system metrics (CPU, RAM, disk space, uptime), testing SSH connectivity health, and searching, finding, listing, and reading files across all directories starting from root (/) and /home/uchihakamal.",
        capabilities=types.SubagentCapabilities(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enabled_tools=[
                types.BuiltinTools.RUN_COMMAND,
                types.BuiltinTools.VIEW_FILE,
                types.BuiltinTools.LIST_DIR,
                types.BuiltinTools.SEARCH_DIR,
                types.BuiltinTools.FIND_FILE,
            ],
        ),
    )

    # 5. Optimized Supervisor Configuration using model: gemini-3.5-flash-lite
    config = LocalAgentConfig(
        model="gemini-3.5-flash-lite",
        system_instructions="You are the Hermes Supervisor for JARVIS. Delegate prompts to specialized subagents. sys_admin_agent has root-level access (/) to search, inspect, and run diagnostic commands across any folder on the system. Keep all final voice responses under 3 sentences directly.",
        subagents=[research_agent, coding_agent, browser_agent, sys_admin_agent],
        capabilities=types.CapabilitiesConfig(
            enable_subagents=True,
            allowed_subagents=["research_agent", "coding_agent", "browser_agent", "sys_admin_agent"],
            max_subagent_depth=1,  # Strictly limit depth to 1 to prevent recursive subagent spawning
        ),
        budget_config=types.BudgetConfig(
            max_total_tokens=100000, # Raised total token ceiling for multi-step agent turns
            max_model_calls=10,      # Cap model generation calls to prevent runaway loops
        ),
        policies=[policy.allow_all()],  # Allows sys_admin_agent to run shell utility/SSH health checks
    )

    return config


async def process_with_agents(user_prompt: str) -> str:
    """
    Asynchronously processes a transcribed voice prompt using the Hermes Orchestration Layer.

    Args:
        user_prompt (str): The transcribed text input from the JARVIS voice pipeline.

    Returns:
        str: The final text response produced by the Supervisor and delegated subagents,
             ready to be passed back to the TTS module.
    """
    logger.info(f"Hermes Orchestrator received prompt: '{user_prompt}'")
    config = build_orchestrator_config()

    try:
        async with Agent(config) as supervisor:
            response = await supervisor.chat(user_prompt)
            result_text = await response.text()

            # Track Antigravity Gemini call
            try:
                from core.src.api_battery_tracker import api_battery
                api_battery.record_gemini_call()
            except ImportError:
                pass

            # Remove subagent intermediate handoff messages if concatenated
            cleaned_result = re.sub(r"I have gathered [^.\n]+\.\s*", "", result_text, flags=re.IGNORECASE)
            cleaned_result = re.sub(r"sent the report to the parent agent\.?\s*", "", cleaned_result, flags=re.IGNORECASE)

            logger.info("Hermes Orchestrator successfully processed prompt.")
            return cleaned_result.strip()
    except Exception as exc:
        err_str = str(exc)
        logger.error(f"Hermes execution error: {err_str}")
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            return "Gemini API rate limit reached. Please wait a minute before trying again."
        return "I encountered a temporary issue with the subagent service. Please try again."


if __name__ == "__main__":
    # Quick standalone test execution
    async def _test():
        response = await process_with_agents("Check PC system metrics and search Desktop folder files.")
        print("\n[Hermes Output]:", response)

    asyncio.run(_test())
