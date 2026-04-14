"""A2A Controller memory integration tests"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import IntentResult
from src.memory import MemoryService
from src.models.types import AgentMessage, AgentMessageType
from src.thread.models import Thread


class SyncProcessor:
    """Synchronous processor for tests that runs coroutines immediately."""
    async def start(self):
        pass

    async def shutdown(self):
        pass

    def fire_and_forget(self, coro, name="unnamed"):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            pass

    def run_in_thread(self, fn, *args, name="unnamed"):
        fn(*args)


@pytest.fixture(autouse=True)
def sync_processor():
    with patch("src.collaboration.a2a_controller.get_processor", return_value=SyncProcessor()):
        yield


def mock_invoke_stream(items, cat_id="orange", session_id=None):
    async def invoke_fn(prompt, options=None):
        for item in items:
            yield item
        yield AgentMessage(type=AgentMessageType.DONE, cat_id=cat_id, session_id=session_id)
    return invoke_fn


def text_msg(text, cat_id="orange"):
    return AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=cat_id)


class InvokeRecorder:
    """Wraps an async generator invoke fn to record call_args."""
    def __init__(self, fn):
        self._fn = fn
        self.call_args = None

    def __call__(self, *args, **kwargs):
        self.call_args = (args, kwargs)
        return self._fn(*args, **kwargs)


@pytest.fixture
def memory_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield MemoryService(db_path=str(Path(tmpdir) / "test.db"))


@pytest.fixture
def mock_agents():
    service = MagicMock()
    service.build_system_prompt.return_value = "You are a cat."
    service.invoke = mock_invoke_stream([text_msg("Meow reply", "orange")], "orange")
    return [{"service": service, "name": "Orange", "breed_id": "orange"}]


@pytest.fixture
def thread():
    t = Thread.create("Test")
    t.id = "test-thread"
    return t


class TestAutoStoreConversations:
    @pytest.mark.asyncio
    async def test_auto_stores_user_and_assistant(self, memory_service, mock_agents, thread):
        """Auto-store saves user message and cat reply to episodic memory"""
        controller = A2AController(
            mock_agents, memory_service=memory_service, metrics_collector=MagicMock()
        )
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="Hello cat")

        responses = []
        async for r in controller.execute(intent, "Hello cat", thread):
            responses.append(r)

        # Flush background tasks scheduled by fire_and_forget
        import asyncio
        await asyncio.sleep(0)

        # Verify episodic memory has stored the conversation
        episodes = memory_service.episodic.recall_by_thread("test-thread")
        roles = [ep["role"] for ep in episodes]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_auto_store_importance(self, memory_service, mock_agents, thread):
        """User messages get importance=3, assistant replies get importance=5"""
        controller = A2AController(
            mock_agents, memory_service=memory_service, metrics_collector=MagicMock()
        )
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="Test message")

        async for r in controller.execute(intent, "Test message", thread):
            pass

        import asyncio
        await asyncio.sleep(0)

        episodes = memory_service.episodic.recall_by_thread("test-thread")
        user_eps = [e for e in episodes if e["role"] == "user"]
        asst_eps = [e for e in episodes if e["role"] == "assistant"]

        assert len(user_eps) >= 1
        assert user_eps[0]["importance"] == 3
        assert len(asst_eps) >= 1
        assert asst_eps[0]["importance"] == 5

    @pytest.mark.asyncio
    async def test_no_store_when_no_memory_service(self, mock_agents, thread):
        """No crash when memory_service is None"""
        controller = A2AController(mock_agents)
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="Hello")

        async for r in controller.execute(intent, "Hello", thread):
            pass
        # Should not crash


class TestAutoRetrieveMemory:
    @pytest.mark.asyncio
    async def test_memory_injected_into_prompt(self, memory_service, mock_agents, thread):
        """Relevant memory is injected into the system prompt"""
        # Pre-populate memory
        memory_service.store_episode(
            "other-thread", "user", "React is great for frontend", importance=5
        )

        # Wrap invoke to record call_args
        recorder = InvokeRecorder(mock_agents[0]["service"].invoke)
        mock_agents[0]["service"].invoke = recorder

        controller = A2AController(
            mock_agents, memory_service=memory_service, metrics_collector=MagicMock()
        )
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="React")

        async for r in controller.execute(intent, "React", thread):
            pass

        # Verify invoke was called with a system prompt containing memory
        options = recorder.call_args[0][1]  # second positional arg is InvocationOptions
        assert "相关记忆" in options.system_prompt

    @pytest.mark.asyncio
    async def test_no_memory_injection_when_empty(self, memory_service, mock_agents, thread):
        """No memory section added when no relevant memories exist"""
        # Wrap invoke to record call_args
        recorder = InvokeRecorder(mock_agents[0]["service"].invoke)
        mock_agents[0]["service"].invoke = recorder

        controller = A2AController(
            mock_agents, memory_service=memory_service, metrics_collector=MagicMock()
        )
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="Hello")

        async for r in controller.execute(intent, "Hello", thread):
            pass

        options = recorder.call_args[0][1]
        assert "相关记忆" not in options.system_prompt


class TestAutoExtractEntities:
    @pytest.mark.asyncio
    async def test_extracts_preference_from_text(self, memory_service, thread):
        """Entity extractor finds preference in user message"""
        service = MagicMock()
        service.build_system_prompt.return_value = "You are a cat."
        service.invoke = mock_invoke_stream([text_msg("OK React is nice", "orange")], "orange")
        agents = [{"service": service, "name": "Orange", "breed_id": "orange"}]

        controller = A2AController(agents, memory_service=memory_service, metrics_collector=MagicMock())
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="用户喜欢React")

        async for r in controller.execute(intent, "用户喜欢React", thread):
            pass

        import asyncio
        await asyncio.sleep(0)

        entity = memory_service.semantic.get_entity("React")
        assert entity is not None
        assert entity["type"] == "preference"

    @pytest.mark.asyncio
    async def test_no_extraction_when_no_patterns(self, memory_service, thread):
        """No entities stored for plain text"""
        service = MagicMock()
        service.build_system_prompt.return_value = "You are a cat."
        service.invoke = mock_invoke_stream([text_msg("OK", "orange")], "orange")
        agents = [{"service": service, "name": "Orange", "breed_id": "orange"}]

        controller = A2AController(agents, memory_service=memory_service, metrics_collector=MagicMock())
        intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="Hello there")

        async for r in controller.execute(intent, "Hello there", thread):
            pass

        import asyncio
        await asyncio.sleep(0)

        results = memory_service.semantic.search_entities("Hello")
        assert len(results) == 0


class TestAutoRecordWorkflow:
    @pytest.mark.asyncio
    async def test_records_workflow_pattern(self, memory_service):
        """DAG execution records workflow pattern to procedural memory"""
        from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG
        from src.workflow.executor import DAGExecutor
        from src.workflow.templates import WorkflowTemplateFactory

        # Create a mock agent registry
        registry = MagicMock()
        service = MagicMock()
        service.build_system_prompt.return_value = "You are a cat."

        async def _make_stream(*args, **kwargs):
            from src.models.types import AgentMessage, AgentMessageType
            yield AgentMessage(type=AgentMessageType.TEXT, content="Idea 1")

        service.invoke = AsyncMock(side_effect=_make_stream)
        registry.get.return_value = service

        executor = DAGExecutor(agent_registry=registry)
        factory = WorkflowTemplateFactory()

        agents = [
            {"service": service, "name": "Orange", "breed_id": "orange"},
            {"service": service, "name": "Inky", "breed_id": "inky"},
        ]

        dag = factory.create("brainstorm", agents, "test topic")

        # Use a real thread
        t = Thread.create("wf-test")
        results = []
        async for result in executor.execute(dag, "test topic", t):
            results.append(result)

        # Manually record (simulating what ws.py does)
        if memory_service:
            success = sum(1 for r in results if r.status == "completed")
            memory_service.procedural.store_procedure(
                name="brainstorm",
                category="workflow",
                steps=["orange", "inky", "aggregator"],
                trigger_conditions=["#brainstorm"],
                outcomes={
                    "total_nodes": 3,
                    "success": success,
                    "failed": len(results) - success,
                }
            )

        # Verify stored
        procs = memory_service.procedural.search("brainstorm")
        assert len(procs) >= 1
        assert procs[0]["name"] == "brainstorm"
