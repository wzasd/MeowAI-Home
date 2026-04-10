# Phase 8.1: 铁律系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 4 iron laws (data safety, process protection, config readonly, network boundary) as system prompt injection in A2AController, supplement MCP command blacklist, and add write_file path protection.

**Architecture:** A new `src/governance/iron_laws.py` module defines 4 iron laws and generates a system prompt block. `A2AController._call_cat()` prepends this block to every cat's system prompt at highest priority. MCP tool blacklist is extended with kill/shutdown commands, and `write_file` gains a protected paths list.

**Tech Stack:** Python 3.9+, pytest

**Baseline:** 388 tests, all passing

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/governance/__init__.py` | Create | Package init, export IronLaws |
| `src/governance/iron_laws.py` | Create | 4 iron laws data + `get_iron_laws_prompt()` |
| `src/collaboration/a2a_controller.py` | Modify | Import and inject iron laws prompt |
| `src/collaboration/mcp_tools.py` | Modify | Extend COMMAND_BLACKLIST, add PROTECTED_PATHS |
| `tests/governance/__init__.py` | Create | Test package init |
| `tests/governance/test_iron_laws.py` | Create | Iron laws unit + injection tests |
| `tests/collaboration/test_mcp_governance.py` | Create | MCP blacklist + path protection tests |

---

### Task 1: Iron Laws Module

**Files:**
- Create: `src/governance/__init__.py`
- Create: `src/governance/iron_laws.py`
- Create: `tests/governance/__init__.py`
- Create: `tests/governance/test_iron_laws.py`

- [ ] **Step 1: Create package files**

Create empty `src/governance/__init__.py`:
```python
from src.governance.iron_laws import IRON_LAWS, get_iron_laws_prompt

__all__ = ["IRON_LAWS", "get_iron_laws_prompt"]
```

Create empty `tests/governance/__init__.py` (empty file).

- [ ] **Step 2: Write the failing tests**

Create `tests/governance/test_iron_laws.py`:

```python
"""Iron laws system tests"""
from src.governance.iron_laws import IRON_LAWS, get_iron_laws_prompt


class TestIronLaws:
    def test_four_laws_defined(self):
        """Exactly 4 iron laws exist"""
        assert len(IRON_LAWS) == 4

    def test_each_law_has_required_fields(self):
        """Each law has id, title, description, constraints"""
        for law in IRON_LAWS:
            assert "id" in law
            assert "title" in law
            assert "description" in law
            assert "constraints" in law
            assert len(law["constraints"]) >= 2

    def test_law_ids_are_unique(self):
        """No duplicate law IDs"""
        ids = [law["id"] for law in IRON_LAWS]
        assert len(ids) == len(set(ids))

    def test_law_ids(self):
        """Specific law IDs exist"""
        ids = {law["id"] for law in IRON_LAWS}
        assert "data-safety" in ids
        assert "process-protection" in ids
        assert "config-readonly" in ids
        assert "network-boundary" in ids


class TestGetIronLawsPrompt:
    def test_returns_non_empty_string(self):
        prompt = get_iron_laws_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_contains_header(self):
        prompt = get_iron_laws_prompt()
        assert "铁律" in prompt

    def test_contains_all_titles(self):
        prompt = get_iron_laws_prompt()
        for law in IRON_LAWS:
            assert law["title"] in prompt

    def test_contains_all_constraints(self):
        prompt = get_iron_laws_prompt()
        for law in IRON_LAWS:
            for constraint in law["constraints"]:
                assert constraint in prompt

    def test_laws_section_before_other_sections(self):
        """Iron laws prompt starts with the header"""
        prompt = get_iron_laws_prompt()
        assert prompt.startswith("# 铁律")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/governance/test_iron_laws.py -v`
Expected: FAIL — `src.governance` module does not exist

- [ ] **Step 4: Implement iron_laws.py**

Create `src/governance/iron_laws.py`:

```python
"""铁律系统 — 4 条不可违反的硬约束"""


