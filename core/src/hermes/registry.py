from typing import Dict, List, Optional
from .models import AgentIdentity

class AgentRegistry:
    """Tracks active agents and their capabilities."""
    
    def __init__(self):
        self._agents: Dict[str, AgentIdentity] = {}

    def register(self, identity: AgentIdentity) -> None:
        """Register an agent with Hermes."""
        self._agents[identity.id] = identity

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from Hermes."""
        if agent_id in self._agents:
            del self._agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[AgentIdentity]:
        """Lookup an agent by ID."""
        return self._agents.get(agent_id)

    def find_agents_by_capability(self, capability: str) -> List[AgentIdentity]:
        """Find all agents that possess a specific capability."""
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]

    def list_agents(self) -> List[AgentIdentity]:
        """Return all registered agents."""
        return list(self._agents.values())
