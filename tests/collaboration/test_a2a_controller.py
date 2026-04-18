import pytest
from unittest.mock import MagicMock
from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread
from src.models.types import AgentMessage, AgentMessageType


def mock_invoke_stream(items, cat_id="orange", session_id=None):
    async def invoke_fn(prompt, options=None):
        for item in items:
            yield item
        yield AgentMessage(
            type=AgentMessageType.DONE, cat_id=cat_id, session_id=session_id
        )

    return invoke_fn


def text_msg(text, cat_id="orange"):
    return AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=cat_id)


@pytest.fixture
def mock_agents():
    agent1 = {"breed_id": "orange", "name": "阿橘", "service": MagicMock()}
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].invoke = mock_invoke_stream(
        [text_msg("你好", "orange")], "orange"
    )

    agent2 = {"breed_id": "inky", "name": "墨点", "service": MagicMock()}
    agent2["service"].build_system_prompt = MagicMock(return_value="你是墨点")
    agent2["service"].invoke = mock_invoke_stream([text_msg("嗨", "inky")], "inky")

    return [agent1, agent2]


@pytest.mark.asyncio
async def test_parallel_ideate(mock_agents):
    controller = A2AController(mock_agents)
    intent = IntentResult(
        intent="ideate", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")
    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)
    # Streaming yields partial chunks + final markers per cat
    finals = [r for r in responses if r.is_final]
    assert len(finals) == 2
    assert any(r.cat_id == "orange" for r in finals)
    assert any(r.cat_id == "inky" for r in finals)


@pytest.mark.asyncio
async def test_serial_execute(mock_agents):
    controller = A2AController(mock_agents)
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")
    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)
    finals = [r for r in responses if r.is_final]
    assert len(finals) == 2
    assert finals[0].cat_id == "orange"
    assert finals[1].cat_id == "inky"


@pytest.mark.asyncio
async def test_mcp_callback_integration(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream(
        [
            text_msg("Found it!", "orange"),
            AgentMessage(
                type=AgentMessageType.TEXT,
                content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>',
                cat_id="orange",
            ),
        ],
        "orange",
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")
    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)
    final_orange = [r for r in responses if r.is_final and r.cat_id == "orange"][0]
    assert final_orange.targetCats == ["inky"]
    assert "targetCats" not in final_orange.content


@pytest.mark.asyncio
async def test_target_cats_routing(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream(
        [
            text_msg("Please help me @inky", "orange"),
            AgentMessage(
                type=AgentMessageType.TEXT,
                content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>',
                cat_id="orange",
            ),
        ],
        "orange",
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")
    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)
    finals = [r for r in responses if r.is_final]
    assert len(finals) == 2
    assert finals[1].cat_id == "inky"


@pytest.mark.asyncio
async def test_status_message_broadcasts_cat_status(mock_agents):
    """STATUS messages from provider should trigger cat_status broadcast."""
    broadcasts = []

    async def capture_broadcast(data):
        broadcasts.append(data)

    controller = A2AController(mock_agents, broadcast_callback=capture_broadcast)
    mock_agents[0]["service"].invoke = mock_invoke_stream(
        [
            AgentMessage(
                type=AgentMessageType.STATUS, content="Starting...", cat_id="orange"
            ),
            text_msg("Hello", "orange"),
        ],
        "orange",
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    status_broadcasts = [b for b in broadcasts if b.get("type") == "cat_status"]
    provider_status = [
        b for b in status_broadcasts if b.get("content") == "Starting..."
    ]
    assert len(provider_status) == 1
    assert provider_status[0]["cat_id"] == "orange"

    finals = [r for r in responses if r.is_final]
    assert len(finals) == 2
    assert finals[0].cat_id == "orange"


@pytest.mark.asyncio
async def test_thinking_message_does_not_crash_and_reaches_final(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream(
        [
            AgentMessage(
                type=AgentMessageType.THINKING, content="分析中", cat_id="orange"
            ),
            text_msg("结论", "orange"),
        ],
        "orange",
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    thinking = [r for r in responses if r.thinking == "分析中" and not r.is_final]
    finals = [r for r in responses if r.is_final]

    assert len(thinking) == 1
    assert thinking[0].content == ""
    assert len(finals) == 2
    assert finals[0].cat_id == "orange"


@pytest.mark.asyncio
async def test_error_message_propagates_as_runtime_error(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream(
        [
            AgentMessage(
                type=AgentMessageType.ERROR, content="provider failure", cat_id="orange"
            ),
        ],
        "orange",
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="测试"
    )
    thread = Thread.create("Test")

    with pytest.raises(RuntimeError, match="provider failure"):
        async for _ in controller.execute(intent, "测试", thread):
            pass


@pytest.mark.asyncio
async def test_execute_accepts_dict_config_capabilities_for_implement_tasks():
    invoke_calls = 0

    async def invoke(prompt, options=None):
        nonlocal invoke_calls
        invoke_calls += 1
        async for item in mock_invoke_stream([text_msg("实现好了", "orange")], "orange")(
            prompt, options
        ):
            yield item

    service = MagicMock()
    service.config = {
        "capabilities": ["code_gen", "chat"],
        "cli_command": "claude",
        "default_model": "claude-opus-4-6",
    }
    service.build_system_prompt = MagicMock(return_value="你是阿橘")
    service.invoke = invoke

    controller = A2AController(
        [{"breed_id": "orange", "name": "阿橘", "service": service}]
    )
    intent = IntentResult(
        intent="execute", explicit=True, prompt_tags=[], clean_message="Write the fix"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "Write the fix", thread):
        responses.append(response)

    finals = [r for r in responses if r.is_final]
    assert len(finals) == 1
    assert finals[0].content == "实现好了"
    assert "无法处理该任务" not in finals[0].content
    assert invoke_calls == 1
