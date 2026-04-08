import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread


class AsyncIteratorMock:
    """模拟异步迭代器"""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


def mock_async_iterator(items):
    """创建一个返回异步迭代器的 mock 函数"""
    async def async_iter(*args, **kwargs):
        for item in items:
            yield item
    return async_iter


@pytest.fixture
def mock_agents():
    """创建模拟 agents"""
    agent1 = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock()
    }
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].chat_stream = mock_async_iterator(["你好"])

    agent2 = {
        "breed_id": "inky",
        "name": "墨点",
        "service": MagicMock()
    }
    agent2["service"].build_system_prompt = MagicMock(return_value="你是墨点")
    agent2["service"].chat_stream = mock_async_iterator(["嗨"])

    return [agent1, agent2]


@pytest.mark.asyncio
async def test_parallel_ideate(mock_agents):
    """测试并行 ideate 模式"""
    controller = A2AController(mock_agents)

    intent = IntentResult(
        intent="ideate",
        explicit=True,
        prompt_tags=[],
        clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert len(responses) == 2
    assert any(r.cat_id == "orange" for r in responses)
    assert any(r.cat_id == "inky" for r in responses)


@pytest.mark.asyncio
async def test_serial_execute(mock_agents):
    """测试串行 execute 模式"""
    controller = A2AController(mock_agents)

    intent = IntentResult(
        intent="execute",
        explicit=True,
        prompt_tags=[],
        clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert len(responses) == 2
    # 串行模式下按顺序
    assert responses[0].cat_id == "orange"
    assert responses[1].cat_id == "inky"


@pytest.mark.asyncio
async def test_mcp_callback_integration(mock_agents):
    """测试 MCP 回调集成"""
    controller = A2AController(mock_agents)

    # Mock 服务返回带回调的内容
    mock_agents[0]["service"].chat_stream = mock_async_iterator([
        'Found it!',
        '<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
    ])

    intent = IntentResult(
        intent="execute",
        explicit=True,
        prompt_tags=[],
        clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    # 验证 targetCats 被解析
    assert responses[0].targetCats == ["inky"]
    assert "targetCats" not in responses[0].content


@pytest.mark.asyncio
async def test_target_cats_routing(mock_agents):
    """测试 targetCats 结构化路由"""
    controller = A2AController(mock_agents)

    # 第一只猫返回 targetCats 指向第二只猫
    mock_agents[0]["service"].chat_stream = mock_async_iterator([
        'Please help me @inky',
        '<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
    ])

    intent = IntentResult(
        intent="execute",
        explicit=True,
        prompt_tags=[],
        clean_message="测试"
    )
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    # 验证两只猫都响应了
    assert len(responses) == 2
    # 第二个响应应该是 inky
    assert responses[1].cat_id == "inky"

