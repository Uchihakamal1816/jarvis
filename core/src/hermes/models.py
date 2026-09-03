from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
import time

class AgentIdentity(BaseModel):
    """Identifies an agent in the Hermes network."""
    id: str
    name: str
    description: str
    capabilities: List[str] = Field(default_factory=list)

class Message(BaseModel):
    """Base class for all Hermes communication."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str
    sender_id: str
    receiver_id: str
    timestamp: float = Field(default_factory=time.time)

class TaskRequest(Message):
    """A request for an agent to perform a task."""
    task_description: str
    context: Dict[str, Any] = Field(default_factory=dict)

class TaskResult(Message):
    """The result of a completed or failed task."""
    success: bool
    output: Any
    error_message: Optional[str] = None