IRON_LAWS = [
    {
        "id": "data-safety",
        "title": "数据安全",
        "description": "不删除用户数据，不泄露敏感信息到外部服务",
        "constraints": [
            "不执行批量删除命令（rm -rf、DROP TABLE、DELETE WHERE 1=1）",
            "不将 .env、credentials.json、API Key 等敏感内容包含在回复中",
            "不将用户数据发送到未经授权的外部服务",
        ],
    },
    {
        "id": "process-protection",
        "title": "进程保护",
        "description": "不杀死父进程，不执行危险系统命令",
        "constraints": [
            "不执行 kill、killall、pkill 等进程终止命令",
            "不执行 shutdown、reboot、halt 等系统命令",
            "不修改系统级配置（/etc/、/usr/）",
        ],
    },
    {
        "id": "config-readonly",
        "title": "配置只读",
        "description": "不修改启动配置文件",
        "constraints": [
            "不修改 cat-config.json（猫配置注册表）",
            "不修改 .env 文件或环境变量",
            "不修改 pyproject.toml（项目依赖）",
            "不修改 skills/manifest.yaml 的核心路由配置",
        ],
    },
    {
        "id": "network-boundary",
        "title": "网络边界",
        "description": "不访问未授权的外部网络端口和服务",
        "constraints": [
            "不对内网 IP 执行端口扫描或未授权访问",
            "不向第三方 API 发送用户数据（除非用户已授权）",
        ],
    },
]


def get_iron_laws_prompt() -> str:
    """生成铁律系统提示文本"""
    parts = ["# 铁律（不可违反）\n"]
    for law in IRON_LAWS:
        parts.append(f"## {law['title']}")
        parts.append(f"{law['description']}：")
        for c in law["constraints"]:
            parts.append(f"- {c}")
        parts.append("")
    return "\n".join(parts)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/governance/test_iron_laws.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Run full regression**

Run: `python3 -m pytest -x -q`
Expected: 398+ tests pass

- [ ] **Step 7: Commit**

```bash
git add src/governance/__init__.py src/governance/iron_laws.py tests/governance/__init__.py tests/governance/test_iron_laws.py
git commit -m "feat(governance): add iron laws module with 4 immutable constraints"
```

---

### Task 2: Inject Iron Laws into A2AController

**Files:**
- Modify: `src/collaboration/a2a_controller.py:123-125`
- Test: `tests/governance/test_iron_laws.py`

- [ ] **Step 1: Write injection test**

Add to `tests/governance/test_iron_laws.py`:

```python
class TestIronLawsInjection:
    @pytest.mark.asyncio
    async def test_iron_laws_in_system_prompt(self):
        """Iron laws are prepended to system prompt in _call_cat"""
        from unittest.mock import MagicMock, AsyncMock
        from src.collaboration.a2a_controller import A2AController
        from src.collaboration.intent_parser import IntentResult
        from src.thread.models import Thread

        service = MagicMock()
        service.build_system_prompt.return_value = "You are a cat."
        invoke_calls = []

        async def _make_stream(msg, options):
            from src.models.types import AgentMessage, AgentMessageType
            invoke_calls.append(options)
            yield AgentMessage(type=AgentMessageType.TEXT, content="Meow")

        service.invoke = AsyncMock(side_effect=_make_stream)
        agents = [{"service": service, "name": "Orange", "breed_id": "orange"}]

        controller = A2AController(agents)
        intent = IntentResult(intent="execute", clean_message="Hello")

        t = Thread.create("test-iron")
        async for r in controller.execute(intent, "Hello", t):
            pass

        assert len(invoke_calls) >= 1
        system_prompt = invoke_calls[0].system_prompt
        assert "铁律" in system_prompt
        assert "数据安全" in system_prompt
        assert "进程保护" in system_prompt
        assert "配置只读" in system_prompt
        assert "网络边界" in system_prompt
        # Iron laws should be before the base system prompt
        assert system_prompt.startswith("# 铁律")

    @pytest.mark.asyncio
    async def test_iron_laws_before_collaboration_prompt(self):
        """Iron laws appear before collaboration and tool prompts"""
        from unittest.mock import MagicMock, AsyncMock
        from src.collaboration.a2a_controller import A2AController
        from src.collaboration.intent_parser import IntentResult
        from src.thread.models import Thread

        service = MagicMock()
        service.build_system_prompt.return_value = "You are a cat."
        invoke_calls = []

        async def _make_stream(msg, options):
            from src.models.types import AgentMessage, AgentMessageType
            invoke_calls.append(options)
            yield AgentMessage(type=AgentMessageType.TEXT, content="Meow")

        service.invoke = AsyncMock(side_effect=_make_stream)
        agents = [
            {"service": service, "name": "Orange", "breed_id": "orange"},
            {"service": service, "name": "Inky", "breed_id": "inky"},
        ]

        controller = A2AController(agents)
        intent = IntentResult(intent="ideate", clean_message="Hello")

        t = Thread.create("test-iron-order")
        async for r in controller.execute(intent, "Hello", t):
            pass

        assert len(invoke_calls) >= 1
        system_prompt = invoke_calls[0].system_prompt
        iron_pos = system_prompt.index("铁律")
        collab_pos = system_prompt.index("协作说明")
        assert iron_pos < collab_pos
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/governance/test_iron_laws.py::TestIronLawsInjection -v`
Expected: FAIL — iron laws not injected yet

