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
        yield AgentMessage(type=AgentMessageType.DONE, cat_id=cat_id, session_id=session_id)
    return invoke_fn


def text_msg(text, cat_id="orange"):
    return AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=cat_id)


@pytest.fixture
def mock_agents():
    agent1 = {"breed_id": "orange", "name": "阿橘", "service": MagicMock()}
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].invoke = mock_invoke_stream([text_msg("你好", "orange")], "orange")

    agent2 = {"breed_id": "inky", "name": "墨点", "service": MagicMock()}
    agent2["service"].build_system_prompt = MagicMock(return_value="你是墨点")
    agent2["service"].invoke = mock_invoke_stream([text_msg("嗨", "inky")], "inky")

    return [agent1, agent2]


@pytest.mark.asyncio
async def test_parallel_ideate(mock_agents):
    controller = A2AController(mock_agents)
    intent = IntentResult(intent="ideate", explicit=True, prompt_tags=[], clean_message="测试")
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
    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
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
    mock_agents[0]["service"].invoke = mock_invoke_stream([
        text_msg("Found it!", "orange"),
        AgentMessage(type=AgentMessageType.TEXT, content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>', cat_id="orange"),
    ], "orange")
    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
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
    mock_agents[0]["service"].invoke = mock_invoke_stream([
        text_msg("Please help me @inky", "orange"),
        AgentMessage(type=AgentMessageType.TEXT, content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>', cat_id="orange"),
    ], "orange")
    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
    thread = Thread.create("Test")
    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)
    finals = [r for r in responses if r.is_final]
    assert len(finals) == 2
    assert finals[1].cat_id == "inky"
