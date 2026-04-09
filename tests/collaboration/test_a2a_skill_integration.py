"""测试 A2A 协作中的技能集成"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import parse_intent
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
    """创建模拟 agents"""
    agent1 = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock()
    }
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].invoke = mock_invoke_stream([text_msg("测试响应", "orange")], "orange")

    return [agent1]


@pytest.fixture
def temp_skill_env():
    """创建临时技能环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # 创建 manifest.yaml
        manifest_path = Path(tmpdir) / "manifest.yaml"
        manifest_content = {
            "skills": {
                "tdd": {
                    "name": "TDD 工作流",
                    "description": "测试驱动开发",
                    "triggers": ["写代码", "TDD"],
                    "priority": 10,
                    "next": ["quality-gate"]
                }
            }
        }
        with open(manifest_path, 'w') as f:
            yaml.dump(manifest_content, f)

        # 创建技能目录
        skill_dir = Path(tmpdir) / "tdd"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: TDD 工作流
description: >
  测试驱动开发

  Use when: 开始写代码
  Not for: ...
  Output: ...
triggers:
  - "写代码"
  - "TDD"
next: ["quality-gate"]
---

# TDD 工作流

测试驱动开发（TDD）是一种测试优先的开发方法...
""")

        yield {
            "manifest_path": manifest_path,
            "skill_dir": skill_dir,
            "tmpdir": tmpdir
        }


@pytest.mark.asyncio
async def test_skill_triggered_in_a2a(mock_agents, temp_skill_env):
    """测试技能在 A2A 中触发"""
    controller = A2AController(mock_agents)

    # 直接设置 mock skill_router
    mock_router = MagicMock()
    mock_router.route.return_value = [{"skill_id": "tdd", "name": "TDD 工作流", "priority": 10}]
    controller.skill_router = mock_router

    # Mock _load_skill 返回技能数据
    skill_data = {
        "metadata": {
            "name": "TDD 工作流",
            "description": "测试驱动开发",
            "next": ["quality-gate"]
        },
        "content": "请按照 Red-Green-Refactor 循环进行开发。",
        "path": temp_skill_env["skill_dir"]
    }
    controller._load_skill = MagicMock(return_value=skill_data)

    intent = parse_intent("帮我写代码", cat_count=1)
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "帮我写代码", thread):
        responses.append(response)

    # 验证技能路由被调用
    mock_router.route.assert_called_once_with("帮我写代码")
    # 验证有响应
    assert len(responses) > 0


@pytest.mark.asyncio
async def test_no_skill_triggered(mock_agents):
    """测试无技能触发"""
    controller = A2AController(mock_agents)

    # 设置 mock skill_router 不触发技能
    mock_router = MagicMock()
    mock_router.route.return_value = []  # 没有技能匹配
    controller.skill_router = mock_router

    intent = parse_intent("随便说说", cat_count=1)
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "随便说说", thread):
        responses.append(response)

    # 验证路由器被调用
    mock_router.route.assert_called_once_with("随便说说")
    # 验证有响应（正常流程）
    assert len(responses) > 0


@pytest.mark.asyncio
async def test_skill_load_failure_fallback(mock_agents):
    """测试技能加载失败降级"""
    controller = A2AController(mock_agents)

    # 设置 mock skill_router 触发技能
    mock_router = MagicMock()
    mock_router.route.return_value = [{"skill_id": "tdd", "name": "TDD"}]
    controller.skill_router = mock_router

    # Mock _load_skill 返回 None（加载失败）
    controller._load_skill = MagicMock(return_value=None)

    intent = parse_intent("随便说说", cat_count=1)
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "随便说说", thread):
        responses.append(response)

    # 验证降级成功（应该有响应）
    assert len(responses) > 0
