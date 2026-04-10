# Phase 3.3: Intent 解析与 A2A 协作 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Intent 解析（#ideate/#execute/#critique）和 A2A 协作模式（并行/串行多猫协作）。

**Architecture:** 创建 IntentParser 解析用户输入中的标签，根据 intent 类型选择协作模式（ideate=并行独立思考，execute=串行接力执行），通过 A2AController 管理多猫协作流程。

**Tech Stack:** Python 3.9+, asyncio, pytest

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `src/collaboration/intent_parser.py` | Intent 解析器 |
| `src/collaboration/a2a_controller.py` | A2A 协作控制器 |
| `src/collaboration/__init__.py` | 导出 |
| `tests/collaboration/test_intent_parser.py` | Intent 测试 |
| `tests/collaboration/test_a2a_controller.py` | A2A 测试 |
| `src/cli/main.py` | 集成到 chat |

---

## Task 1: IntentParser 实现

**Files:**
- Create: `src/collaboration/intent_parser.py`
- Create: `src/collaboration/__init__.py`
- Test: `tests/collaboration/test_intent_parser.py`

**Context:** 解析用户输入中的 #ideate, #execute, #critique 标签。

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/collaboration tests/collaboration
```

- [ ] **Step 2: 实现 IntentParser**

Create `src/collaboration/intent_parser.py`:

```python
from dataclasses import dataclass
from typing import List, Literal, Optional
import re

IntentType = Literal["ideate", "execute"]
PromptTagType = Literal["critique"]

VALID_INTENTS = {"ideate", "execute"}
VALID_PROMPT_TAGS = {"critique"}
TAG_PATTERN = re.compile(r"#(\w+)", re.IGNORECASE)


@dataclass
class IntentResult:
    """Intent 解析结果"""
    intent: IntentType
    explicit: bool  # 是否显式指定
    prompt_tags: List[PromptTagType]
    clean_message: str  # 移除标签后的消息


class IntentParser:
    """解析用户输入的 intent"""

    def parse(self, message: str, cat_count: int) -> IntentResult:
        """
        解析消息中的 intent

        Args:
            message: 用户输入
            cat_count: 涉及的猫数量

        Returns:
            IntentResult
        """
        tags = self._extract_tags(message)

        # 确定 intent
        explicit_intent = self._find_explicit_intent(tags)
        if explicit_intent:
            intent = explicit_intent
            explicit = True
        else:
            # 自动推断: >=2猫 -> ideate, 1猫 -> execute
            intent = "ideate" if cat_count >= 2 else "execute"
            explicit = False

        # 提取 prompt tags
        prompt_tags = self._find_prompt_tags(tags)

        # 清理消息
        clean_message = self._strip_tags(message)

        return IntentResult(
            intent=intent,
            explicit=explicit,
            prompt_tags=prompt_tags,
            clean_message=clean_message
        )

    def _extract_tags(self, message: str) -> List[str]:
        """提取所有 #标签"""
        return [match.group(1).lower() for match in TAG_PATTERN.finditer(message)]

    def _find_explicit_intent(self, tags: List[str]) -> Optional[IntentType]:
        """查找显式 intent"""
        for tag in tags:
            if tag in VALID_INTENTS:
                return tag  # type: ignore
        return None

    def _find_prompt_tags(self, tags: List[str]) -> List[PromptTagType]:
        """查找 prompt tags"""
        result = []
        for tag in tags:
            if tag in VALID_PROMPT_TAGS:
                result.append(tag)  # type: ignore
        return result

    def _strip_tags(self, message: str) -> str:
        """移除所有标签"""
        return TAG_PATTERN.sub("", message).strip()


def parse_intent(message: str, cat_count: int) -> IntentResult:
    """便捷函数"""
    return IntentParser().parse(message, cat_count)
```

- [ ] **Step 3: 创建 __init__.py**

Create `src/collaboration/__init__.py`:

```python
from src.collaboration.intent_parser import (
    IntentParser,
    IntentResult,
    IntentType,
    parse_intent,
)

__all__ = ["IntentParser", "IntentResult", "IntentType", "parse_intent"]
```

- [ ] **Step 4: 编写测试**

Create `tests/collaboration/test_intent_parser.py`:

```python
import pytest
from src.collaboration.intent_parser import (
    IntentParser,
    parse_intent,
    VALID_INTENTS,
    VALID_PROMPT_TAGS,
)