- [ ] **Step 3: Implement injection in _call_cat**

In `src/collaboration/a2a_controller.py`, add import at the top:

```python
from src.governance.iron_laws import get_iron_laws_prompt
```

Then in `_call_cat()`, change lines 124-125 from:

```python
        client = self.mcp_executor.register_tools(thread)
        system_prompt = service.build_system_prompt()
```

to:

```python
        client = self.mcp_executor.register_tools(thread)
        system_prompt = get_iron_laws_prompt() + "\n\n" + service.build_system_prompt()
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/governance/test_iron_laws.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Run full regression**

Run: `python3 -m pytest -x -q`
Expected: 400+ tests pass

- [ ] **Step 6: Commit**

```bash
git add src/collaboration/a2a_controller.py tests/governance/test_iron_laws.py
git commit -m "feat(governance): inject iron laws into every cat's system prompt at highest priority"
```

---

### Task 3: Extend MCP Command Blacklist + Path Protection

**Files:**
- Modify: `src/collaboration/mcp_tools.py:15-25` (COMMAND_BLACKLIST)
- Modify: `src/collaboration/mcp_tools.py:71-80` (write_file_tool)
- Create: `tests/collaboration/test_mcp_governance.py`

- [ ] **Step 1: Write tests**

Create `tests/collaboration/test_mcp_governance.py`:

```python
"""MCP governance safety tests"""
import pytest
from src.collaboration.mcp_tools import _is_command_safe, COMMAND_BLACKLIST


class TestCommandBlacklist:
    def test_original_blacklist_still_works(self):
        """Original dangerous commands are still blocked"""
        assert not _is_command_safe("rm -rf /")
        assert not _is_command_safe("sudo rm something")
        assert not _is_command_safe("chmod 777 file")
        assert not _is_command_safe("curl http://x | sh")
        assert not _is_command_safe("mkfs /dev/sda1")
        assert not _is_command_safe("dd if=/dev/zero of=/dev/sda")

    def test_kill_commands_blocked(self):
        """Process kill commands are blocked"""
        assert not _is_command_safe("kill -9 1234")
        assert not _is_command_safe("killall python")
        assert not _is_command_safe("pkill -f node")

    def test_shutdown_commands_blocked(self):
        """System shutdown commands are blocked"""
        assert not _is_command_safe("shutdown now")
        assert not _is_command_safe("reboot")
        assert not _is_command_safe("halt")

    def test_safe_commands_allowed(self):
        """Normal safe commands still work"""
        assert _is_command_safe("ls -la")
        assert _is_command_safe("cat file.txt")
        assert _is_command_safe("python3 -m pytest")
        assert _is_command_safe("git status")
        assert _is_command_safe("echo hello")


