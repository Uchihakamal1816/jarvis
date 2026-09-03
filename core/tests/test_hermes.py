import unittest
import asyncio
from src.hermes.models import AgentIdentity, TaskRequest, TaskResult
from src.hermes.registry import AgentRegistry
from src.hermes.broker import HermesBroker

class TestHermes(unittest.IsolatedAsyncioTestCase):
    
    async def test_registry(self):
        registry = AgentRegistry()
        agent = AgentIdentity(id="research_1", name="ResearchAgent", description="Finds things", capabilities=["web_search"])
        registry.register(agent)
        
        found = registry.get_agent("research_1")
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "ResearchAgent")
        
        capable = registry.find_agents_by_capability("web_search")
        self.assertEqual(len(capable), 1)
        
        registry.unregister("research_1")
        self.assertIsNone(registry.get_agent("research_1"))

    async def test_broker_pub_sub(self):
        broker = HermesBroker()
        
        async def agent_listen():
            messages = []
            async for msg in broker.subscribe("agent_a"):
                messages.append(msg)
                if len(messages) == 2:
                    break
            return messages
            
        task = asyncio.create_task(agent_listen())
        
        req = TaskRequest(
            correlation_id="123",
            sender_id="supervisor",
            receiver_id="agent_a",
            task_description="Do work"
        )
        
        res = TaskResult(
            correlation_id="123",
            sender_id="supervisor",
            receiver_id="agent_a",
            success=True,
            output="Done"
        )
        
        await broker.publish(req)
        await broker.publish(res)
        
        received = await task
        
        self.assertEqual(len(received), 2)
        self.assertEqual(received[0].correlation_id, "123")
        self.assertEqual(received[1].output, "Done")

if __name__ == "__main__":
    unittest.main()
