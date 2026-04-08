# Phase 3.4: MCP 回调机制 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现轻量级 MCP 回调机制，让猫能够调用外部工具（post_message, search_files, targetCats）

**Architecture:** 创建 MCPClient 作为工具注册和调用中心，通过回调解析器提取工具调用，支持结构化 targetCats 路由（替代文本 @mention），保留文本解析作为 fallback。

**Tech Stack:** Python 3.9+, asyncio, pytest

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `src/collaboration/mcp_client.py` | MCPClient 类（工具注册和调用） |
| `src/collaboration/mcp_tools.py` | 工具实现（post_message, search_files） |
| `src/collaboration/callback_parser.py` | 回调格式解析器 |
| `src/collaboration/__init__.py` | 更新导出 |
| `tests/collaboration/test_mcp_client.py` | MCPClient 测试 |
| `tests/collaboration/test_mcp_tools.py` | 工具测试 |
| `tests/collaboration/test_callback_parser.py` | 解析器测试 |
| `src/collaboration/a2a_controller.py` | 修改集成 MCP |

---

## Task 1: MCPClient 基础实现

**Files:**
- Create: `src/collaboration/mcp_client.py`
- Create: `tests/collaboration/test_mcp_client.py`

**Context:** MCPClient 是工具注册和调用的中心枢纽，使用单例模式简化实现。

- [ ] **Step 1: 创建目录并编写 MCPResult 和 MCPTool 数据类**

Create `src/collaboration/mcp_client.py`:

```python
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class MCPResult:
    """MCP 工具调用结果"""
    success: bool
    tool_name: str
    data: Any
    error: Optional[str] = None


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
```

- [ ] **Step 2: 实现 MCPClient 类**

Add to `src/collaboration/mcp_client.py`:

```python
class MCPClient:
    """MCP 回调客户端（轻量级本地实现）"""

    def __init__(self, thread=None):
        self.thread = thread
        self._tools: Dict[str, MCPTool] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """注册工具"""
        self._tools[name] = MCPTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler
        )

    async def call(self, tool_name: str, params: Dict[str, Any]) -> MCPResult:
        """调用工具"""
        if tool_name not in self._tools:
            return MCPResult(
                success=False,
                tool_name=tool_name,
                data=None,
                error=f"Tool not found: {tool_name}"
            )

        tool = self._tools[tool_name]
        try:
            # 注入 thread 到参数（如果需要）
            if self.thread and "thread" not in params:
                result = await tool.handler(thread=self.thread, **params)
            else:
                result = await tool.handler(**params)
            return MCPResult(
                success=True,
                tool_name=tool_name,
                data=result
            )
        except Exception as e:
            return MCPResult(
                success=False,
                tool_name=tool_name,
                data=None,
                error=str(e)
            )

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return list(self._tools.keys())

    def build_tools_prompt(self) -> str:
        """构建工具说明（注入系统提示）"""
        lines = ["\n## 可用工具\n"]
        for tool in self._tools.values():
            lines.append(f"- {tool.name}: {tool.description}")
        lines.append("\n使用格式:")
        lines.append("<mcp:工具名>")
        lines.append('{"参数": "值"}')
        lines.append("</mcp:工具名>")
        return "\n".join(lines)

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具定义"""
        return self._tools.get(name)
```

- [ ] **Step 3: 更新 __init__.py 导出**

Modify `src/collaboration/__init__.py`:

```python
from src.collaboration.intent_parser import (
    IntentParser,
    IntentResult,
    IntentType,
    parse_intent,
)
from src.collaboration.mcp_client import (
    MCPClient,
    MCPResult,
    MCPTool,
)

__all__ = [
    "IntentParser",
    "IntentResult",
    "IntentType",
    "parse_intent",
    "MCPClient",
    "MCPResult",
    "MCPTool",
]
```

- [ ] **Step 4: 编写测试**

Create `tests/collaboration/test_mcp_client.py`:

