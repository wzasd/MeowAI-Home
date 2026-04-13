# Phase 6: 多模型支持系统 (v0.6.0) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建企业级多模型架构，实现多 Provider 适配器、注册表、路由、会话链、配置系统。

**Architecture:** CLI 子进程模式（ADR-001），每个 Provider 独立 Service 实现，统一 `invoke()` AsyncGenerator 接口。双注册表（CatRegistry 配置 + AgentRegistry 服务）。配置级联：env > cat-config.json > 硬编码默认值。

**Tech Stack:** Python 3.10+, asyncio, pytest, FastAPI, aiofiles

**参考:** `docs/decisions/001-cli-as-backend.md`

---

## 文件结构总览

| 文件 | 职任 | 状态 |
|------|------|------|
| `src/models/cat_registry.py` | 全局猫配置注册表 | 新建 |
| `src/models/agent_registry.py` | 服务实例注册表 | 新建 |
| `src/models/types.py` | 共享类型定义 | 新建 |
| `src/providers/base.py` | Provider 基类（升级 AgentService） | 新建 |
| `src/providers/claude_provider.py` | Claude CLI 适配器 | 新建 |
| `src/providers/codex_provider.py` | Codex CLI 适配器 | 新建 |
| `src/providers/gemini_provider.py` | Gemini CLI 适配器 | 新建 |
| `src/providers/opencode_provider.py` | OpenCode CLI 适配器 | 新建 |
| `src/providers/__init__.py` | Provider 工厂 | 新建 |
| `src/utils/cli_spawn.py` | CLI 进程生命周期管理 | 新建 |
| `src/utils/ndjson_stream.py` | 流式 NDJSON 解析器 | 新建 |
| `src/config/account_resolver.py` | subscription/api_key 认证解析 | 新建 |
| `src/config/budgets.py` | Context Budget 管理 | 新建 |
| `src/config/model_resolver.py` | 模型解析（env > config > default） | 新建 |
| `src/config/context_windows.py` | 模型上下文窗口大小表 | 新建 |
| `src/router/agent_router.py` | 升级路由（长匹配 + routing policy） | 修改 |
| `src/session/chain.py` | 会话链管理 | 新建 |
| `src/session/__init__.py` | Session 包 | 新建 |
| `src/invocation/tracker.py` | 调用追踪器 | 新建 |
| `src/invocation/stream_merge.py` | 并行流合并 | 新建 |
| `src/invocation/__init__.py` | Invocation 包 | 新建 |
| `scripts/anthropic_proxy.py` | Anthropic 网关代理 | 新建 |
| `src/cats/base.py` | 保留但标记 deprecated | 修改 |
| `src/cats/orange/service.py` | 迁移到 providers | 修改 |
| `src/web/app.py` | 使用新注册表 | 修改 |
| `src/web/routes/ws.py` | 使用新路由 | 修改 |

---

## 子阶段 6.1: 基础设施

### Task 1: 共享类型定义

**Files:**
- Create: `src/models/__init__.py`
- Create: `src/models/types.py`
- Test: `tests/models/test_types.py`

- [ ] **Step 1: 写类型定义测试**

```python
# tests/models/test_types.py
import pytest
from src.models.types import (
    CatConfig, CatId, VariantConfig, ContextBudget,
    AgentMessage, AgentMessageType, ProviderType,
    TokenUsage, InvocationOptions
)


def test_cat_config_creation():
    config = CatConfig(
        cat_id=CatId("opus"),
        breed_id="ragdoll",
        name="布偶猫",
        display_name="宪宪",
        provider="anthropic",
        default_model="claude-opus-4-6",
        personality="温柔但有主见",
        mention_patterns=["@opus", "@布偶猫"],
        avatar="/avatars/opus.png",
        color_primary="#9B7EBD",
        color_secondary="#E8DFF5",
        cli_command="claude",
        cli_args=["--output-format", "stream-json"],
        budget=ContextBudget(
            max_prompt_tokens=180000,
            max_context_tokens=160000,
            max_messages=200,
            max_content_length_per_msg=10000
        )
    )
    assert config.cat_id == "opus"
    assert config.provider == "anthropic"
    assert config.budget.max_prompt_tokens == 180000


def test_agent_message_types():
    msg = AgentMessage(type=AgentMessageType.TEXT, content="hello")
    assert msg.type == AgentMessageType.TEXT
    assert msg.content == "hello"


def test_token_usage_defaults():
    usage = TokenUsage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cost_usd == 0.0


def test_invocation_options():
    opts = InvocationOptions(system_prompt="test", timeout=300.0)
    assert opts.system_prompt == "test"
    assert opts.timeout == 300.0
    assert opts.session_id is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_types.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: 实现类型定义**

```python
# src/models/__init__.py
from src.models.types import (
    CatConfig, CatId, VariantConfig, ContextBudget,
    AgentMessage, AgentMessageType, ProviderType,
    TokenUsage, InvocationOptions
)
```

```python
# src/models/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


# Brand type for cat IDs
CatId = str