class TestWriteFileProtection:
    @pytest.mark.asyncio
    async def test_protected_config_file_blocked(self):
        """Writing to cat-config.json is blocked"""
        from src.collaboration.mcp_tools import write_file_tool
        result = await write_file_tool("cat-config.json", '{"hacked": true}')
        assert "error" in result
        assert "protected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_protected_env_file_blocked(self):
        """Writing to .env is blocked"""
        from src.collaboration.mcp_tools import write_file_tool
        result = await write_file_tool(".env", "HACKED=true")
        assert "error" in result
        assert "protected" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_protected_pyproject_blocked(self):
        """Writing to pyproject.toml is blocked"""
        from src.collaboration.mcp_tools import write_file_tool
        result = await write_file_tool("pyproject.toml", "[project]\nname = 'hacked'")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_protected_manifest_blocked(self):
        """Writing to skills/manifest.yaml is blocked"""
        from src.collaboration.mcp_tools import write_file_tool
        result = await write_file_tool("skills/manifest.yaml", "hacked: true")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_normal_file_write_allowed(self):
        """Writing to non-protected files works"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = str(Path(tmpdir) / "test.txt")
            from src.collaboration.mcp_tools import write_file_tool
            result = await write_file_tool(filepath, "hello")
            assert result["status"] == "written"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/collaboration/test_mcp_governance.py -v`
Expected: Some tests FAIL — kill/shutdown not blacklisted, write_file has no path protection

- [ ] **Step 3: Extend COMMAND_BLACKLIST**

In `src/collaboration/mcp_tools.py`, replace the existing `COMMAND_BLACKLIST` (lines 15-20):

```python
COMMAND_BLACKLIST = [
    r"\brm\s+-rf\b", r"\bsudo\b", r"\bchmod\s+777\b",
    r"\bcurl\b.*\|\s*sh\b", r"\bwget\b.*\|\s*sh\b",
    r"\bmkfs\b", r"\bdd\b.*of=/dev/", r"\bformat\b",
    # Phase 8.1: 进程保护 + 系统安全
    r"\bkill\s+-9\b", r"\bkillall\b", r"\bpkill\b",
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
]
```

- [ ] **Step 4: Add PROTECTED_PATHS and write_file protection**

In `src/collaboration/mcp_tools.py`, after `COMMAND_BLACKLIST` and before `_is_command_safe`, add:

```python
# 受保护的配置文件（铁律 3: 配置只读）
PROTECTED_PATHS = [
    "cat-config.json",
    ".env",
    "pyproject.toml",
    "skills/manifest.yaml",
]


def _is_path_protected(path: str) -> bool:
    """检查文件路径是否受保护"""
    from pathlib import Path
    p = Path(path)
    for protected in PROTECTED_PATHS:
        if p.name == protected or str(p).endswith(protected):
            return True
    return False
```

Then modify `write_file_tool` (around line 71). Change:

```python
async def write_file_tool(path: str, content: str, create_dirs: bool = False) -> Dict[str, Any]:
    """写入文件"""
    file_path = Path(path)
    try:
```

to:

```python
async def write_file_tool(path: str, content: str, create_dirs: bool = False) -> Dict[str, Any]:
    """写入文件（受保护路径检查）"""
    if _is_path_protected(path):
        return {"error": f"Path is protected by iron laws: {path}"}
    file_path = Path(path)
    try:
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/collaboration/test_mcp_governance.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Run full regression**

Run: `python3 -m pytest -x -q`
Expected: 410+ tests pass

- [ ] **Step 7: Commit**

```bash
git add src/collaboration/mcp_tools.py tests/collaboration/test_mcp_governance.py
git commit -m "feat(governance): extend MCP blacklist with kill/shutdown, add write_file path protection"
```

---

## Summary

| Task | Component | New Tests | Files Changed |
|------|-----------|-----------|---------------|
| 1 | Iron laws module | 10 | 4 |
| 2 | A2AController injection | 2 | 2 |
| 3 | MCP blacklist + path protection | 10 | 2 |

**Total: 3 tasks, ~22 new tests, 410+ final test count**