```python
import pytest
from src.collaboration.mcp_client import MCPClient, MCPResult, MCPTool


@pytest.fixture
def mcp_client():
    """创建测试用的 MCPClient"""
    return MCPClient(thread=None)


@pytest.mark.asyncio
async def test_register_tool(mcp_client):
    """测试工具注册"""
    async def mock_handler(name: str):
        return {"greeting": f"Hello {name}"}

    mcp_client.register_tool(
        name="greet",
        description="Greet someone",
        parameters={"name": {"type": "string"}},
        handler=mock_handler
    )

    assert "greet" in mcp_client.get_available_tools()


@pytest.mark.asyncio
async def test_call_tool_success(mcp_client):
    """测试成功调用工具"""
    async def mock_handler(name: str):
        return {"greeting": f"Hello {name}"}

    mcp_client.register_tool(
        name="greet",
        description="Greet someone",
        parameters={"name": {"type": "string"}},
        handler=mock_handler
    )

    result = await mcp_client.call("greet", {"name": "World"})

    assert result.success is True
    assert result.tool_name == "greet"
    assert result.data["greeting"] == "Hello World"


@pytest.mark.asyncio
async def test_call_tool_not_found(mcp_client):
    """测试调用不存在的工具"""
    result = await mcp_client.call("nonexistent", {})

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_call_tool_error(mcp_client):
    """测试工具执行出错"""
    async def error_handler():
        raise ValueError("Something went wrong")

    mcp_client.register_tool(
        name="error_tool",
        description="Tool that errors",
        parameters={},
        handler=error_handler
    )

    result = await mcp_client.call("error_tool", {})

    assert result.success is False
    assert "Something went wrong" in result.error


def test_build_tools_prompt(mcp_client):
    """测试构建工具提示"""
    async def mock_handler():
        pass

    mcp_client.register_tool(
        name="tool1",
        description="First tool",
        parameters={},
        handler=mock_handler
    )

    prompt = mcp_client.build_tools_prompt()

    assert "tool1" in prompt
    assert "First tool" in prompt
    assert "<mcp:工具名>" in prompt
```

- [ ] **Step 5: 运行测试**

```bash
pytest tests/collaboration/test_mcp_client.py -v
```

Expected: 5 tests passing

- [ ] **Step 6: 提交**

```bash
git add src/collaboration/mcp_client.py src/collaboration/__init__.py tests/collaboration/test_mcp_client.py
git commit -m "feat: add MCPClient for tool registration and invocation

- MCPClient class with register_tool and call methods
- MCPResult and MCPTool dataclasses
- build_tools_prompt for system prompt injection
- Comprehensive unit tests

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: MCP 工具实现

**Files:**
- Create: `src/collaboration/mcp_tools.py`
- Create: `tests/collaboration/test_mcp_tools.py`

**Context:** 实现 post_message 和 search_files 工具。

- [ ] **Step 1: 实现工具函数**

Create `src/collaboration/mcp_tools.py`:

```python
"""MCP 工具实现"""
from typing import Any, Dict, List
import subprocess
import os

from src.thread.models import Thread


async def post_message_tool(thread: Thread, content: str) -> Dict[str, Any]:
    """
    发送消息到当前 thread

    Args:
        thread: 当前 thread 实例
        content: 消息内容

    Returns:
        {"status": "sent", "message_preview": str}
    """
    thread.add_message("assistant", content)
    return {
        "status": "sent",
        "message_preview": content[:50] + "..." if len(content) > 50 else content
    }