class ProviderType(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DARE = "dare"
    ANTIGRAVITY = "antigravity"
    OPENCODE = "opencode"
    A2A = "a2a"


class AgentMessageType(str, Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    DONE = "done"
    USAGE = "usage"


@dataclass
class ContextBudget:
    max_prompt_tokens: int = 100000
    max_context_tokens: int = 60000
    max_messages: int = 200
    max_content_length_per_msg: int = 10000


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0

    def merge(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=other.input_tokens or self.input_tokens,
            output_tokens=self.output_tokens + (other.output_tokens or 0),
            cache_read_tokens=self.cache_read_tokens + (other.cache_read_tokens or 0),
            cache_creation_tokens=self.cache_creation_tokens + (other.cache_creation_tokens or 0),
            cost_usd=self.cost_usd + (other.cost_usd or 0.0),
        )


@dataclass
class VariantConfig:
    id: str
    cat_id: CatId
    provider: str
    default_model: str
    personality: str = ""
    cli_command: str = ""
    cli_args: List[str] = field(default_factory=list)
    mention_patterns: List[str] = field(default_factory=list)
    avatar: Optional[str] = None
    color_primary: str = "#666666"
    color_secondary: str = "#EEEEEE"
    budget: ContextBudget = field(default_factory=ContextBudget)
    mcp_support: bool = False
    effort: str = "high"


@dataclass
class CatConfig:
    cat_id: CatId
    breed_id: str
    name: str
    display_name: str
    provider: str
    default_model: str
    personality: str = ""
    mention_patterns: List[str] = field(default_factory=list)
    avatar: Optional[str] = None
    color_primary: str = "#666666"
    color_secondary: str = "#EEEEEE"
    cli_command: str = ""
    cli_args: List[str] = field(default_factory=list)
    budget: ContextBudget = field(default_factory=ContextBudget)
    variant_id: Optional[str] = None
    breed_name: Optional[str] = None
    role_description: Optional[str] = None
    team_strengths: Optional[str] = None
    caution: Optional[str] = None
    mcp_support: bool = False
    effort: str = "high"


@dataclass
class AgentMessage:
    type: AgentMessageType
    content: str = ""
    cat_id: Optional[CatId] = None
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    usage: Optional[TokenUsage] = None
    session_id: Optional[str] = None


@dataclass
class InvocationOptions:
    system_prompt: Optional[str] = None
    timeout: float = 300.0
    session_id: Optional[str] = None
    effort: Optional[str] = None
    mcp_config: Optional[Dict[str, Any]] = None
    extra_args: List[str] = field(default_factory=list)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_types.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/models/ tests/models/
git commit -m "feat: add shared types for Phase 6 multi-model system"
```

---

### Task 2: CatRegistry — 全局配置注册表

**Files:**
- Create: `src/models/cat_registry.py`
- Test: `tests/models/test_cat_registry.py`

**Context:** 替代现有 `CatConfigLoader`（保留向后兼容），提供全局猫配置注册表。从 `cat-config.json` 的 breeds+variants 扁平化为 cat_id -> CatConfig 映射。

- [ ] **Step 1: 写测试**

```python
# tests/models/test_cat_registry.py
import pytest
from src.models.cat_registry import CatRegistry, cat_registry
from src.models.types import CatConfig


@pytest.fixture
def sample_breeds():
    return [
        {
            "id": "ragdoll",
            "catId": "opus",
            "name": "布偶猫",
            "displayName": "布偶猫",
            "nickname": "宪宪",
            "avatar": "/avatars/opus.png",
            "color": {"primary": "#9B7EBD", "secondary": "#E8DFF5"},
            "mentionPatterns": ["@opus", "@布偶猫", "@宪宪"],
            "roleDescription": "主架构师",
            "defaultVariantId": "opus-default",
            "variants": [
                {
                    "id": "opus-default",
                    "catId": "opus",
                    "provider": "anthropic",
                    "defaultModel": "claude-opus-4-6",
                    "personality": "温柔但有主见",
                    "cli": {
                        "command": "claude",
                        "outputFormat": "stream-json",
                        "defaultArgs": ["--output-format", "stream-json"],
                    },
                    "contextBudget": {
                        "maxPromptTokens": 180000,
                        "maxContextTokens": 160000,
                        "maxMessages": 200,
                        "maxContentLengthPerMsg": 10000,
                    },
                },
                {
                    "id": "opus-sonnet",
                    "catId": "sonnet",
                    "variantLabel": "Sonnet",
                    "displayName": "布偶猫",
                    "mentionPatterns": ["@sonnet"],
                    "provider": "anthropic",
                    "defaultModel": "claude-sonnet-4-6",
                    "personality": "快速灵活",
                    "cli": {
                        "command": "claude",
                        "outputFormat": "stream-json",
                        "defaultArgs": ["--output-format", "stream-json", "--model", "claude-sonnet-4-6"],
                    },
                    "contextBudget": {
                        "maxPromptTokens": 180000,
                        "maxContextTokens": 160000,
                        "maxMessages": 200,
                        "maxContentLengthPerMsg": 10000,
                    },
                },
            ],
        }
    ]


class TestCatRegistry:
    def test_register_and_get(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)

        config = reg.get("opus")
        assert config.cat_id == "opus"
        assert config.provider == "anthropic"
        assert config.default_model == "claude-opus-4-6"

    def test_register_multiple_variants(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)

        assert reg.has("opus")
        assert reg.has("sonnet")

        sonnet = reg.get("sonnet")
        assert sonnet.default_model == "claude-sonnet-4-6"

    def test_get_not_found_raises(self):
        reg = CatRegistry()
        with pytest.raises(KeyError, match="nonexistent"):
            reg.get("nonexistent")

    def test_try_get_returns_none(self):
        reg = CatRegistry()
        assert reg.try_get("nonexistent") is None

    def test_get_all_ids(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        ids = reg.get_all_ids()
        assert "opus" in ids
        assert "sonnet" in ids

    def test_get_by_mention(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)

        config = reg.get_by_mention("@布偶猫")
        assert config is not None
        assert config.cat_id == "opus"

    def test_get_by_mention_case_insensitive(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)

        config = reg.get_by_mention("@OPUS")
        assert config is not None
        assert config.cat_id == "opus"

    def test_reset(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        reg.reset()
        assert reg.has("opus") is False

    def test_default_cat(self, sample_breeds):
        reg = CatRegistry()
        reg.load_from_breeds(sample_breeds)
        reg.set_default("opus")
        assert reg.get_default_id() == "opus"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_cat_registry.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 CatRegistry**

```python
# src/models/cat_registry.py
from typing import Dict, List, Optional
from src.models.types import CatConfig, CatId, ContextBudget


class CatRegistry:
    """全局猫配置注册表 — 从 cat-config.json breeds+variants 扁平化"""

    def __init__(self):
        self._cats: Dict[CatId, CatConfig] = {}
        self._mention_index: Dict[str, CatId] = {}  # lowercase mention -> catId
        self._default_id: Optional[CatId] = None

    def load_from_breeds(self, breeds: List[dict]) -> None:
        """从 cat-config.json breeds 数组加载所有猫"""
        for breed in breeds:
            breed_id = breed["id"]
            breed_name = breed.get("name", breed_id)
            default_variant_id = breed.get("defaultVariantId")

            for variant in breed.get("variants", []):
                cat_id = variant.get("catId", breed.get("catId"))
                if not cat_id:
                    continue

                cli_config = variant.get("cli", {})
                budget_data = variant.get("contextBudget", {})
                color_data = breed.get("color", {})

                config = CatConfig(
                    cat_id=cat_id,
                    breed_id=breed_id,
                    name=breed.get("displayName", breed_name),
                    display_name=variant.get("displayName", breed.get("displayName", breed_name)),
                    provider=variant.get("provider", ""),
                    default_model=variant.get("defaultModel", ""),
                    personality=variant.get("personality", ""),
                    mention_patterns=variant.get("mentionPatterns", breed.get("mentionPatterns", [])),
                    avatar=variant.get("avatar", breed.get("avatar")),
                    color_primary=color_data.get("primary", "#666666"),
                    color_secondary=color_data.get("secondary", "#EEEEEE"),
                    cli_command=cli_config.get("command", ""),
                    cli_args=cli_config.get("defaultArgs", []),
                    budget=ContextBudget(
                        max_prompt_tokens=budget_data.get("maxPromptTokens", 100000),
                        max_context_tokens=budget_data.get("maxContextTokens", 60000),
                        max_messages=budget_data.get("maxMessages", 200),
                        max_content_length_per_msg=budget_data.get("maxContentLengthPerMsg", 10000),
                    ),
                    variant_id=variant.get("id"),
                    breed_name=breed_name,
                    role_description=breed.get("roleDescription"),
                    team_strengths=breed.get("teamStrengths"),
                    caution=breed.get("caution"),
                    mcp_support=variant.get("mcpSupport", False),
                    effort=cli_config.get("effort", "high"),
                )
                self._cats[cat_id] = config

                # 索引 mention patterns
                for pattern in config.mention_patterns:
                    self._mention_index[pattern.lower().lstrip("@")] = cat_id
                    self._mention_index[pattern.lower()] = cat_id

            # 设置默认猫（breed 的 defaultVariantId）
            if default_variant_id:
                for variant in breed.get("variants", []):
                    if variant.get("id") == default_variant_id:
                        cid = variant.get("catId", breed.get("catId"))
                        if cid and (self._default_id is None):
                            self._default_id = cid

    def register(self, cat_id: CatId, config: CatConfig) -> None:
        """手动注册一只猫"""
        if cat_id in self._cats:
            raise ValueError(f"Cat already registered: {cat_id}")
        self._cats[cat_id] = config

    def get(self, cat_id: CatId) -> CatConfig:
        """获取猫配置，不存在抛 KeyError"""
        if cat_id not in self._cats:
            registered = list(self._cats.keys())
            raise KeyError(f"Cat not found: {cat_id}. Registered: {registered}")
        return self._cats[cat_id]

    def try_get(self, cat_id: CatId) -> Optional[CatConfig]:
        """安全获取"""
        return self._cats.get(cat_id)

    def has(self, cat_id: CatId) -> bool:
        return cat_id in self._cats

    def get_all_ids(self) -> List[CatId]:
        return list(self._cats.keys())

    def get_all_configs(self) -> Dict[CatId, CatConfig]:
        return dict(self._cats)

    def get_by_mention(self, mention: str) -> Optional[CatConfig]:
        """通过 @mention 查找猫（不区分大小写）"""
        key = mention.lower().lstrip("@")
        cat_id = self._mention_index.get(key)
        if cat_id:
            return self._cats[cat_id]
        # 也尝试带 @ 的原始形式
        cat_id = self._mention_index.get(mention.lower())
        if cat_id:
            return self._cats[cat_id]
        return None

    def set_default(self, cat_id: CatId) -> None:
        self._default_id = cat_id

    def get_default_id(self) -> Optional[CatId]:
        return self._default_id

    def reset(self) -> None:
        self._cats.clear()
        self._mention_index.clear()
        self._default_id = None


# 全局单例
cat_registry = CatRegistry()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_cat_registry.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/models/cat_registry.py tests/models/test_cat_registry.py
git commit -m "feat: add CatRegistry — global config registry from breeds/variants"
```

---

### Task 3: AgentRegistry — 服务实例注册表

**Files:**
- Create: `src/models/agent_registry.py`
- Test: `tests/models/test_agent_registry.py`

- [ ] **Step 1: 写测试**

```python
# tests/models/test_agent_registry.py
import pytest
from src.models.agent_registry import AgentRegistry
from unittest.mock import AsyncMock


class FakeAgentService:
    """测试用的 fake service"""
    def __init__(self, cat_id: str):
        self.cat_id = cat_id
    async def invoke(self, prompt, options=None):
        yield f"response from {self.cat_id}"


class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        service = FakeAgentService("opus")
        reg.register("opus", service)

        assert reg.get("opus") is service

    def test_register_duplicate_raises(self):
        reg = AgentRegistry()
        reg.register("opus", FakeAgentService("opus"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register("opus", FakeAgentService("opus"))

    def test_get_not_found_raises(self):
        reg = AgentRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_has(self):
        reg = AgentRegistry()
        assert reg.has("opus") is False
        reg.register("opus", FakeAgentService("opus"))
        assert reg.has("opus") is True

    def test_get_all_entries(self):
        reg = AgentRegistry()
        s1 = FakeAgentService("opus")
        s2 = FakeAgentService("sonnet")
        reg.register("opus", s1)
        reg.register("sonnet", s2)

        entries = reg.get_all_entries()
        assert entries["opus"] is s1
        assert entries["sonnet"] is s2

    def test_reset(self):
        reg = AgentRegistry()
        reg.register("opus", FakeAgentService("opus"))
        reg.reset()
        assert reg.has("opus") is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_agent_registry.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/models/agent_registry.py
from typing import Dict, Any
from src.models.types import CatId


class AgentRegistry:
    """Agent 服务实例注册表 — catId -> AgentService"""

    def __init__(self):
        self._services: Dict[CatId, Any] = {}

    def register(self, cat_id: CatId, service: Any) -> None:
        if cat_id in self._services:
            raise ValueError(f"Cat already registered: {cat_id}")
        self._services[cat_id] = service

    def get(self, cat_id: CatId) -> Any:
        if cat_id not in self._services:
            raise KeyError(f"Agent not registered: {cat_id}")
        return self._services[cat_id]

    def has(self, cat_id: CatId) -> bool:
        return cat_id in self._services

    def get_all_entries(self) -> Dict[CatId, Any]:
        return dict(self._services)

    def reset(self) -> None:
        self._services.clear()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_agent_registry.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/models/agent_registry.py tests/models/test_agent_registry.py
git commit -m "feat: add AgentRegistry — service instance registry"
```

---

### Task 4: CLI Spawn — 流式 NDJSON 进程管理

**Files:**
- Create: `src/utils/cli_spawn.py`
- Create: `src/utils/ndjson_stream.py`
- Test: `tests/utils/test_cli_spawn.py`
- Test: `tests/utils/test_ndjson_stream.py`

**Context:** 替代现有 `src/utils/process.py`（保留向后兼容），新增真正的流式 NDJSON 解析 + 进程生命周期管理（超时、SIGTERM→SIGKILL、僵尸防护）。

- [ ] **Step 1: 写 ndjson_stream 测试**

```python
# tests/utils/test_ndjson_stream.py
import pytest
import asyncio
from src.utils.ndjson_stream import parse_ndjson_lines


@pytest.mark.asyncio
async def test_parse_valid_ndjson():
    lines = ['{"type":"text","content":"hello"}', '{"type":"done"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 2
    assert events[0]["content"] == "hello"
    assert events[1]["type"] == "done"


@pytest.mark.asyncio
async def test_parse_skips_empty_lines():
    lines = ['', '{"type":"text"}', '  ', '{"type":"done"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 2


@pytest.mark.asyncio
async def test_parse_handles_invalid_json():
    lines = ['not json', '{"type":"ok"}']
    events = []
    async for event in parse_ndjson_lines(lines):
        events.append(event)
    assert len(events) == 1
    assert events[0]["type"] == "ok"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/utils/test_ndjson_stream.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 ndjson_stream**

```python
# src/utils/ndjson_stream.py
import json
from typing import AsyncIterator, Dict, Any, Iterable


async def parse_ndjson_lines(lines: Iterable[str]) -> AsyncIterator[Dict[str, Any]]:
    """流式解析 NDJSON 行（来自 CLI stdout）

    Args:
        lines: 可迭代的字符串行

    Yields:
        解析后的 JSON 对象
    """
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
            yield event
        except json.JSONDecodeError:
            continue
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/utils/test_ndjson_stream.py -v`
Expected: PASS

- [ ] **Step 5: 写 cli_spawn 测试**

```python
# tests/utils/test_cli_spawn.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.utils.cli_spawn import spawn_cli


@pytest.mark.asyncio
async def test_spawn_cli_basic():
    """测试基本 CLI 调用"""
    # 用 echo 模拟 CLI 输出
    events = []
    async for event in spawn_cli("echo", ['{"type":"text","content":"hello"}']):
        events.append(event)
    # echo 输出的是纯文本不是 JSON，所以会被跳过
    # 这个测试主要验证 spawn 不会崩溃


@pytest.mark.asyncio
async def test_spawn_cli_timeout():
    """测试超时 kill"""
    with pytest.raises(asyncio.TimeoutError):
        async for event in spawn_cli("sleep", ["10"], timeout=0.5):
            pass
```

- [ ] **Step 6: 运行测试确认失败**

Run: `pytest tests/utils/test_cli_spawn.py -v`
Expected: FAIL

- [ ] **Step 7: 实现 cli_spawn**

```python
# src/utils/cli_spawn.py
import asyncio
import os
from typing import AsyncIterator, Dict, Any, List, Optional
from src.utils.ndjson_stream import parse_ndjson_lines


KILL_GRACE_MS = 3.0  # SIGTERM -> SIGKILL 等待时间


async def spawn_cli(
    command: str,
    args: List[str],
    timeout: float = 300.0,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> AsyncIterator[Dict[str, Any]]:
    """spawn CLI 子进程，流式解析 NDJSON 输出

    功能：
    - 真正的流式读取（逐行 yield，不等进程结束）
    - 超时管理（SIGTERM → SIGKILL 升级）
    - 僵尸进程防护

    Args:
        command: CLI 命令
        args: 参数列表
        timeout: 超时时间（秒）
        env: 子进程环境变量（None 则继承当前）
        cwd: 工作目录

    Yields:
        解析后的 NDJSON 事件
    """
    cmd = [command] + args
    child_env = dict(os.environ)
    if env:
        # 合并环境变量，None 值表示删除
        for k, v in env.items():
            if v is None:
                child_env.pop(k, None)
            else:
                child_env[k] = v

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=child_env,
        cwd=cwd,
    )

    # 僵尸防护：进程退出时确保 kill
    child_exited = False

    def _cleanup_on_exit():
        if not child_exited and process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass

    # 收集行数据
    buffer = []

    try:
        async with asyncio.timeout(timeout):
            async for line in process.stdout:
                decoded = line.decode("utf-8", errors="replace")
                buffer.append(decoded)
                stripped = decoded.strip()
                if not stripped:
                    continue
                try:
                    import json
                    event = json.loads(stripped)
                    yield event
                except json.JSONDecodeError:
                    continue

        # 等待进程退出
        await process.wait()

    except asyncio.TimeoutError:
        # SIGTERM
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=KILL_GRACE_MS)
        except asyncio.TimeoutError:
            # SIGKILL
            process.kill()
            await process.wait()
        raise
    finally:
        child_exited = True
```

- [ ] **Step 8: 运行测试确认通过**

Run: `pytest tests/utils/test_cli_spawn.py -v`
Expected: PASS

- [ ] **Step 9: 提交**

```bash
git add src/utils/cli_spawn.py src/utils/ndjson_stream.py tests/utils/
git commit -m "feat: add streaming CLI spawn with NDJSON parsing and lifecycle management"
```

---

### Task 5: Provider 基类与 Claude 适配器

**Files:**
- Create: `src/providers/__init__.py`
- Create: `src/providers/base.py`
- Create: `src/providers/claude_provider.py`
- Test: `tests/providers/test_claude_provider.py`

**Context:** 所有 Provider 继承 `BaseProvider`，统一 `invoke()` 接口。Claude 适配器 spawn `claude` CLI。

- [ ] **Step 1: 写测试**

```python
# tests/providers/test_claude_provider.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from src.providers.claude_provider import ClaudeProvider
from src.models.types import CatConfig, ContextBudget, InvocationOptions, AgentMessage, AgentMessageType


@pytest.fixture
def opus_config():
    return CatConfig(
        cat_id="opus",
        breed_id="ragdoll",
        name="布偶猫",
        display_name="宪宪",
        provider="anthropic",
        default_model="claude-opus-4-6",
        personality="温柔但有主见",
        cli_command="claude",
        cli_args=["--output-format", "stream-json"],
        budget=ContextBudget(max_prompt_tokens=180000, max_context_tokens=160000),
    )


def test_build_system_prompt(opus_config):
    provider = ClaudeProvider(opus_config)
    prompt = provider.build_system_prompt()
    assert "布偶猫" in prompt
    assert "温柔但有主见" in prompt


def test_build_cli_args_basic(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("你好", InvocationOptions())
    assert "--output-format" in args
    assert "stream-json" in args
    assert "你好" in args


def test_build_cli_args_with_system_prompt(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("你好", InvocationOptions(system_prompt="你是架构师"))
    assert "--append-system-prompt" in args
    assert "你是架构师" in args


def test_build_cli_args_with_session_id(opus_config):
    provider = ClaudeProvider(opus_config)
    args = provider._build_args("继续", InvocationOptions(session_id="abc123"))
    assert "--resume" in args
    assert "abc123" in args


def test_transform_event_text():
    provider = ClaudeProvider(opus_config)
    event = {
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": "hello"}]
        }
    }
    msgs = provider._transform_event(event)
    assert len(msgs) == 1
    assert msgs[0].type == AgentMessageType.TEXT
    assert msgs[0].content == "hello"


def test_transform_event_usage():
    provider = ClaudeProvider(opus_config)
    event = {
        "type": "assistant",
        "message": {
            "usage": {"input_tokens": 100, "output_tokens": 50}
        }
    }
    msgs = provider._transform_event(event)
    assert len(msgs) == 1
    assert msgs[0].type == AgentMessageType.USAGE
    assert msgs[0].usage.input_tokens == 100


def test_transform_event_done():
    provider = ClaudeProvider(opus_config)
    event = {"type": "result", "subtype": "success"}
    msgs = provider._transform_event(event)
    assert len(msgs) == 1
    assert msgs[0].type == AgentMessageType.DONE
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/providers/test_claude_provider.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 base + claude provider**

```python
# src/providers/__init__.py
from src.providers.base import BaseProvider
from src.providers.claude_provider import ClaudeProvider

PROVIDER_MAP = {
    "anthropic": ClaudeProvider,
    # 后续 Task 中添加：
    # "openai": CodexProvider,
    # "google": GeminiProvider,
    # "opencode": OpenCodeProvider,
}


def create_provider(config) -> BaseProvider:
    """工厂方法：根据 provider 类型创建适配器"""
    provider_cls = PROVIDER_MAP.get(config.provider)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {config.provider}")
    return provider_cls(config)
```

```python
# src/providers/base.py
import tempfile
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions, AgentMessageType
)


class BaseProvider(ABC):
    """所有 Provider 的基类"""

    def __init__(self, config: CatConfig):
        self.config = config
        self.cat_id = config.cat_id
        self.name = config.display_name

    def build_system_prompt(self) -> str:
        """从配置构建系统提示"""
        parts = [f"你是{self.config.name}。"]
        if self.config.personality:
            parts.append(f"性格：{self.config.personality}")
        if self.config.role_description:
            parts.append(f"角色：{self.config.role_description}")
        return "\n".join(parts)

    @abstractmethod
    async def invoke(
        self,
        prompt: str,
        options: InvocationOptions = None,
    ) -> AsyncIterator[AgentMessage]:
        """统一的流式调用接口

        Args:
            prompt: 用户消息
            options: 调用选项（系统提示、session_id、超时等）

        Yields:
            AgentMessage（text/thinking/usage/done/error）
        """
        pass

    @abstractmethod
    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        """构建 CLI 参数"""
        pass

    @abstractmethod
    def _transform_event(self, event: dict) -> list[AgentMessage]:
        """将 CLI NDJSON 事件转换为 AgentMessage 列表"""
        pass
```

```python
# src/providers/claude_provider.py
import os
import tempfile
from typing import AsyncIterator, List

from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions,
    AgentMessageType, TokenUsage
)
from src.utils.cli_spawn import spawn_cli


class ClaudeProvider(BaseProvider):
    """Claude CLI 适配器 — spawn `claude` 命令，解析 stream-json 输出"""

    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = list(self.config.cli_args)  # 默认参数

        # 系统提示
        if options and options.system_prompt:
            args.extend(["--append-system-prompt", options.system_prompt])

        # 会话恢复
        if options and options.session_id:
            args.extend(["--resume", options.session_id])

        # effort 级别
        if options and options.effort:
            args.extend(["--effort", options.effort])

        # 额外参数
        if options and options.extra_args:
            args.extend(options.extra_args)

        # 用户消息放最后
        args.append(prompt)
        return args

    async def invoke(
        self,
        prompt: str,
        options: InvocationOptions = None,
    ) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()

        args = self._build_args(prompt, options)
        timeout = options.timeout or 300.0

        # 构建环境变量
        env = {}
        if options.system_prompt is None:
            # 如果没有传系统提示，用默认的
            pass

        try:
            async for event in spawn_cli(
                self.config.cli_command,
                args,
                timeout=timeout,
                env=env or None,
            ):
                messages = self._transform_event(event)
                for msg in messages:
                    yield msg
        except Exception as e:
            yield AgentMessage(
                type=AgentMessageType.ERROR,
                content=str(e),
                cat_id=self.cat_id,
            )
        finally:
            yield AgentMessage(
                type=AgentMessageType.DONE,
                cat_id=self.cat_id,
            )

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        """将 Claude CLI stream-json 事件转换为 AgentMessage"""
        event_type = event.get("type", "")
        messages = []

        if event_type == "assistant":
            msg_data = event.get("message", {})
            # 文本内容
            for block in msg_data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        messages.append(AgentMessage(
                            type=AgentMessageType.TEXT,
                            content=text,
                            cat_id=self.cat_id,
                        ))
                elif isinstance(block, dict) and block.get("type") == "thinking":
                    text = block.get("text", "")
                    if text:
                        messages.append(AgentMessage(
                            type=AgentMessageType.THINKING,
                            content=text,
                            cat_id=self.cat_id,
                        ))

            # Token 用量
            usage_data = msg_data.get("usage")
            if usage_data:
                messages.append(AgentMessage(
                    type=AgentMessageType.USAGE,
                    usage=TokenUsage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
                        cache_creation_tokens=usage_data.get("cache_creation_input_tokens", 0),
                    ),
                    cat_id=self.cat_id,
                ))

        elif event_type == "result":
            subtype = event.get("subtype", "")
            if subtype == "success":
                messages.append(AgentMessage(
                    type=AgentMessageType.DONE,
                    cat_id=self.cat_id,
                ))
            # result 事件可能也有 session_id
            session_id = event.get("session_id")
            if session_id:
                for msg in messages:
                    msg.session_id = session_id

        return messages
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/providers/test_claude_provider.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/providers/ tests/providers/
git commit -m "feat: add BaseProvider and ClaudeProvider adapter"
```

---

### Task 6: Codex / Gemini / OpenCode 适配器

**Files:**
- Create: `src/providers/codex_provider.py`
- Create: `src/providers/gemini_provider.py`
- Create: `src/providers/opencode_provider.py`
- Modify: `src/providers/__init__.py`
- Test: `tests/providers/test_providers.py`

- [ ] **Step 1: 写测试**

```python
# tests/providers/test_providers.py
import pytest
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.opencode_provider import OpenCodeProvider
from src.providers import create_provider
from src.models.types import CatConfig, ContextBudget, InvocationOptions


@pytest.fixture
def codex_config():
    return CatConfig(
        cat_id="codex", breed_id="maine-coon",
        name="缅因猫", display_name="砚砚",
        provider="openai", default_model="gpt-5.3-codex",
        personality="严谨认真",
        cli_command="codex", cli_args=["exec", "--json"],
    )


@pytest.fixture
def gemini_config():
    return CatConfig(
        cat_id="gemini", breed_id="siamese",
        name="暹罗猫", display_name="烁烁",
        provider="google", default_model="gemini-3.1-pro-preview",
        personality="热血奔放",
        cli_command="gemini", cli_args=[],
    )


@pytest.fixture
def opencode_config():
    return CatConfig(
        cat_id="opencode", breed_id="golden-chinchilla",
        name="金渐层", display_name="金渐层",
        provider="opencode", default_model="anthropic/claude-opus-4-6",
        personality="沉稳可靠",
        cli_command="opencode", cli_args=["run", "--format", "json"],
    )


class TestCodexProvider:
    def test_build_args(self, codex_config):
        provider = CodexProvider(codex_config)
        args = provider._build_args("write tests", InvocationOptions(system_prompt="你是审查员"))
        assert "exec" in args
        assert "write tests" in args

    def test_transform_text_event(self, codex_config):
        provider = CodexProvider(codex_config)
        event = {"type": "message", "content": [{"type": "text", "text": "done"}]}
        msgs = provider._transform_event(event)
        assert len(msgs) == 1
        assert msgs[0].content == "done"


class TestGeminiProvider:
    def test_build_args(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        args = provider._build_args("设计 UI", InvocationOptions(system_prompt="你是设计师"))
        assert "设计 UI" in args

    def test_transform_text_event(self, gemini_config):
        provider = GeminiProvider(gemini_config)
        event = {"type": "text", "text": "这是一个设计"}
        msgs = provider._transform_event(event)
        assert len(msgs) == 1
        assert msgs[0].content == "这是一个设计"


class TestOpenCodeProvider:
    def test_build_args(self, opencode_config):
        provider = OpenCodeProvider(opencode_config)
        args = provider._build_args("refactor", InvocationOptions())
        assert "run" in args
        assert "refactor" in args


class TestProviderFactory:
    def test_create_claude(self):
        config = CatConfig(
            cat_id="opus", breed_id="ragdoll", name="test",
            display_name="test", provider="anthropic",
            default_model="claude-opus-4-6", cli_command="claude",
        )
        from src.providers.claude_provider import ClaudeProvider
        provider = create_provider(config)
        assert isinstance(provider, ClaudeProvider)

    def test_create_codex(self, codex_config):
        provider = create_provider(codex_config)
        assert isinstance(provider, CodexProvider)

    def test_create_gemini(self, gemini_config):
        provider = create_provider(gemini_config)
        assert isinstance(provider, GeminiProvider)

    def test_create_unknown_raises(self):
        config = CatConfig(
            cat_id="x", breed_id="x", name="x",
            display_name="x", provider="unknown",
            default_model="x", cli_command="x",
        )
        with pytest.raises(ValueError, match="Unknown provider"):
            create_provider(config)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/providers/test_providers.py -v`
Expected: FAIL

- [ ] **Step 3: 实现三个 Provider**

```python
# src/providers/codex_provider.py
from typing import AsyncIterator, List

from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions,
    AgentMessageType, TokenUsage
)
from src.utils.cli_spawn import spawn_cli


class CodexProvider(BaseProvider):
    """Codex CLI 适配器 — spawn `codex` 命令"""

    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = list(self.config.cli_args)

        if options and options.system_prompt:
            args.extend(["--instructions", options.system_prompt])

        if options and options.extra_args:
            args.extend(options.extra_args)

        args.append(prompt)
        return args

    async def invoke(
        self, prompt: str, options: InvocationOptions = None,
    ) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()

        args = self._build_args(prompt, options)

        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=options.timeout or 300.0
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id)
        finally:
            yield AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        event_type = event.get("type", "")
        messages = []

        if event_type == "message":
            for block in event.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        messages.append(AgentMessage(
                            type=AgentMessageType.TEXT, content=text, cat_id=self.cat_id,
                        ))
        elif event_type == "result":
            messages.append(AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id))

        return messages
```

```python
# src/providers/gemini_provider.py
from typing import AsyncIterator, List

from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions,
    AgentMessageType, TokenUsage
)
from src.utils.cli_spawn import spawn_cli


class GeminiProvider(BaseProvider):
    """Gemini CLI 适配器 — spawn `gemini` 命令"""

    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = list(self.config.cli_args)

        if options and options.system_prompt:
            args.extend(["--system-instruction", options.system_prompt])

        if options and options.session_id:
            args.extend(["--resume", options.session_id])

        if options and options.extra_args:
            args.extend(options.extra_args)

        args.append(prompt)
        return args

    async def invoke(
        self, prompt: str, options: InvocationOptions = None,
    ) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()

        args = self._build_args(prompt, options)

        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=options.timeout or 300.0
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id)
        finally:
            yield AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        event_type = event.get("type", "")
        messages = []

        if event_type == "text":
            text = event.get("text", "")
            if text:
                messages.append(AgentMessage(
                    type=AgentMessageType.TEXT, content=text, cat_id=self.cat_id,
                ))
        elif event_type == "usage":
            messages.append(AgentMessage(
                type=AgentMessageType.USAGE,
                usage=TokenUsage(
                    input_tokens=event.get("input_tokens", 0),
                    output_tokens=event.get("output_tokens", 0),
                ),
                cat_id=self.cat_id,
            ))
        elif event_type in ("done", "finish"):
            messages.append(AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id))

        return messages
```

```python
# src/providers/opencode_provider.py
from typing import AsyncIterator, List

from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions,
    AgentMessageType, TokenUsage
)
from src.utils.cli_spawn import spawn_cli


class OpenCodeProvider(BaseProvider):
    """OpenCode CLI 适配器 — spawn `opencode` 命令"""

    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = list(self.config.cli_args)

        if options and options.system_prompt:
            args.extend(["--system", options.system_prompt])

        if options and options.extra_args:
            args.extend(options.extra_args)

        args.append(prompt)
        return args

    async def invoke(
        self, prompt: str, options: InvocationOptions = None,
    ) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()

        args = self._build_args(prompt, options)

        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=options.timeout or 300.0
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id)
        finally:
            yield AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        event_type = event.get("type", "")
        messages = []

        if event_type == "assistant":
            content = event.get("content", "")
            if content:
                messages.append(AgentMessage(
                    type=AgentMessageType.TEXT, content=content, cat_id=self.cat_id,
                ))
        elif event_type == "usage":
            messages.append(AgentMessage(
                type=AgentMessageType.USAGE,
                usage=TokenUsage(
                    input_tokens=event.get("input_tokens", 0),
                    output_tokens=event.get("output_tokens", 0),
                ),
                cat_id=self.cat_id,
            ))
        elif event_type == "done":
            messages.append(AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id))

        return messages
```

- [ ] **Step 4: 更新 `src/providers/__init__.py` 的 PROVIDER_MAP**

```python
# src/providers/__init__.py
from src.providers.base import BaseProvider
from src.providers.claude_provider import ClaudeProvider
from src.providers.codex_provider import CodexProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.opencode_provider import OpenCodeProvider

PROVIDER_MAP = {
    "anthropic": ClaudeProvider,
    "openai": CodexProvider,
    "google": GeminiProvider,
    "opencode": OpenCodeProvider,
}


def create_provider(config) -> BaseProvider:
    """工厂方法：根据 provider 类型创建适配器"""
    provider_cls = PROVIDER_MAP.get(config.provider)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {config.provider}")
    return provider_cls(config)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `pytest tests/providers/ -v`
Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add src/providers/ tests/providers/
git commit -m "feat: add Codex, Gemini, OpenCode provider adapters with factory"
```

---

### Task 7: 注册表集成 — 替换现有 cat 服务初始化

**Files:**
- Create: `src/models/registry_init.py`
- Modify: `src/web/app.py`
- Modify: `src/web/dependencies.py`
- Test: `tests/models/test_registry_init.py`

**Context:** 将 CatRegistry + AgentRegistry + Provider 工厂串起来，在 FastAPI lifespan 中初始化。

- [ ] **Step 1: 写测试**

```python
# tests/models/test_registry_init.py
import pytest
from src.models.registry_init import initialize_registries


def test_initialize_with_real_config():
    """使用真实 cat-config.json 初始化"""
    cat_reg, agent_reg = initialize_registries("cat-config.json")

    # 至少应该有 opus, sonnet, codex, gemini
    assert cat_reg.has("opus")
    assert cat_reg.has("sonnet")
    assert cat_reg.has("codex")
    assert cat_reg.has("gemini")

    # AgentRegistry 也应该有对应的服务实例
    assert agent_reg.has("opus")

    # 验证 provider 类型
    opus_service = agent_reg.get("opus")
    from src.providers.claude_provider import ClaudeProvider
    assert isinstance(opus_service, ClaudeProvider)

    # 验证 codex 用 CodexProvider
    codex_service = agent_reg.get("codex")
    from src.providers.codex_provider import CodexProvider
    assert isinstance(codex_service, CodexProvider)


def test_initialize_default_cat():
    cat_reg, _ = initialize_registries("cat-config.json")
    default_id = cat_reg.get_default_id()
    assert default_id is not None
    assert cat_reg.has(default_id)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/models/test_registry_init.py -v`
Expected: FAIL

- [ ] **Step 3: 实现注册表初始化**

```python
# src/models/registry_init.py
import json
from pathlib import Path
from typing import Tuple

from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers import create_provider


def initialize_registries(config_path: str = "cat-config.json") -> Tuple[CatRegistry, AgentRegistry]:
    """从 cat-config.json 初始化双注册表

    Returns:
        (CatRegistry, AgentRegistry) 元组
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    breeds = config.get("breeds", [])

    # 1. 加载配置注册表
    cat_reg = CatRegistry()
    cat_reg.load_from_breeds(breeds)

    # 2. 构建 Agent 服务注册表
    agent_reg = AgentRegistry()
    for cat_id in cat_reg.get_all_ids():
        cat_config = cat_reg.get(cat_id)
        try:
            provider = create_provider(cat_config)
            agent_reg.register(cat_id, provider)
        except ValueError as e:
            # 未知 provider 类型，跳过（如 dare, antigravity）
            print(f"Skipping {cat_id}: {e}")

    return cat_reg, agent_reg
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/models/test_registry_init.py -v`
Expected: PASS

- [ ] **Step 5: 更新 FastAPI app.py 使用新注册表**

```python
# src/web/app.py — 修改 lifespan 函数
# 在文件顶部添加 import:
# from src.models.registry_init import initialize_registries
# from src.models.cat_registry import cat_registry as global_cat_registry
# from src.models.agent_registry import AgentRegistry

# 替换 lifespan 中的初始化逻辑:
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    # 初始化双注册表
    try:
        cat_reg, agent_reg = initialize_registries("cat-config.json")
    except FileNotFoundError:
        cat_reg, agent_reg = CatRegistry(), AgentRegistry()

    app.state.cat_registry = cat_reg
    app.state.agent_registry = agent_reg

    # ThreadManager
    tm = ThreadManager(skip_init=True)
    await tm.async_init()
    app.state.thread_manager = tm

    # 保留旧 router 向后兼容
    app.state.agent_router = AgentRouter()

    yield

    if hasattr(tm, '_store') and tm._store:
        await tm._store.close()
```

- [ ] **Step 6: 更新 dependencies.py**

```python
# src/web/dependencies.py — 添加新依赖
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry


def get_cat_registry(request: Request) -> CatRegistry:
    return request.app.state.cat_registry


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry
```

- [ ] **Step 7: 运行全部测试**

Run: `pytest tests/ -v --ignore=tests/integration`
Expected: ALL PASS（确保没有破坏现有功能）

- [ ] **Step 8: 提交**

```bash
git add src/models/registry_init.py src/web/app.py src/web/dependencies.py tests/models/test_registry_init.py
git commit -m "feat: integrate CatRegistry + AgentRegistry into FastAPI lifecycle"
```

---

## 子阶段 6.2: 配置系统

### Task 8: Context Budget 管理

**Files:**
- Create: `src/config/budgets.py`
- Test: `tests/config/test_budgets.py`

- [ ] **Step 1: 写测试**

```python
# tests/config/test_budgets.py
import pytest
from src.config.budgets import get_cat_budget, DEFAULT_BUDGETS, GLOBAL_FALLBACK_BUDGET
from src.models.types import ContextBudget
from src.models.cat_registry import CatRegistry


@pytest.fixture
def registry_with_budgets():
    reg = CatRegistry()
    reg.load_from_breeds([
        {
            "id": "ragdoll",
            "catId": "opus",
            "name": "布偶猫",
            "displayName": "布偶猫",
            "mentionPatterns": ["@opus"],
            "defaultVariantId": "opus-default",
            "variants": [{
                "id": "opus-default",
                "catId": "opus",
                "provider": "anthropic",
                "defaultModel": "claude-opus-4-6",
                "contextBudget": {
                    "maxPromptTokens": 180000,
                    "maxContextTokens": 160000,
                    "maxMessages": 200,
                    "maxContentLengthPerMsg": 10000,
                },
            }],
        }
    ])
    return reg


def test_get_cat_budget_from_registry(registry_with_budgets):
    budget = get_cat_budget("opus", registry_with_budgets)
    assert budget.max_prompt_tokens == 180000
    assert budget.max_context_tokens == 160000


def test_get_cat_budget_fallback():
    reg = CatRegistry()
    budget = get_cat_budget("unknown_cat", reg)
    assert budget.max_prompt_tokens == GLOBAL_FALLBACK_BUDGET.max_prompt_tokens
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/config/test_budgets.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/config/budgets.py
import os
from typing import Optional

from src.models.types import ContextBudget
from src.models.cat_registry import CatRegistry


GLOBAL_FALLBACK_BUDGET = ContextBudget(
    max_prompt_tokens=100000,
    max_context_tokens=60000,
    max_messages=200,
    max_content_length_per_msg=10000,
)


def get_cat_budget(cat_id: str, registry: CatRegistry) -> ContextBudget:
    """三级解析：env > registry > fallback"""
    # Level 1: 环境变量
    env_key = f"CAT_{cat_id.upper().replace('-', '_')}_MAX_PROMPT_TOKENS"
    env_val = os.environ.get(env_key)
    if env_val:
        try:
            return ContextBudget(max_prompt_tokens=int(env_val))
        except ValueError:
            pass

    # Level 2: 注册表
    config = registry.try_get(cat_id)
    if config:
        return config.budget

    # Level 3: 全局 fallback
    return GLOBAL_FALLBACK_BUDGET
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/config/test_budgets.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/config/budgets.py tests/config/
git commit -m "feat: add context budget management with 3-tier resolution"
```

---

### Task 9: Model Resolution — 模型解析

**Files:**
- Create: `src/config/model_resolver.py`
- Create: `src/config/context_windows.py`
- Test: `tests/config/test_model_resolver.py`

- [ ] **Step 1: 写测试**

```python
# tests/config/test_model_resolver.py
import pytest
from src.config.model_resolver import get_cat_model
from src.config.context_windows import get_context_window_size
from src.models.cat_registry import CatRegistry


@pytest.fixture
def registry():
    reg = CatRegistry()
    reg.load_from_breeds([{
        "id": "ragdoll", "catId": "opus", "name": "布偶猫",
        "displayName": "布偶猫", "mentionPatterns": ["@opus"],
        "defaultVariantId": "opus-default",
        "variants": [{
            "id": "opus-default", "catId": "opus", "provider": "anthropic",
            "defaultModel": "claude-opus-4-6",
        }],
    }])
    return reg


def test_get_model_from_registry(registry):
    model = get_cat_model("opus", registry)
    assert model == "claude-opus-4-6"


def test_get_model_env_override(registry, monkeypatch):
    monkeypatch.setenv("CAT_OPUS_MODEL", "claude-sonnet-4-6")
    model = get_cat_model("opus", registry)
    assert model == "claude-sonnet-4-6"


def test_get_model_not_found_raises(registry):
    with pytest.raises(KeyError):
        get_cat_model("nonexistent", registry)


def test_context_window_exact_match():
    size = get_context_window_size("claude-opus-4-6")
    assert size == 200000


def test_context_window_prefix_match():
    size = get_context_window_size("claude-opus-4-6-20260101")
    assert size == 200000


def test_context_window_unknown():
    size = get_context_window_size("unknown-model")
    assert size is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/config/test_model_resolver.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/config/context_windows.py
from typing import Optional

# 模型上下文窗口大小表（tokens）
CONTEXT_WINDOW_SIZES: dict[str, int] = {
    # Claude family
    "claude-opus-4-6": 200000,
    "claude-opus-4-5-20251101": 200000,
    "claude-sonnet-4-6": 200000,
    "claude-sonnet-4-5-20251001": 200000,
    "claude-haiku-4-5-20251001": 200000,
    # OpenAI family
    "gpt-5.3-codex": 240000,
    "gpt-5.3-codex-spark": 128000,
    "gpt-5.4": 400000,
    # Google family
    "gemini-3.1-pro-preview": 1000000,
    "gemini-2.5-pro": 1000000,
}


def get_context_window_size(model: str) -> Optional[int]:
    """查询模型上下文窗口大小，支持前缀匹配"""
    if model in CONTEXT_WINDOW_SIZES:
        return CONTEXT_WINDOW_SIZES[model]
    # 前缀匹配（处理带日期后缀的模型名）
    for key, size in CONTEXT_WINDOW_SIZES.items():
        if model.startswith(key):
            return size
    return None
```

```python
# src/config/model_resolver.py
import os
from typing import Optional

from src.models.cat_registry import CatRegistry


def _get_env_key(cat_id: str) -> str:
    """生成环境变量名: CAT_{CATID}_MODEL"""
    return f"CAT_{cat_id.upper().replace('-', '_')}_MODEL"


def get_cat_model(cat_id: str, registry: CatRegistry) -> str:
    """三级解析：env > registry config > raise

    Args:
        cat_id: 猫 ID
        registry: 配置注册表

    Returns:
        模型名称字符串

    Raises:
        KeyError: 猫不存在
    """
    # Level 1: 环境变量
    env_val = os.environ.get(_get_env_key(cat_id))
    if env_val:
        return env_val

    # Level 2: 注册表
    config = registry.try_get(cat_id)
    if config and config.default_model:
        return config.default_model

    raise KeyError(f"No model found for cat: {cat_id}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/config/test_model_resolver.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/config/model_resolver.py src/config/context_windows.py tests/config/
git commit -m "feat: add model resolver and context window size table"
```

---

### Task 10: Account Resolver — 认证解析

**Files:**
- Create: `src/config/account_resolver.py`
- Test: `tests/config/test_account_resolver.py`

**Context:** 区分 subscription（CLI OAuth）和 api_key 模式，构建子进程环境变量。

- [ ] **Step 1: 写测试**

```python
# tests/config/test_account_resolver.py
import pytest
from src.config.account_resolver import (
    resolve_runtime_env, AuthMode
)


def test_subscription_mode_strips_api_keys():
    """subscription 模式应该清除 API key 环境变量"""
    base_env = {
        "ANTHROPIC_API_KEY": "sk-xxx",
        "ANTHROPIC_BASE_URL": "https://api.example.com",
        "PATH": "/usr/bin",
    }
    result = resolve_runtime_env("anthropic", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("ANTHROPIC_API_KEY") is None
    assert result.get("ANTHROPIC_BASE_URL") is None
    assert result["PATH"] == "/usr/bin"


def test_api_key_mode_preserves_key():
    """api_key 模式保留 API key"""
    base_env = {"PATH": "/usr/bin"}
    result = resolve_runtime_env(
        "anthropic", AuthMode.API_KEY, base_env,
        api_key="sk-test", base_url="https://proxy.example.com"
    )
    assert result["ANTHROPIC_API_KEY"] == "sk-test"
    assert result["ANTHROPIC_BASE_URL"] == "https://proxy.example.com"


def test_openai_subscription_strips_keys():
    base_env = {
        "OPENAI_API_KEY": "sk-xxx",
        "PATH": "/usr/bin",
    }
    result = resolve_runtime_env("openai", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("OPENAI_API_KEY") is None


def test_google_subscription_strips_keys():
    base_env = {"GOOGLE_API_KEY": "xxx", "PATH": "/usr/bin"}
    result = resolve_runtime_env("google", AuthMode.SUBSCRIPTION, base_env)
    assert result.get("GOOGLE_API_KEY") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/config/test_account_resolver.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/config/account_resolver.py
import os
from enum import Enum
from typing import Dict, Optional


class AuthMode(str, Enum):
    SUBSCRIPTION = "subscription"
    API_KEY = "api_key"


# 每个 provider 在 subscription 模式下需要清除的环境变量
SUBSCRIPTION_STRIP_KEYS = {
    "anthropic": [
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
    ],
    "openai": [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_ORG_ID",
    ],
    "google": [
        "GOOGLE_API_KEY",
        "GOOGLE_GENAI_API_KEY",
    ],
    "opencode": [],
    "dare": [],
    "antigravity": [],
}

# api_key 模式下的环境变量映射
API_KEY_ENV_MAP = {
    "anthropic": {"key": "ANTHROPIC_API_KEY", "url": "ANTHROPIC_BASE_URL"},
    "openai": {"key": "OPENAI_API_KEY", "url": "OPENAI_BASE_URL"},
    "google": {"key": "GOOGLE_API_KEY", "url": None},
    "opencode": {"key": "OPENAI_API_KEY", "url": "OPENAI_BASE_URL"},
}


def resolve_runtime_env(
    provider: str,
    auth_mode: AuthMode,
    base_env: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, str]:
    """解析运行时环境变量

    Args:
        provider: 提供商类型
        auth_mode: 认证模式
        base_env: 基础环境变量（None 则用 os.environ）
        api_key: API Key（api_key 模式）
        base_url: 自定义 base URL（api_key 模式）

    Returns:
        清理后的环境变量字典
    """
    env = dict(base_env or os.environ)

    if auth_mode == AuthMode.SUBSCRIPTION:
        # subscription 模式：清除 API key，让 CLI 用自己的 OAuth
        strip_keys = SUBSCRIPTION_STRIP_KEYS.get(provider, [])
        for key in strip_keys:
            env[key] = None  # 会在 cli_spawn 中被删除

    elif auth_mode == AuthMode.API_KEY:
        env_map = API_KEY_ENV_MAP.get(provider, {})
        if api_key and "key" in env_map:
            env[env_map["key"]] = api_key
        if base_url and "url" in env_map and env_map["url"]:
            env[env_map["url"]] = base_url

    return env
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/config/test_account_resolver.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/config/account_resolver.py tests/config/test_account_resolver.py
git commit -m "feat: add account resolver for subscription/api_key auth modes"
```

---

## 子阶段 6.3: 高级路由

### Task 11: AgentRouter 升级 — 长匹配 + routing policy

**Files:**
- Modify: `src/router/agent_router.py`
- Test: `tests/unit/test_agent_router_v2.py`

**Context:** 升级路由为基于 CatRegistry + AgentRegistry 的版本，支持最长 @mention 匹配、fallback 策略。

- [ ] **Step 1: 写测试**

```python
# tests/unit/test_agent_router_v2.py
import pytest
from src.router.agent_router_v2 import AgentRouterV2
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers.claude_provider import ClaudeProvider
from src.models.types import CatConfig, ContextBudget


@pytest.fixture
def setup_registries():
    cat_reg = CatRegistry()
    cat_reg.load_from_breeds([
        {
            "id": "ragdoll", "catId": "opus", "name": "布偶猫",
            "displayName": "布偶猫", "mentionPatterns": ["@opus", "@布偶猫", "@宪宪"],
            "defaultVariantId": "opus-default",
            "variants": [{
                "id": "opus-default", "catId": "opus", "provider": "anthropic",
                "defaultModel": "claude-opus-4-6", "personality": "温柔",
                "cli": {"command": "claude", "defaultArgs": []},
            }],
        },
        {
            "id": "maine-coon", "catId": "codex", "name": "缅因猫",
            "displayName": "缅因猫", "mentionPatterns": ["@codex", "@缅因猫", "@砚砚"],
            "defaultVariantId": "codex-default",
            "variants": [{
                "id": "codex-default", "catId": "codex", "provider": "openai",
                "defaultModel": "gpt-5.3-codex", "personality": "严谨",
                "cli": {"command": "codex", "defaultArgs": []},
            }],
        },
    ])
    cat_reg.set_default("opus")

    agent_reg = AgentRegistry()
    for cid in cat_reg.get_all_ids():
        config = cat_reg.get(cid)
        try:
            from src.providers import create_provider
            agent_reg.register(cid, create_provider(config))
        except ValueError:
            pass

    return cat_reg, agent_reg


class TestAgentRouterV2:
    def test_parse_single_mention(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        targets = router.resolve_targets("@opus 帮我写代码")
        assert len(targets) == 1
        assert targets[0] == "opus"

    def test_parse_multiple_mentions(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        targets = router.resolve_targets("@opus @codex review this")
        assert len(targets) == 2
        assert "opus" in targets
        assert "codex" in targets

    def test_parse_chinese_mention(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        targets = router.resolve_targets("@布偶猫 写代码")
        assert targets == ["opus"]

    def test_no_mention_falls_to_default(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        targets = router.resolve_targets("随便聊聊")
        assert targets == ["opus"]

    def test_unknown_mention_falls_to_default(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        targets = router.resolve_targets("@nonexistent 写代码")
        assert targets == ["opus"]

    def test_get_service(self, setup_registries):
        cat_reg, agent_reg = setup_registries
        router = AgentRouterV2(cat_reg, agent_reg)
        service = router.get_service("opus")
        assert isinstance(service, ClaudeProvider)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/unit/test_agent_router_v2.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 AgentRouterV2**

```python
# src/router/agent_router_v2.py
import re
from typing import List, Optional

from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.models.types import CatId


class AgentRouterV2:
    """升级版路由器 — 基于 CatRegistry + AgentRegistry"""

    def __init__(self, cat_registry: CatRegistry, agent_registry: AgentRegistry):
        self.cat_registry = cat_registry
        self.agent_registry = agent_registry
        self._mention_pattern = re.compile(r'@[\w\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff-]+')

    def parse_mentions(self, message: str) -> List[str]:
        """解析 @mention，去重，保持顺序"""
        raw = self._mention_pattern.findall(message)
        seen = set()
        result = []
        for m in raw:
            key = m[1:].lower()  # 去掉 @
            if key not in seen:
                seen.add(key)
                result.append(m)
        return result

    def resolve_targets(self, message: str) -> List[CatId]:
        """解析消息中的目标猫

        优先级：
        1. @mention 精确匹配
        2. 无 mention → 默认猫
        """
        mentions = self.parse_mentions(message)
        targets = []
        seen = set()

        for mention in mentions:
            config = self.cat_registry.get_by_mention(mention)
            if config and config.cat_id not in seen:
                targets.append(config.cat_id)
                seen.add(config.cat_id)

        if not targets:
            default_id = self.cat_registry.get_default_id()
            if default_id:
                targets.append(default_id)

        return targets

    def get_service(self, cat_id: CatId):
        """获取 Agent 服务实例"""
        return self.agent_registry.get(cat_id)

    def route_message(self, message: str) -> List[dict]:
        """兼容旧接口：返回 [{cat_id, name, service}]"""
        targets = self.resolve_targets(message)
        results = []
        for cat_id in targets:
            config = self.cat_registry.get(cat_id)
            service = self.agent_registry.get(cat_id)
            results.append({
                "breed_id": cat_id,
                "name": config.display_name,
                "service": service,
            })
        return results
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/unit/test_agent_router_v2.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/router/agent_router_v2.py tests/unit/test_agent_router_v2.py
git commit -m "feat: add AgentRouterV2 with registry-based routing and fallback"
```

---

## 子阶段 6.4: 会话管理

### Task 12: Session Chain — 会话链管理

**Files:**
- Create: `src/session/__init__.py`
- Create: `src/session/chain.py`
- Test: `tests/session/test_chain.py`

- [ ] **Step 1: 写测试**

```python
# tests/session/test_chain.py
import pytest
from src.session.chain import SessionChain, SessionRecord, SessionStatus


class TestSessionChain:
    def test_create_chain(self):
        chain = SessionChain()
        record = chain.create("opus", "thread-1", "session-abc")
        assert record.cat_id == "opus"
        assert record.session_id == "session-abc"
        assert record.status == SessionStatus.ACTIVE

    def test_get_active(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-abc")
        active = chain.get_active("opus", "thread-1")
        assert active is not None
        assert active.session_id == "session-abc"

    def test_seal_session(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-abc")
        chain.seal("opus", "thread-1")
        active = chain.get_active("opus", "thread-1")
        assert active is None

    def test_create_after_seal(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-old")
        chain.seal("opus", "thread-1")
        chain.create("opus", "thread-1", "session-new")
        active = chain.get_active("opus", "thread-1")
        assert active.session_id == "session-new"

    def test_consecutive_failures_triggers_seal(self):
        chain = SessionChain()
        record = chain.create("opus", "thread-1", "session-abc")
        record.consecutive_restore_failures = 3
        assert chain.should_auto_seal("opus", "thread-1") is True

    def test_no_chain_returns_none(self):
        chain = SessionChain()
        assert chain.get_active("opus", "thread-1") is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/session/test_chain.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/session/__init__.py
from src.session.chain import SessionChain, SessionRecord
```

```python
# src/session/chain.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SessionStatus(str, Enum):
    ACTIVE = "active"
    SEALED = "sealed"


@dataclass
class SessionRecord:
    cat_id: str
    thread_id: str
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    consecutive_restore_failures: int = 0


class SessionChain:
    """会话链管理 — 跟踪每个 (cat_id, thread_id) 的 CLI 会话"""

    MAX_RESTORE_FAILURES = 3

    def __init__(self):
        self._chains: Dict[Tuple[str, str], List[SessionRecord]] = {}

    def create(self, cat_id: str, thread_id: str, session_id: str) -> SessionRecord:
        """创建新的会话记录"""
        key = (cat_id, thread_id)
        if key not in self._chains:
            self._chains[key] = []

        record = SessionRecord(
            cat_id=cat_id,
            thread_id=thread_id,
            session_id=session_id,
        )
        self._chains[key].append(record)
        return record

    def get_active(self, cat_id: str, thread_id: str) -> Optional[SessionRecord]:
        """获取当前活跃的会话记录"""
        key = (cat_id, thread_id)
        records = self._chains.get(key, [])
        for record in reversed(records):
            if record.status == SessionStatus.ACTIVE:
                return record
        return None

    def seal(self, cat_id: str, thread_id: str) -> None:
        """封存当前活跃会话"""
        active = self.get_active(cat_id, thread_id)
        if active:
            active.status = SessionStatus.SEALED

    def should_auto_seal(self, cat_id: str, thread_id: str) -> bool:
        """检查是否应该自动封存（连续失败次数）"""
        active = self.get_active(cat_id, thread_id)
        if active and active.consecutive_restore_failures >= self.MAX_RESTORE_FAILURES:
            return True
        return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/session/test_chain.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/session/ tests/session/
git commit -m "feat: add session chain management for CLI session continuity"
```

---

### Task 13: Stream Merge — 并行流合并

**Files:**
- Create: `src/invocation/__init__.py`
- Create: `src/invocation/stream_merge.py`
- Test: `tests/invocation/test_stream_merge.py`

- [ ] **Step 1: 写测试**

```python
# tests/invocation/test_stream_merge.py
import pytest
import asyncio
from src.invocation.stream_merge import merge_streams
from src.models.types import AgentMessage, AgentMessageType


async def _make_stream(messages):
    async def gen():
        for m in messages:
            yield m
    return gen()


@pytest.mark.asyncio
async def test_merge_two_streams():
    s1 = _make_stream([
        AgentMessage(type=AgentMessageType.TEXT, content="a1", cat_id="opus"),
        AgentMessage(type=AgentMessageType.DONE, cat_id="opus"),
    ])
    s2 = _make_stream([
        AgentMessage(type=AgentMessageType.TEXT, content="b1", cat_id="codex"),
        AgentMessage(type=AgentMessageType.DONE, cat_id="codex"),
    ])

    results = []
    async for msg in merge_streams([s1, s2]):
        results.append(msg)

    # 应该有 4 条消息（2 text + 2 done）
    assert len(results) == 4
    cat_ids = {m.cat_id for m in results}
    assert cat_ids == {"opus", "codex"}


@pytest.mark.asyncio
async def test_merge_single_stream():
    s1 = _make_stream([
        AgentMessage(type=AgentMessageType.TEXT, content="only", cat_id="opus"),
    ])
    results = []
    async for msg in merge_streams([s1]):
        results.append(msg)
    assert len(results) == 1
    assert results[0].content == "only"


@pytest.mark.asyncio
async def test_merge_handles_error():
    async def failing_gen():
        yield AgentMessage(type=AgentMessageType.TEXT, content="before", cat_id="opus")
        raise RuntimeError("boom")

    errors = []
    results = []
    async for msg in merge_streams([failing_gen()], on_error=lambda e: errors.append(e)):
        results.append(msg)
    assert len(results) >= 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/invocation/test_stream_merge.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/invocation/__init__.py
from src.invocation.stream_merge import merge_streams
```

```python
# src/invocation/stream_merge.py
import asyncio
from typing import AsyncIterator, Callable, List, Optional

from src.models.types import AgentMessage


async def merge_streams(
    streams: List[AsyncIterator[AgentMessage]],
    on_error: Optional[Callable[[Exception], None]] = None,
) -> AsyncIterator[AgentMessage]:
    """合并多个异步流 — 先到先 yield

    使用 asyncio.Task 池，每个流的 __anext__ 包装为 Task，
    用 asyncio.wait 按 FIRST_COMPLETED 方式收集。

    Args:
        streams: 异步迭代器列表
        on_error: 错误回调

    Yields:
        AgentMessage
    """
    if len(streams) == 1:
        async for msg in streams[0]:
            yield msg
        return

    # 每个流的 task
    tasks: dict[asyncio.Task, int] = {}  # task -> stream index

    async def _next_item(idx: int):
        return await streams[idx].__anext__()

    # 初始化：为每个流创建第一个 task
    for i, stream in enumerate(streams):
        task = asyncio.create_task(_next_item(i))
        tasks[task] = i

    while tasks:
        done, _ = await asyncio.wait(
            tasks.keys(), return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            idx = tasks.pop(task)
            try:
                msg = task.result()
                yield msg
                # 重新注册这个流
                new_task = asyncio.create_task(_next_item(idx))
                tasks[new_task] = idx
            except StopAsyncIteration:
                # 流结束，不再注册
                pass
            except Exception as e:
                if on_error:
                    on_error(e)
                # 流出错，不再注册
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/invocation/test_stream_merge.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/invocation/ tests/invocation/
git commit -m "feat: add async stream merge for parallel agent responses"
```

---

### Task 14: InvocationTracker — 调用追踪

**Files:**
- Create: `src/invocation/tracker.py`
- Test: `tests/invocation/test_tracker.py`

- [ ] **Step 1: 写测试**

```python
# tests/invocation/test_tracker.py
import pytest
from src.invocation.tracker import InvocationTracker


class TestInvocationTracker:
    def test_start(self):
        tracker = InvocationTracker()
        controller = tracker.start("thread-1", "opus")
        assert controller is not None
        assert tracker.is_active("thread-1", "opus")

    def test_start_replaces_existing(self):
        tracker = InvocationTracker()
        old = tracker.start("thread-1", "opus")
        new = tracker.start("thread-1", "opus")
        assert old.is_cancelled()
        assert tracker.is_active("thread-1", "opus")

    def test_complete(self):
        tracker = InvocationTracker()
        ctrl = tracker.start("thread-1", "opus")
        tracker.complete("thread-1", "opus", ctrl)
        assert not tracker.is_active("thread-1", "opus")

    def test_cancel(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.cancel("thread-1", "opus")
        assert not tracker.is_active("thread-1", "opus")

    def test_cancel_all_for_thread(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.start("thread-1", "codex")
        tracker.cancel_all("thread-1")
        assert not tracker.is_active("thread-1", "opus")
        assert not tracker.is_active("thread-1", "codex")

    def test_different_threads_independent(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.start("thread-2", "opus")
        tracker.cancel("thread-1", "opus")
        assert not tracker.is_active("thread-1", "opus")
        assert tracker.is_active("thread-2", "opus")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/invocation/test_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# src/invocation/tracker.py
import asyncio
from typing import Dict, Optional, Tuple


class _TrackedInvocation:
    """追踪的单次调用"""
    def __init__(self):
        self.controller = asyncio.Event()
        self._cancelled = False

    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self):
        self._cancelled = True
        self.controller.set()


class InvocationTracker:
    """调用追踪器 — per-thread per-cat 的活跃调用管理"""

    def __init__(self):
        self._slots: Dict[Tuple[str, str], _TrackedInvocation] = {}

    def start(self, thread_id: str, cat_id: str) -> _TrackedInvocation:
        """开始追踪，如果已有则取消旧的"""
        key = (thread_id, cat_id)
        existing = self._slots.get(key)
        if existing:
            existing.cancel()

        invocation = _TrackedInvocation()
        self._slots[key] = invocation
        return invocation

    def complete(self, thread_id: str, cat_id: str, invocation: _TrackedInvocation) -> None:
        """完成调用（仅当 invocation 匹配时清除）"""
        key = (thread_id, cat_id)
        if self._slots.get(key) is invocation:
            del self._slots[key]

    def cancel(self, thread_id: str, cat_id: str) -> None:
        """取消特定调用"""
        key = (thread_id, cat_id)
        existing = self._slots.get(key)
        if existing:
            existing.cancel()
            del self._slots[key]

    def cancel_all(self, thread_id: str) -> None:
        """取消线程下所有调用"""
        keys_to_remove = [k for k in self._slots if k[0] == thread_id]
        for key in keys_to_remove:
            self._slots[key].cancel()
            del self._slots[key]

    def is_active(self, thread_id: str, cat_id: str) -> bool:
        key = (thread_id, cat_id)
        return key in self._slots
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/invocation/test_tracker.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/invocation/tracker.py tests/invocation/test_tracker.py
git commit -m "feat: add invocation tracker for per-thread per-cat management"
```

---

## 子阶段 6.5: 企业特性

### Task 15: Anthropic Proxy — 第三方网关代理

**Files:**
- Create: `scripts/anthropic_proxy.py`
- Test: `tests/scripts/test_anthropic_proxy.py`

**Context:** HTTP 反向代理，处理第三方 API 网关兼容性问题：清理 thinking block 签名、规范化 SSE、自动重试。

- [ ] **Step 1: 写测试**

```python
# tests/scripts/test_anthropic_proxy.py
import pytest
from scripts.anthropic_proxy import (
    strip_thinking_from_history, normalize_sse_event, ProxyConfig
)


def test_strip_thinking_blocks():
    messages = [
        {
            "role": "user",
            "content": "hello"
        },
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "inner thoughts"},
                {"type": "text", "text": "response"},
            ]
        },
        {
            "role": "user",
            "content": "continue"
        },
    ]
    result = strip_thinking_from_history(messages)
    # assistant 消息应该只保留 text block
    assert len(result[1]["content"]) == 1
    assert result[1]["content"][0]["type"] == "text"


def test_normalize_sse_usage():
    event = {
        "type": "message_start",
        "message": {
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }
    }
    result = normalize_sse_event(event)
    # input_tokens 为 0 时保持原样（后续 message_delta 会修正）
    assert result is not None


def test_proxy_config_defaults():
    config = ProxyConfig()
    assert config.port == 9877
    assert config.max_retries == 3
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/scripts/test_anthropic_proxy.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# scripts/anthropic_proxy.py
"""
Anthropic API 反向代理

功能：
1. 清理 thinking block 签名（防止第三方网关签名不匹配）
2. 规范化 SSE 事件（修正 input_tokens: 0）
3. 自动重试（429/529）
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    port: int = 9877
    max_retries: int = 3
    retry_delay_base: float = 1.0  # 指数退避基数
    upstream_timeout: float = 60.0
    upstreams_file: str = "proxy-upstreams.json"


def strip_thinking_from_history(messages: List[dict]) -> List[dict]:
    """清理请求历史中的 thinking/redacted_thinking blocks

    第三方网关可能修改 thinking 内容但保留签名，导致 Invalid signature 错误。
    直接移除所有 thinking block 来避免。
    """
    result = []
    for msg in messages:
        if msg.get("role") != "assistant":
            result.append(msg)
            continue

        content = msg.get("content", [])
        if isinstance(content, list):
            filtered = [
                block for block in content
                if isinstance(block, dict) and block.get("type") not in ("thinking", "redacted_thinking")
            ]
            msg = {**msg, "content": filtered}

        result.append(msg)
    return result


def normalize_sse_event(event: dict) -> Optional[dict]:
    """规范化 SSE 事件

    修正：
    - input_tokens: 0 → 保留（message_delta 会提供真实值）
    - 非标准字段白名单过滤
    """
    if not isinstance(event, dict):
        return event

    event_type = event.get("type", "")

    if event_type == "message_start":
        message = event.get("message", {})
        usage = message.get("usage", {})
        # 记录异常值但不修改（后续 message_delta 会修正）
        if usage.get("input_tokens") == 0:
            logger.debug("message_start has input_tokens=0, will be corrected by message_delta")

    # 白名单过滤 content block 字段
    if event_type in ("content_block_start", "content_block_delta"):
        block = event.get("content_block") or event.get("delta", {})
        if isinstance(block, dict):
            allowed_fields = {"type", "text", "thinking", "signature", "index"}
            extra = set(block.keys()) - allowed_fields
            if extra:
                for key in extra:
                    block.pop(key, None)

    return event


def load_upstreams(config_path: str) -> Dict[str, str]:
    """加载上游路由配置"""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/scripts/test_anthropic_proxy.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add scripts/anthropic_proxy.py tests/scripts/
git commit -m "feat: add Anthropic proxy for third-party gateway compatibility"
```

---

### Task 16: 全量集成测试 + 文档更新

**Files:**
- Create: `tests/integration/test_phase6_registry.py`
- Modify: `docs/diary/kittens-phase6-multimodel.md`
- Modify: `docs/superpowers/ROADMAP.md`

- [ ] **Step 1: 写集成测试**

```python
# tests/integration/test_phase6_registry.py
"""Phase 6 集成测试 — 验证注册表 + Provider + 路由端到端"""
import pytest
from src.models.registry_init import initialize_registries
from src.router.agent_router_v2 import AgentRouterV2
from src.config.budgets import get_cat_budget
from src.config.model_resolver import get_cat_model
from src.config.context_windows import get_context_window_size
from src.session.chain import SessionChain
from src.invocation.tracker import InvocationTracker
from src.invocation.stream_merge import merge_streams


def test_full_registry_initialization():
    cat_reg, agent_reg = initialize_registries("cat-config.json")

    # 验证所有猫都注册了
    assert cat_reg.has("opus")
    assert cat_reg.has("sonnet")
    assert cat_reg.has("codex")
    assert cat_reg.has("gemini")

    # 验证 agent 服务
    assert agent_reg.has("opus")
    assert agent_reg.has("codex")
    assert agent_reg.has("gemini")


def test_router_end_to_end():
    cat_reg, agent_reg = initialize_registries("cat-config.json")
    router = AgentRouterV2(cat_reg, agent_reg)

    # 单猫路由
    targets = router.resolve_targets("@opus 写代码")
    assert targets == ["opus"]

    # 多猫路由
    targets = router.resolve_targets("@opus @codex review")
    assert "opus" in targets
    assert "codex" in targets

    # 服务获取
    service = router.get_service("opus")
    assert service is not None
    assert service.cat_id == "opus"


def test_budget_and_model_resolution():
    cat_reg, _ = initialize_registries("cat-config.json")

    budget = get_cat_budget("opus", cat_reg)
    assert budget.max_prompt_tokens > 0

    model = get_cat_model("opus", cat_reg)
    assert "claude" in model

    window = get_context_window_size(model)
    assert window is not None
    assert window >= 200000


def test_session_chain_lifecycle():
    chain = SessionChain()

    # 创建 → 使用 → 封存 → 新建
    r1 = chain.create("opus", "t1", "s1")
    assert chain.get_active("opus", "t1").session_id == "s1"

    chain.seal("opus", "t1")
    assert chain.get_active("opus", "t1") is None

    r2 = chain.create("opus", "t1", "s2")
    assert chain.get_active("opus", "t1").session_id == "s2"


def test_tracker_lifecycle():
    tracker = InvocationTracker()

    c1 = tracker.start("t1", "opus")
    assert tracker.is_active("t1", "opus")

    tracker.cancel("t1", "opus")
    assert not tracker.is_active("t1", "opus")
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/integration/test_phase6_registry.py -v`
Expected: ALL PASS

- [ ] **Step 3: 更新开发日记**

在 `docs/diary/kittens-phase6-multimodel.md` 末尾追加完成记录。

- [ ] **Step 4: 更新 ROADMAP**

将 Phase 6 状态从 📋 改为 ✅。

- [ ] **Step 5: 运行全量测试**

Run: `pytest tests/ -v --ignore=tests/web`
Expected: ALL PASS

- [ ] **Step 6: 提交**

```bash
git add tests/integration/test_phase6_registry.py docs/
git commit -m "feat: Phase 6 multi-model system complete with integration tests"
```

---

## 实施总结

| Task | 模块 | 预估时间 |
|------|------|----------|
| 1 | 共享类型定义 | 15 min |
| 2 | CatRegistry | 20 min |
| 3 | AgentRegistry | 10 min |
| 4 | CLI Spawn + NDJSON Stream | 30 min |
| 5 | Provider 基类 + Claude | 30 min |
| 6 | Codex / Gemini / OpenCode | 25 min |
| 7 | 注册表集成（FastAPI） | 20 min |
| 8 | Context Budget | 15 min |
| 9 | Model Resolver + Context Windows | 15 min |
| 10 | Account Resolver | 20 min |
| 11 | AgentRouter V2 | 25 min |
| 12 | Session Chain | 20 min |
| 13 | Stream Merge | 20 min |
| 14 | Invocation Tracker | 15 min |
| 15 | Anthropic Proxy | 20 min |
| 16 | 集成测试 + 文档 | 20 min |

**总计**: ~5 小时

---

## 依赖关系

```
Task 1 (types)
  ├── Task 2 (CatRegistry)
  ├── Task 3 (AgentRegistry)
  ├── Task 5 (BaseProvider + Claude)
  │     └── Task 6 (Codex/Gemini/OpenCode)
  ├── Task 8 (Budgets)
  ├── Task 9 (Model Resolver)
  ├── Task 12 (Session Chain)
  └── Task 13 (Stream Merge)

Task 4 (CLI Spawn)
  └── Task 5 (Claude uses CLI Spawn)

Task 2 + Task 3 + Task 6
  └── Task 7 (Registry Init)

Task 7
  └── Task 11 (AgentRouterV2)

Task 7
  └── Task 16 (Integration Tests)
```

**推荐执行顺序**: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16

---

## 验收标准

- [ ] CatRegistry 从 cat-config.json 正确加载所有 breeds/variants
- [ ] AgentRegistry 为每个 cat 创建正确的 Provider 实例
- [ ] 所有 4 个 Provider（Claude/Codex/Gemini/OpenCode）独立可用
- [ ] CLI Spawn 支持流式 NDJSON + 超时 + 进程清理
- [ ] Context Budget 三级解析正确
- [ ] Model Resolver 支持 env 覆盖
- [ ] Account Resolver subscription/api_key 模式正确
- [ ] AgentRouterV2 @mention 路由 + fallback 正确
- [ ] Session Chain 创建/封存/自动封存正确
- [ ] Stream Merge 并行合并正确
- [ ] InvocationTracker 追踪/取消正确
- [ ] Anthropic Proxy thinking block 清理正确
- [ ] 全量测试通过
- [ ] 现有 Phase 1-5 功能不受影响