def test_explicit_ideate():
    """测试显式 #ideate"""
    result = parse_intent("帮我设计架构 #ideate", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is True


def test_explicit_execute():
    """测试显式 #execute"""
    result = parse_intent("实现这个功能 #execute", cat_count=2)
    assert result.intent == "execute"
    assert result.explicit is True


def test_auto_infer_ideate():
    """测试自动推断 ideate (>=2 猫)"""
    result = parse_intent("帮我看看这个", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is False


def test_auto_infer_execute():
    """测试自动推断 execute (1 猫)"""
    result = parse_intent("帮我写代码", cat_count=1)
    assert result.intent == "execute"
    assert result.explicit is False


def test_critique_tag():
    """测试 #critique 标签"""
    result = parse_intent("检查这段代码 #critique", cat_count=1)
    assert "critique" in result.prompt_tags


def test_clean_message():
    """测试清理后的消息"""
    result = parse_intent("帮我设计 #ideate #critique", cat_count=2)
    assert "#ideate" not in result.clean_message
    assert "#critique" not in result.clean_message
    assert "帮我设计" in result.clean_message


def test_multiple_tags():
    """测试多个标签"""
    result = parse_intent("帮我看看 #ideate #critique", cat_count=2)
    assert result.intent == "ideate"
    assert "critique" in result.prompt_tags


def test_case_insensitive():
    """测试大小写不敏感"""
    result = parse_intent("帮我 #IDEATE #CRITIQUE", cat_count=2)
    assert result.intent == "ideate"
    assert "critique" in result.prompt_tags
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/collaboration/test_intent_parser.py -v
```

Expected: 8 tests passing

- [ ] **Step 6: 提交**

```bash
git add src/collaboration/ tests/collaboration/
git commit -m "feat: add IntentParser for #ideate/#execute/#critique

- Parse intent tags from user messages
- Auto-infer intent based on cat count
- Support #critique prompt tag
- Clean message by stripping tags

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: A2AController 实现

**Files:**
- Create: `src/collaboration/a2a_controller.py`
- Test: `tests/collaboration/test_a2a_controller.py`

**Context:** 管理多猫协作流程（并行 ideate / 串行 execute）。

- [ ] **Step 1: 实现 A2AController**

Create `src/collaboration/a2a_controller.py`:

```python
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator
import asyncio

from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread, Message


@dataclass
class CatResponse:
    """猫的响应"""
    cat_id: str
    cat_name: str
    content: str


class A2AController:
    """A2A 协作控制器"""

    def __init__(self, agents: List[Dict[str, Any]]):
        """
        Args:
            agents: 来自 router.route_message() 的结果列表
        """
        self.agents = agents

    async def execute(
        self,
        intent: IntentResult,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """
        执行协作

        Args:
            intent: 解析后的 intent
            message: 用户消息（已清理标签）
            thread: 当前 thread

        Yields:
            CatResponse
        """
        if intent.intent == "ideate":
            async for response in self._parallel_ideate(message, thread):
                yield response
        else:  # execute
            async for response in self._serial_execute(message, thread):
                yield response

    async def _parallel_ideate(
        self,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """并行 ideate 模式 - 所有猫同时独立思考"""
        # 创建所有任务
        tasks = []
        for agent_info in self.agents:
            service = agent_info["service"]
            name = agent_info["name"]
            breed_id = agent_info["breed_id"]

            task = self._call_cat(service, name, breed_id, message, thread)
            tasks.append(task)

        # 并行执行，按完成顺序返回
        for coro in asyncio.as_completed(tasks):
            response = await coro
            yield response

    async def _serial_execute(
        self,
        message: str,
        thread: Thread
    ) -> AsyncIterator[CatResponse]:
        """串行 execute 模式 - 猫按顺序接力"""
        for i, agent_info in enumerate(self.agents):
            service = agent_info["service"]
            name = agent_info["name"]
            breed_id = agent_info["breed_id"]

            # 构建提示，包含之前猫的回复
            context_msg = self._build_context(message, thread, i)

            response = await self._call_cat(
                service, name, breed_id, context_msg, thread
            )
            yield response

            # 添加到 thread 供下一只猫参考
            thread.add_message("assistant", response.content, cat_id=breed_id)

    async def _call_cat(
        self,
        service,
        name: str,
        breed_id: str,
        message: str,
        thread: Thread
    ) -> CatResponse:
        """调用单只猫"""
        # 构建系统提示
        system_prompt = service.build_system_prompt()

        # 添加协作上下文
        if len(self.agents) > 1:
            system_prompt += self._build_collaboration_context(breed_id)

        # 调用服务
        chunks = []
        async for chunk in service.chat_stream(message, system_prompt):
            chunks.append(chunk)

        content = "".join(chunks)

        return CatResponse(
            cat_id=breed_id,
            cat_name=name,
            content=content
        )

    def _build_collaboration_context(self, current_cat_id: str) -> str:
        """构建协作上下文提示"""
        other_cats = [a["name"] for a in self.agents if a["breed_id"] != current_cat_id]

        if not other_cats:
            return ""

        return f"\n\n## 协作说明\n本次有多只猫参与：{', '.join(other_cats)}。请专注于你的角色，给出独立见解。"

    def _build_context(self, message: str, thread: Thread, current_index: int) -> str:
        """为串行模式构建上下文"""
        if current_index == 0:
            return message

        # 添加之前猫的回复作为上下文
        context_parts = [message, "\n\n## 前面的回复"]

        for msg in thread.messages[-current_index:]:
            if msg.role == "assistant" and msg.cat_id:
                context_parts.append(f"\n{msg.cat_id}: {msg.content[:200]}...")

        context_parts.append("\n\n请继续完成或补充：")
        return "".join(context_parts)
```

- [ ] **Step 2: 编写测试**

Create `tests/collaboration/test_a2a_controller.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread


@pytest.fixture
def mock_agents():
    """创建模拟 agents"""
    agent1 = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock()
    }
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].chat_stream = AsyncMock(return_value=AsyncIteratorMock(["你好"]))

    agent2 = {
        "breed_id": "inky",
        "name": "墨点",
        "service": MagicMock()
    }
    agent2["service"].build_system_prompt = MagicMock(return_value="你是墨点")
    agent2["service"].chat_stream = AsyncMock(return_value=AsyncIteratorMock(["嗨"]))

    return [agent1, agent2]


class AsyncIteratorMock:
    """模拟异步迭代器"""
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return iter(self.items).__aiter__()


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
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/collaboration/test_a2a_controller.py -v
```

- [ ] **Step 4: 提交**

```bash
git add src/collaboration/a2a_controller.py tests/collaboration/test_a2a_controller.py
git commit -m "feat: add A2AController for multi-cat collaboration

- Parallel ideate mode (independent thinking)
- Serial execute mode (relay collaboration)
- Build collaboration context for each cat

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 集成到 Chat

**Files:**
- Modify: `src/cli/main.py`

**Context:** 在 chat 命令中使用 IntentParser 和 A2AController。

- [ ] **Step 1: 修改 chat 命令**

Modify `src/cli/main.py`:

```python
import click
import asyncio
from src.router.agent_router import AgentRouter
from src.cli.thread_commands import thread_cli, get_cat_mention
from src.collaboration.intent_parser import parse_intent
from src.collaboration.a2a_controller import A2AController


@click.group()
@click.version_option(version='0.3.2', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


cli.add_command(thread_cli)


@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫')
@click.option('--thread', 'thread_id', help='指定 thread ID')
@click.option('--resume', is_flag=True, help='恢复上次会话')
def chat(cat: str, thread_id: str, resume: bool):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()
    router = AgentRouter()

    # ... 原有 thread 处理逻辑 ...

    # 显示协作模式提示
    click.echo("💡 提示: 使用 #ideate 多猫并行讨论, #execute 串行接力执行")
    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 如果没有 @mention，添加默认
            if '@' not in message:
                message = f"@{cat_id} {message}"

            # 路由消息获取 agents
            agents = router.route_message(message)

            # 解析 intent
            intent_result = parse_intent(message, len(agents))

            # 显示模式信息
            if intent_result.explicit:
                mode_str = "并行讨论" if intent_result.intent == "ideate" else "串行接力"
                click.echo(f"🔄 模式: {mode_str} ({intent_result.intent})")

            if intent_result.prompt_tags:
                click.echo(f"🏷️  标签: {', '.join(intent_result.prompt_tags)}")

            # 添加用户消息到 thread（使用清理后的消息）
            thread.add_message("user", intent_result.clean_message)

            # 使用 A2AController 执行协作
            try:
                controller = A2AController(agents)

                async for response in controller.execute(
                    intent_result,
                    intent_result.clean_message,
                    thread
                ):
                    click.echo(f"\n{response.cat_name}: {response.content}\n")

                    # 添加回复到 thread
                    thread.add_message(
                        "assistant",
                        response.content,
                        cat_id=response.cat_id
                    )

                # 保存 thread
                asyncio.run(manager.update_thread(thread))

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～对话已保存\n")
        asyncio.run(manager.update_thread(thread))


def build_thread_aware_prompt(service, thread, breed_id):
    """构建包含 thread 历史的系统提示（保留原有实现）"""
    # ... 原有实现 ...
    pass


if __name__ == '__main__':
    cli()
```

- [ ] **Step 2: 测试**

```bash
# 测试 ideate 模式
python3 -m src.cli.main chat
# 输入: @dev @review 这个架构怎么样？#ideate

# 测试 execute 模式
python3 -m src.cli.main chat
# 输入: @dev @review 实现这个功能 #execute

# 测试 critique 标签
python3 -m src.cli.main chat
# 输入: @review 检查这段代码 #critique
```

- [ ] **Step 3: 提交**

```bash
git add src/cli/main.py
git commit -m "feat: integrate IntentParser and A2AController into chat

- Auto-detect intent from user messages
- Support #ideate/#execute/#critique
- Parallel ideate with multiple cats
- Serial execute with relay collaboration

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 集成测试和文档

**Files:**
- Create: `tests/integration/test_intent_a2a.py`
- Modify: `README.md`
- Create: `docs/diary/kittens-phase3-3.md`

- [ ] **Step 1: 编写集成测试**

Create `tests/integration/test_intent_a2a.py`:

```python
import pytest
from click.testing import CliRunner
from src.cli.main import cli
from src.collaboration.intent_parser import parse_intent


def test_intent_ideate():
    """测试 ideate intent"""
    result = parse_intent("帮我设计 #ideate", cat_count=2)
    assert result.intent == "ideate"
    assert result.explicit is True


def test_intent_execute():
    """测试 execute intent"""
    result = parse_intent("帮我实现 #execute", cat_count=2)
    assert result.intent == "execute"
    assert result.explicit is True


def test_intent_auto_infer():
    """测试自动推断"""
    # 多猫默认 ideate
    result = parse_intent("帮我看看", cat_count=2)
    assert result.intent == "ideate"

    # 单猫默认 execute
    result = parse_intent("帮我看看", cat_count=1)
    assert result.intent == "execute"


def test_critique_mode():
    """测试 critique 标签"""
    result = parse_intent("检查代码 #critique", cat_count=1)
    assert "critique" in result.prompt_tags
```

- [ ] **Step 2: 更新 README**

Add to README:

```markdown
## A2A 智能协作 (Phase 3.3)

支持多猫协作模式：

```bash
# 并行讨论模式 (#ideate) - 多猫同时给出独立见解
@dev @review 这个架构怎么样？#ideate

# 串行执行模式 (#execute) - 猫按顺序接力完成
@dev @review 实现这个功能 #execute

# 批判性分析 (#critique) - 严格审查找出问题
@review 检查这段代码 #critique
```

### 自动模式选择

- **>=2 只猫**: 默认进入 `#ideate` 并行讨论
- **1 只猫**: 默认进入 `#execute` 串行执行
- **显式标签**: 使用用户指定的模式
```

- [ ] **Step 3: 创建小猫开发笔记**

Create `docs/diary/kittens-phase3-3.md` with development notes from the three cats.

- [ ] **Step 4: 运行所有测试**

```bash
pytest tests/collaboration/ tests/integration/test_intent_a2a.py -v
```

- [ ] **Step 5: 提交并打标签**

```bash
git add tests/integration/test_intent_a2a.py README.md docs/diary/kittens-phase3-3.md
git commit -m "test: add Phase 3.3 integration tests and docs

- Intent and A2A integration tests
- Updated README with collaboration features
- Kittens dev notes

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git tag -a v0.3.2 -m "Release v0.3.2 - Phase 3.3 A2A Collaboration"
```

---

## 实施总结

| Task | 描述 | 预估时间 |
|------|------|----------|
| 3.3.1 | IntentParser | 45 分钟 |
| 3.3.2 | A2AController | 1 小时 |
| 3.3.3 | 集成到 Chat | 30 分钟 |
| 3.3.4 | 测试和文档 | 30 分钟 |

**总计**: ~2.5 小时

---

**执行选项:**

1. **Subagent-Driven (推荐)** - 每个 task 独立子代理
2. **Inline Execution** - 本会话内批量执行

选择后使用对应的 skill 开始实施。
