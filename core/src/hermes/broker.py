import asyncio
from typing import Dict, AsyncGenerator
from .models import Message

class HermesBroker:
    """
    Local asyncio-based message broker for routing messages between agents.
    """
    
    def __init__(self):
        # Maps agent_id to an asyncio.Queue
        self._queues: Dict[str, asyncio.Queue] = {}

    def _get_or_create_queue(self, agent_id: str) -> asyncio.Queue:
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
        return self._queues[agent_id]

    async def publish(self, message: Message) -> None:
        """
        Publish a message to the target receiver's queue.
        """
        queue = self._get_or_create_queue(message.receiver_id)
        await queue.put(message)

    async def subscribe(self, agent_id: str) -> AsyncGenerator[Message, None]:
        """
        Subscribe to messages sent to this agent_id.
        Yields messages as they arrive.
        """
        queue = self._get_or_create_queue(agent_id)
        while True:
            message = await queue.get()
            yield message
            queue.task_done()