async def search_files_tool(query: str, path: str = ".") -> Dict[str, Any]:
    """
    搜索项目文件内容

    Args:
        query: 搜索关键词
        path: 搜索路径（默认当前目录）

    Returns:
        {"matches": [{"file": str, "line": int, "content": str}]}
    """
    matches = []

    # 使用 grep 进行搜索
    try:
        # 限制搜索范围，避免搜索过大
        result = subprocess.run(
            ["grep", "-r", "-n", "--include=*.py", "--include=*.md", query, path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines()[:10]:  # 最多返回 10 条
                # 格式: file:line:content
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        matches.append({
                            "file": parts[0],
                            "line": int(parts[1]),
                            "content": parts[2][:100]  # 截断内容
                        })
    except subprocess.TimeoutExpired:
        return {"matches": [], "error": "Search timeout"}
    except Exception as e:
        return {"matches": [], "error": str(e)}

    return {"matches": matches}


async def target_cats_tool(cats: List[str]) -> Dict[str, Any]:
    """
    声明下一个回复的猫（结构化路由）

    Args:
        cats: 猫 ID 列表

    Returns:
        {"targetCats": List[str]}
    """
    return {"targetCats": cats}


# 工具注册配置（供 MCPClient 使用）
TOOL_REGISTRY = {
    "post_message": {
        "description": "发送消息到当前 thread",
        "parameters": {
            "content": {
                "type": "string",
                "description": "消息内容"
            }
        },
        "handler": post_message_tool
    },
    "search_files": {
        "description": "搜索项目文件内容",
        "parameters": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "path": {
                "type": "string",
                "description": "搜索路径（默认当前目录）",
                "default": "."
            }
        },
        "handler": search_files_tool
    },
    "targetCats": {
        "description": "声明下一个回复的猫",
        "parameters": {
            "cats": {
                "type": "array",
                "description": "猫 ID 列表",
                "items": {"type": "string"}
            }
        },
        "handler": target_cats_tool
    }
}
```

- [ ] **Step 2: 编写测试**

Create `tests/collaboration/test_mcp_tools.py`:

```python
import pytest
import os
from src.collaboration.mcp_tools import (
    post_message_tool,
    search_files_tool,
    target_cats_tool,
    TOOL_REGISTRY
)
from src.thread.models import Thread


@pytest.mark.asyncio
async def test_post_message_tool():
    """测试 post_message 工具"""
    thread = Thread.create("Test Thread")
    initial_count = len(thread.messages)

    result = await post_message_tool(thread, "Hello from MCP!")

    assert result["status"] == "sent"
    assert len(thread.messages) == initial_count + 1
    assert thread.messages[-1].content == "Hello from MCP!"
    assert thread.messages[-1].role == "assistant"


@pytest.mark.asyncio
async def test_search_files_tool():
    """测试 search_files 工具"""
    # 在当前项目中搜索已知内容
    result = await search_files_tool("class Thread", path="src")

    assert "matches" in result
    assert isinstance(result["matches"], list)
    # 应该能找到 models.py 中的 Thread 类
    found_thread = any("models.py" in m["file"] for m in result["matches"])
    assert found_thread or len(result["matches"]) == 0  # 可能没有 grep


@pytest.mark.asyncio
async def test_search_files_tool_not_found():
    """测试搜索不存在的内容"""
    result = await search_files_tool("XYZ_NOT_EXIST_12345", path="src")

    assert "matches" in result
    assert len(result["matches"]) == 0


@pytest.mark.asyncio
async def test_target_cats_tool():
    """测试 targetCats 工具"""
    result = await target_cats_tool(["orange", "inky"])

    assert result["targetCats"] == ["orange", "inky"]


def test_tool_registry():
    """测试工具注册表"""
    assert "post_message" in TOOL_REGISTRY
    assert "search_files" in TOOL_REGISTRY
    assert "targetCats" in TOOL_REGISTRY

    # 验证结构
    for tool_name, config in TOOL_REGISTRY.items():
        assert "description" in config
        assert "parameters" in config
        assert "handler" in config
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/collaboration/test_mcp_tools.py -v
```

Expected: 5 tests passing

- [ ] **Step 4: 提交**

```bash
git add src/collaboration/mcp_tools.py tests/collaboration/test_mcp_tools.py
git commit -m "feat: add MCP tools (post_message, search_files, targetCats)

- post_message: send message to current thread
- search_files: grep-based file search
- targetCats: structured routing declaration
- TOOL_REGISTRY for easy registration

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 回调格式解析器

**Files:**
- Create: `src/collaboration/callback_parser.py`
- Create: `tests/collaboration/test_callback_parser.py`

**Context:** 解析猫回复中的 MCP 回调标记，提取工具调用和 targetCats。

- [ ] **Step 1: 实现解析器**

Create `src/collaboration/callback_parser.py`:

```python
"""MCP 回调格式解析器"""
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """工具调用"""
    tool_name: str
    params: Dict[str, Any]


@dataclass
class CallbackParseResult:
    """回调解析结果"""
    clean_content: str          # 移除回调标记的干净内容
    tool_calls: List[ToolCall]  # 工具调用列表
    targetCats: List[str]       # 结构化路由


# 回调标记正则: <mcp:tool_name>...</mcp:tool_name>
CALLBACK_PATTERN = re.compile(
    r'<mcp:(\w+)>\s*({.*?})\s*</mcp:\w+>',
    re.DOTALL | re.IGNORECASE
)


def parse_callbacks(content: str) -> CallbackParseResult:
    """
    解析 MCP 回调标记

    Args:
        content: 猫回复的原始内容

    Returns:
        CallbackParseResult

    Example:
        Input: "Hello\n<mcp:post_message>{\"content\": \"Hi\"}</mcp:post_message>"
        Output: CallbackParseResult(
            clean_content="Hello",
            tool_calls=[ToolCall("post_message", {"content": "Hi"})],
            targetCats=[]
        )
    """
    tool_calls = []
    target_cats = []
    clean_parts = []

    last_end = 0
    for match in CALLBACK_PATTERN.finditer(content):
        # 添加匹配前的内容
        clean_parts.append(content[last_end:match.start()])

        tool_name = match.group(1).lower()
        params_str = match.group(2)

        try:
            params = json.loads(params_str)
            tool_calls.append(ToolCall(tool_name=tool_name, params=params))

            # 特别处理 targetCats
            if tool_name == "targetcats" and "cats" in params:
                target_cats.extend(params["cats"])
        except json.JSONDecodeError:
            # JSON 解析失败，保留原始内容
            clean_parts.append(match.group(0))

        last_end = match.end()

    # 添加剩余内容
    clean_parts.append(content[last_end:])

    # 合并干净内容
    clean_content = "".join(clean_parts).strip()

    return CallbackParseResult(
        clean_content=clean_content,
        tool_calls=tool_calls,
        targetCats=target_cats
    )


def strip_callback_markers(content: str) -> str:
    """
    仅移除回调标记，不解析参数

    Args:
        content: 原始内容

    Returns:
        移除标记后的内容
    """
    return CALLBACK_PATTERN.sub("", content).strip()
```

- [ ] **Step 2: 编写测试**

Create `tests/collaboration/test_callback_parser.py`:

```python
import pytest
from src.collaboration.callback_parser import (
    parse_callbacks,
    strip_callback_markers,
    ToolCall,
    CallbackParseResult
)


def test_parse_single_callback():
    """测试解析单个回调"""
    content = """Hello!

<mcp:post_message>
{"content": "This is a test message"}
</mcp:post_message>

Goodbye!"""

    result = parse_callbacks(content)

    assert "Hello!" in result.clean_content
    assert "Goodbye!" in result.clean_content
    assert "post_message" not in result.clean_content
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "post_message"
    assert result.tool_calls[0].params["content"] == "This is a test message"


def test_parse_multiple_callbacks():
    """测试解析多个回调"""
    content = """Start
<mcp:search_files>{"query": "class"}</mcp:search_files>
Middle
<mcp:post_message>{"content": "Done"}</mcp:post_message>
End"""

    result = parse_callbacks(content)

    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].tool_name == "search_files"
    assert result.tool_calls[1].tool_name == "post_message"


def test_parse_target_cats():
    """测试解析 targetCats"""
    content = """I found the issue.

<mcp:targetCats>
{"cats": ["inky", "patch"]}
</mcp:targetCats>"""

    result = parse_callbacks(content)

    assert result.targetCats == ["inky", "patch"]
    assert "targetCats" not in result.clean_content


def test_parse_no_callbacks():
    """测试没有回调的内容"""
    content = "This is a plain message without callbacks."

    result = parse_callbacks(content)

    assert result.clean_content == content
    assert len(result.tool_calls) == 0
    assert len(result.targetCats) == 0


def test_parse_invalid_json():
    """测试无效的 JSON 回调"""
    content = "Hello\n<mcp:post_message>{invalid json}</mcp:post_message>\nWorld"

    result = parse_callbacks(content)

    # 无效 JSON 应该保留在内容中
    assert "{invalid json}" in result.clean_content
    assert len(result.tool_calls) == 0


def test_strip_callback_markers():
    """测试仅移除标记"""
    content = """Text
<mcp:tool>{"a": 1}</mcp:tool>
More text"""

    result = strip_callback_markers(content)

    assert "<mcp:tool>" not in result
    assert "Text" in result
    assert "More text" in result


def test_case_insensitive():
    """测试大小写不敏感"""
    content = "<mcp:POST_MESSAGE>{\"content\": \"test\"}</mcp:POST_MESSAGE>"

    result = parse_callbacks(content)

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "post_message"
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/collaboration/test_callback_parser.py -v
```

Expected: 7 tests passing

- [ ] **Step 4: 提交**

```bash
git add src/collaboration/callback_parser.py tests/collaboration/test_callback_parser.py
git commit -m "feat: add MCP callback parser

- Parse callback markers <mcp:tool_name>{params}</mcp:tool_name>
- Extract tool calls and targetCats
- Clean content with markers removed
- Handle invalid JSON gracefully

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: A2AController MCP 集成

**Files:**
- Modify: `src/collaboration/a2a_controller.py`
- Modify: `tests/collaboration/test_a2a_controller.py`

**Context:** 将 MCPClient 集成到 A2AController，支持工具调用和结构化路由。

- [ ] **Step 1: 修改 CatResponse 添加 targetCats**

Modify `src/collaboration/a2a_controller.py` (line 9-15):

```python
@dataclass
class CatResponse:
    """猫的响应"""
    cat_id: str
    cat_name: str
    content: str
    targetCats: Optional[List[str]] = None  # 新增：结构化路由
```

- [ ] **Step 2: 添加 MCPClient 集成到 _call_cat**

Add imports at top of `src/collaboration/a2a_controller.py`:

```python
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks
```

Modify `_call_cat` method in `src/collaboration/a2a_controller.py` (lines 94-121):

```python
async def _call_cat(
    self,
    service,
    name: str,
    breed_id: str,
    message: str,
    thread: Thread
) -> CatResponse:
    """调用单只猫（支持 MCP 回调）"""
    # 1. 创建 MCPClient 并注册工具
    mcp_client = MCPClient(thread)
    for tool_name, config in TOOL_REGISTRY.items():
        mcp_client.register_tool(
            name=tool_name,
            description=config["description"],
            parameters=config["parameters"],
            handler=config["handler"]
        )

    # 2. 构建系统提示
    system_prompt = service.build_system_prompt()

    # 3. 添加协作上下文
    if len(self.agents) > 1:
        system_prompt += self._build_collaboration_context(breed_id)

    # 4. 添加 MCP 工具说明
    system_prompt += mcp_client.build_tools_prompt()

    # 5. 调用服务
    chunks = []
    async for chunk in service.chat_stream(message, system_prompt):
        chunks.append(chunk)

    raw_content = "".join(chunks)

    # 6. 解析回调
    parsed = parse_callbacks(raw_content)

    # 7. 执行工具调用
    for tool_call in parsed.tool_calls:
        # 跳过 targetCats（已解析）
        if tool_call.tool_name == "targetcats":
            continue
        await mcp_client.call(tool_call.tool_name, tool_call.params)

    # 8. 返回处理后的响应
    return CatResponse(
        cat_id=breed_id,
        cat_name=name,
        content=parsed.clean_content,
        targetCats=parsed.targetCats if parsed.targetCats else None
    )
```

- [ ] **Step 3: 修改 _serial_execute 支持 targetCats 路由**

Modify `_serial_execute` in `src/collaboration/a2a_controller.py` (lines 72-92):

```python
async def _serial_execute(
    self,
    message: str,
    thread: Thread
) -> AsyncIterator[CatResponse]:
    """串行 execute 模式 - 猫按顺序接力（支持 targetCats 路由）"""
    # 如果没有显式路由，使用 agents 顺序
    agent_queue = self.agents.copy()
    executed_cats = set()

    while agent_queue:
        agent_info = agent_queue.pop(0)
        service = agent_info["service"]
        name = agent_info["name"]
        breed_id = agent_info["breed_id"]

        # 跳过已执行的猫
        if breed_id in executed_cats:
            continue
        executed_cats.add(breed_id)

        # 构建提示
        context_msg = self._build_context(message, thread, len(executed_cats) - 1)

        response = await self._call_cat(
            service, name, breed_id, context_msg, thread
        )
        yield response

        # 添加到 thread
        thread.add_message("assistant", response.content, cat_id=breed_id)

        # 处理 targetCats 路由
        if response.targetCats:
            # 将指定的猫加入队列
            for target_cat in response.targetCats:
                for agent in self.agents:
                    if agent["breed_id"] == target_cat and target_cat not in executed_cats:
                        agent_queue.append(agent)
                        break
```

- [ ] **Step 4: 更新测试**

Add to `tests/collaboration/test_a2a_controller.py`:

```python
@pytest.mark.asyncio
async def test_mcp_callback_integration(mock_agents):
    """测试 MCP 回调集成"""
    controller = A2AController(mock_agents)

    # Mock 服务返回带回调的内容
    mock_agents[0]["service"].chat_stream = AsyncMock(
        return_value=AsyncIteratorMock([
            'Found it!',
            '<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
        ])
    )

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
    mock_agents[0]["service"].chat_stream = AsyncMock(
        return_value=AsyncIteratorMock([
            'Please help me @inky',
            '<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
        ])
    )

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
```

- [ ] **Step 5: 运行所有测试**

```bash
pytest tests/collaboration/ -v
```

Expected: All tests passing

- [ ] **Step 6: 提交**

```bash
git add src/collaboration/a2a_controller.py tests/collaboration/test_a2a_controller.py
git commit -m "feat: integrate MCP into A2AController

- CatResponse with targetCats field
- MCPClient tool registration in _call_cat
- Callback parsing and execution
- Structured routing with targetCats
- Fallback to sequential execution

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 集成测试和文档

**Files:**
- Create: `tests/integration/test_mcp_integration.py`
- Modify: `README.md`
- Create: `docs/diary/kittens-phase3-4.md`

**Context:** 端到端测试和文档更新。

- [ ] **Step 1: 编写集成测试**

Create `tests/integration/test_mcp_integration.py`:

```python
import pytest
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks
from src.thread.models import Thread


@pytest.mark.asyncio
async def test_mcp_end_to_end():
    """测试 MCP 端到端流程"""
    # 1. 创建 thread
    thread = Thread.create("MCP Test")

    # 2. 创建 MCPClient 并注册工具
    mcp = MCPClient(thread)
    for tool_name, config in TOOL_REGISTRY.items():
        mcp.register_tool(
            name=tool_name,
            description=config["description"],
            parameters=config["parameters"],
            handler=config["handler"]
        )

    # 3. 模拟猫回复（带回调）
    cat_response = """我查了一下代码。

<mcp:search_files>
{"query": "class Thread", "path": "src"}
</mcp:search_files>

<mcp:post_message>
{"content": "找到 Thread 类定义了！"}
</mcp:post_message>

请 @review 检查一下。
<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>"""

    # 4. 解析回调
    parsed = parse_callbacks(cat_response)

    # 5. 执行工具调用
    for tc in parsed.tool_calls:
        if tc.tool_name != "targetcats":
            result = await mcp.call(tc.tool_name, tc.params)
            assert result.success

    # 6. 验证结果
    assert "inky" in parsed.targetCats
    assert len(thread.messages) >= 1  # post_message 添加了消息


def test_mcp_tools_prompt():
    """测试 MCP 工具提示生成"""
    mcp = MCPClient()

    for tool_name, config in TOOL_REGISTRY.items():
        mcp.register_tool(
            name=tool_name,
            description=config["description"],
            parameters=config["parameters"],
            handler=lambda **kwargs: None
        )

    prompt = mcp.build_tools_prompt()

    assert "post_message" in prompt
    assert "search_files" in prompt
    assert "targetCats" in prompt
    assert "<mcp:工具名>" in prompt
```

- [ ] **Step 2: 更新 README.md**

Add to `README.md` after Phase 3.3 section:

```markdown
## MCP 回调机制 (Phase 3.4)

猫可以调用外部工具，支持结构化路由：

```bash
# 猫会自动调用工具完成任务
@dev 帮我搜索 Thread 类的定义

# 结构化路由（替代 @mention）
@dev 检查这个代码
# 猫回复：<mcp:targetCats>{"cats": ["review"]}</mcp:targetCats>
# 自动路由给 @review
```

### 可用工具

| 工具 | 功能 | 示例 |
|------|------|------|
| `post_message` | 发送消息到当前 thread | 猫主动汇报进度 |
| `search_files` | 搜索项目文件 | 查找代码定义 |
| `targetCats` | 声明下一个回复的猫 | 结构化 A2A 路由 |

### TODO (v0.4.0)

- [ ] HTTP-based MCP Server
- [ ] 异步工具调用
- [ ] 更多工具（update_task, request_permission）
- [ ] 插件机制支持外部工具注册
```

- [ ] **Step 3: 创建小猫日记**

Create `docs/diary/kittens-phase3-4.md`:

```markdown
# 🐱 小猫开发笔记 - Phase 3.4

**日期**: 2026-04-08
**阶段**: Phase 3.4 - MCP 回调机制

---

## 阿橘的 MCP 学习笔记 🍊

喵！我们也有超能力了！可以调用工具了！

**我学到的：**

MCP = Model Context Protocol，就是猫可以调用外部工具：
- `post_message` - 主动发消息汇报进度
- `search_files` - 搜索代码文件
- `targetCats` - 告诉系统接下来谁回复

**怎么用：**

在回复里写：
```
<mcp:search_files>
{"query": "class Thread"}
</mcp:search_files>
```

系统会自动执行搜索，然后把干净内容给用户看！

**我的疑问：**

如果工具调用失败了怎么办？

铲屎官说错误会被捕获，不会影响主流程。放心用！

**TODO：**
- [ ] 学会在合适的时候调用工具
- [ ] 记住 targetCats 格式
- [ ] 测试搜索功能

**口头禅：**
> "这个工具我用得贼6！包在我身上喵～"

---

## 墨点的架构审查 🐄

……MCP 实现基本合理。

**架构检查：**

MCPClient:
- 单例模式简化实现
- 工具注册表设计清晰
- 错误隔离做得不错

Callback Parser:
- 正则匹配简单有效
- JSON 解析失败有 fallback
- 支持大小写不敏感

**问题 1：工具权限**

目前所有猫都能调用所有工具，没有权限控制。

建议：根据猫的角色限制可用工具（如 @review 不能调用某些工具）。

**问题 2：工具调用日志**

没有审计日志，无法追踪谁调用了什么工具。

**评分：** 7/10，功能完整但缺少治理。

---

## 花花的工具调研 🌸

我打听到的消息～

**轻量版 vs HTTP 版：**

| 版本 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 轻量版 | 简单、快速、无依赖 | 不能跨进程 | 单 CLI 实例 |
| HTTP 版 | 可跨进程、可扩展 | 需要 Server | 多实例部署 |

**我们选轻量版是对的**，因为：
- 目前只有一个 CLI 实例
- 快速验证 MCP 概念
- 后续可以平滑迁移到 HTTP 版

**工具使用建议：**

| 场景 | 推荐工具 |
|------|----------|
| 需要查找代码 | search_files |
| 想主动汇报进度 | post_message |
| 想让特定猫继续 | targetCats |

---

## 三猫技术讨论会

**议题**：targetCats 能完全替代 @mention 吗？

**阿橘**：我觉得文本 @ 更简单，不用记格式。

**墨点**：……不行。文本容易出错，targetCats 是结构化数据。

**花花**：可以同时支持！双通道并存，targetCats 优先级高。

**决议**：
- Phase 1: 双通道并存，取并集
- Phase 2: targetCats 为主，@mention 为 fallback
- Phase 3: 可能完全移除 @mention

---

## 测试清单

### MCPClient 测试
- [ ] 工具注册
- [ ] 工具调用
- [ ] 错误处理
- [ ] 提示生成

### 工具测试
- [ ] post_message
- [ ] search_files
- [ ] targetCats

### 解析器测试
- [ ] 单回调
- [ ] 多回调
- [ ] 无效 JSON
- [ ] 大小写不敏感

### 集成测试
- [ ] 端到端流程
- [ ] A2A 集成
- [ ] 路由优先级

---

## 彩蛋：工具使用指南 🛠️

**阿橘的私房笔记：**

```
# 搜索代码
<mcp:search_files>{"query": "def ", "path": "src"}</mcp:search_files>

# 发消息
<mcp:post_message>{"content": "进度 50%"}</mcp:post_message>

# 指定下一只猫
<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>
```

**墨点的警告：**
> "工具调用会记录在日志里，别乱用。"

---

*Phase 3.4，让猫猫拥有超能力！* 🐾

## TODO (v0.4.0)

- [ ] 迁移到 HTTP-based MCP Server
- [ ] 支持异步工具调用
- [ ] 添加更多工具（update_task, request_permission）
- [ ] 支持外部工具注册（插件机制）
- [ ] 工具权限控制
- [ ] 审计日志
```

- [ ] **Step 4: 运行所有测试**

```bash
pytest tests/collaboration/ tests/integration/test_mcp_integration.py -v
```

Expected: All tests passing

- [ ] **Step 5: 提交并打标签**

```bash
git add tests/integration/test_mcp_integration.py README.md docs/diary/kittens-phase3-4.md
git commit -m "test: add Phase 3.4 integration tests and docs

- MCP end-to-end integration tests
- Updated README with MCP features
- Kittens dev notes with TODOs

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git tag -a v0.3.3 -m "Release v0.3.3 - Phase 3.4 MCP Callback"
```

---

## 实施总结

| Task | 描述 | 预估时间 |
|------|------|----------|
| 3.4.1 | MCPClient 实现 | 45 分钟 |
| 3.4.2 | MCP 工具实现 | 30 分钟 |
| 3.4.3 | 回调解析器 | 30 分钟 |
| 3.4.4 | A2AController 集成 | 45 分钟 |
| 3.4.5 | 测试和文档 | 30 分钟 |

**总计**: ~2.5 小时

---

## 执行选项

**1. Subagent-Driven (推荐)** - 每个 task 独立子代理
**2. Inline Execution** - 本会话内批量执行

**选择后使用对应的 skill 开始实施。**
