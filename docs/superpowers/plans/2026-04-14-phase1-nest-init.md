# Phase 1: 猫窝初始化 + CLAUDE.md + cwd 透传 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `.neowai/` 猫窝目录结构、智能初始化 CLI、`CLAUDE.md` 区块注入，以及 Thread 级别的 provider `cwd` 透传。

**Architecture:** 新增 `NestConfig`/`NestRegistry`/`ClaudeMdWriter` 三个核心模块负责配置和文档管理；`InvocationOptions` 新增 `cwd` 字段并打通到所有 provider 子进程；Thread 创建 API 要求 `project_path`，前端增加项目选择器。

**Tech Stack:** Python 3.9+, FastAPI, Pydantic, Click, pathlib, asyncio

---

## File Map

| File | Responsibility |
|------|----------------|
| `src/config/nest_config.py` | `NestConfig` Pydantic model + 读写/校验/自动修正 |
| `src/config/nest_registry.py` | 全局已激活项目索引（`~/.meowai/nest-index.json`） |
| `src/cli/claude_md_writer.py` | `CLAUDE.md` `<!-- NEOWAI-CATS-START -->` 区块读写 |
| `src/cli/nest_init.py` | `neowai` 无参数时的智能初始化/状态显示 |
| `src/cli/main.py` | 把 `neowai` 根命令绑定到 nest init |
| `src/models/types.py` | `InvocationOptions` 新增 `cwd` 字段 |
| `src/providers/base.py` | `build_system_prompt()` 注入 capabilities/permissions（为后续 Phase 预留接口） |
| `src/providers/claude_provider.py` | `invoke()` 传入 `cwd` |
| `src/providers/codex_provider.py` | `invoke()` 传入 `cwd` |
| `src/providers/gemini_provider.py` | `invoke()` 传入 `cwd` |
| `src/providers/opencode_provider.py` | `invoke()` 传入 `cwd` |
| `src/collaboration/a2a_controller.py` | `_call_cat()` 传入 `thread.project_path` |
| `src/web/routes/ws.py` | 确保 `thread.project_path` 已存在 |
| `src/web/schemas.py` | `ThreadCreate.project_path` 改为 `str` 必填 |
| `src/thread/models.py` | `Thread.create()` project_path 必填 |
| `src/thread/thread_manager.py` | `create()` project_path 必填 |
| `src/thread/stores/sqlite_store.py` | `save_thread()` / `get_thread()` 正确处理 project_path |
| `web/src/api/client.ts` | 可能涉及 ThreadCreate 类型调整 |
| `web/src/components/thread/ThreadSidebar.tsx` | Thread 创建弹窗增加项目目录选择 |
| `tests/config/test_nest_config.py` | NestConfig 读写和校验测试 |
| `tests/cli/test_claude_md_writer.py` | CLAUDE.md 区块读写测试 |
| `tests/cli/test_nest_init.py` | nest_init 智能判断测试 |

---

### Task 1: NestConfig Pydantic Model + 读写/校验/自动修正

**Files:**
- Create: `src/config/nest_config.py`
- Create: `tests/config/test_nest_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/config/test_nest_config.py
import json
import pytest
from pathlib import Path

from src.config.nest_config import NestConfig, load_nest_config, save_nest_config, fix_config


def test_nest_config_defaults():
    cfg = NestConfig(project_name="demo", cats=["orange"])
    assert cfg.version == 1
    assert cfg.default_cat == "orange"
    assert cfg.settings["auto_sync_claude_md"] is True


def test_fix_config_invalid_default_cat():
    raw = {"version": 1, "project_name": "demo", "cats": ["inky"], "default_cat": "orange"}
    fixed, warnings = fix_config(raw, valid_cats={"inky": None})
    assert fixed["default_cat"] == "inky"
    assert any("default_cat" in w for w in warnings)


def test_load_nest_config_not_exists_creates_default(tmp_path):
    path = tmp_path / ".neowai" / "config.json"
    cfg = load_nest_config(path, project_name="demo", valid_cats={"orange": None})
    assert cfg.project_name == "demo"
    assert cfg.cats == ["orange"]
    assert path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_nest_config.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'src.config.nest_config'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/config/nest_config.py
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, validator


class NestConfig(BaseModel):
    version: int = Field(default=1, ge=1)
    project_name: str = Field(..., min_length=1)
    activated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    default_cat: str = Field(default="orange", min_length=1)
    cats: List[str] = Field(default_factory=list, min_items=1)
    settings: Dict[str, Any] = Field(default_factory=lambda: {
        "auto_sync_claude_md": True,
        "collect_metrics": True,
    })

    @validator("cats")
    def cats_not_empty(cls, v):
        if not v:
            raise ValueError("cats must not be empty")
        return v


def _default_config(project_name: str, valid_cats: Dict[str, Any]) -> NestConfig:
    first_cat = list(valid_cats.keys())[0] if valid_cats else "orange"
    return NestConfig(
        project_name=project_name,
        default_cat=first_cat,
        cats=[first_cat],
    )


def fix_config(raw: dict, valid_cats: Dict[str, Any]) -> Tuple[dict, List[str]]:
    warnings = []
    fixed = dict(raw)

    if "version" not in fixed:
        fixed["version"] = 1
        warnings.append("缺少 version，已填充为 1")

    if "settings" not in fixed or not isinstance(fixed.get("settings"), dict):
        fixed["settings"] = {"auto_sync_claude_md": True, "collect_metrics": True}
        warnings.append("缺少 settings，已填充默认值")

    cats = fixed.get("cats", [])
    if not isinstance(cats, list):
        cats = []
    original_cats = list(cats)
    cats = [c for c in cats if c in valid_cats]
    if len(cats) != len(original_cats):
        warnings.append(f"过滤了不存在的 cat_id: {set(original_cats) - set(cats)}")
    if not cats:
        first = list(valid_cats.keys())[0] if valid_cats else "orange"
        cats = [first]
        warnings.append(f"cats 为空，已修正为 [{first}]")
    fixed["cats"] = cats

    default_cat = fixed.get("default_cat")
    if default_cat not in cats:
        fixed["default_cat"] = cats[0]
        warnings.append(f"default_cat '{default_cat}' 不在 cats 中，已修正为 '{cats[0]}'")

    return fixed, warnings


def load_nest_config(
    path: Path,
    project_name: str,
    valid_cats: Dict[str, Any],
    interactive: bool = False,
) -> Tuple[NestConfig, List[str]]:
    """
    加载 nest config。文件不存在时自动创建。
    返回 (config, warnings)。
    """
    path = Path(path)
    if not path.exists():
        cfg = _default_config(project_name, valid_cats)
        save_nest_config(path, cfg)
        return cfg, []

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        cfg = _default_config(project_name, valid_cats)
        return cfg, [f"config.json 解析失败 ({e})，本次使用默认配置继续"]

    fixed, warnings = fix_config(raw, valid_cats)
    try:
        cfg = NestConfig(**fixed)
    except Exception as e:
        cfg = _default_config(project_name, valid_cats)
        warnings.append(f"config.json 校验失败 ({e})，本次使用默认配置继续")

    if interactive and warnings:
        # 交互模式下才自动修复并写回
        save_nest_config(path, cfg)
        warnings.append("已自动修复并保存 config.json")

    return cfg, warnings


def save_nest_config(path: Path, config: NestConfig) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config.dict(), f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_nest_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config/nest_config.py tests/config/test_nest_config.py
git commit -m "feat: NestConfig Pydantic model with validation and auto-fix

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: NestRegistry (全局已激活项目索引)

**Files:**
- Create: `src/config/nest_registry.py`
- Create: `tests/config/test_nest_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/config/test_nest_registry.py
import json
import pytest
from pathlib import Path

from src.config.nest_registry import NestRegistry


def test_registry_add_and_list(tmp_path, monkeypatch):
    index_path = tmp_path / "nest-index.json"
    monkeypatch.setattr(
        "src.config.nest_registry._index_path",
        index_path,
    )
    reg = NestRegistry()
    reg.register("/home/user/project-a")
    projects = reg.list_projects()
    assert len(projects) == 1
    assert projects[0]["path"] == "/home/user/project-a"


def test_registry_is_registered(tmp_path, monkeypatch):
    index_path = tmp_path / "nest-index.json"
    monkeypatch.setattr(
        "src.config.nest_registry._index_path",
        index_path,
    )
    reg = NestRegistry()
    reg.register("/home/user/project-b")
    assert reg.is_registered("/home/user/project-b") is True
    assert reg.is_registered("/home/user/project-c") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/config/test_nest_registry.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
# src/config/nest_registry.py
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

INDEX_PATH = Path.home() / ".meowai" / "nest-index.json"


def _index_path() -> Path:
    return INDEX_PATH


class NestRegistry:
    """管理全局已激活的项目目录索引"""

    def __init__(self, index_path: Path = None):
        self.index_path = index_path or _index_path()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.index_path.exists():
            return {"version": 1, "projects": []}
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"version": 1, "projects": []}

    def _save(self, data: Dict[str, Any]) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def register(self, project_path: str) -> None:
        data = self._load()
        projects = data.get("projects", [])
        now = datetime.now(timezone.utc).isoformat()
        existing = next((p for p in projects if p["path"] == project_path), None)
        if existing:
            existing["last_used_at"] = now
        else:
            projects.append({
                "path": project_path,
                "activated_at": now,
                "last_used_at": now,
            })
        data["projects"] = projects
        self._save(data)

    def unregister(self, project_path: str) -> bool:
        data = self._load()
        projects = data.get("projects", [])
        original_len = len(projects)
        data["projects"] = [p for p in projects if p["path"] != project_path]
        changed = len(data["projects"]) != original_len
        if changed:
            self._save(data)
        return changed

    def list_projects(self) -> List[Dict[str, Any]]:
        data = self._load()
        return list(data.get("projects", []))

    def is_registered(self, project_path: str) -> bool:
        return any(p["path"] == project_path for p in self.list_projects())

    def update_last_used(self, project_path: str) -> None:
        self.register(project_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/config/test_nest_registry.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/config/nest_registry.py tests/config/test_nest_registry.py
git commit -m "feat: NestRegistry for global activated project index

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: ClaudeMdWriter (CLAUDE.md 区块读写)

**Files:**
- Create: `src/cli/claude_md_writer.py`
- Create: `tests/cli/test_claude_md_writer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_claude_md_writer.py
import pytest
from pathlib import Path

from src.cli.claude_md_writer import (
    read_neowai_block,
    write_neowai_block,
    NEOWAI_START,
    NEOWAI_END,
)


def test_append_to_empty_file(tmp_path):
    path = tmp_path / "CLAUDE.md"
    cats_text = "## NeowAI Cats\n\n- orange: 热情活泼的橘猫"
    write_neowai_block(path, cats_text)
    content = path.read_text(encoding="utf-8")
    assert NEOWAI_START in content
    assert cats_text in content


def test_replace_existing_block(tmp_path):
    path = tmp_path / "CLAUDE.md"
    original = f"# Hello\n\n{NEOWAI_START}\n## Old\n{NEOWAI_END}\n\nFooter"
    path.write_text(original, encoding="utf-8")
    write_neowai_block(path, "## New")
    content = path.read_text(encoding="utf-8")
    assert "## New" in content
    assert "## Old" not in content
    assert "Footer" in content


def test_read_block(tmp_path):
    path = tmp_path / "CLAUDE.md"
    block = f"{NEOWAI_START}\n## Cats\n{NEOWAI_END}"
    path.write_text(f"# Title\n{block}\n", encoding="utf-8")
    assert read_neowai_block(path) == "## Cats"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_claude_md_writer.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
# src/cli/claude_md_writer.py
import re
from pathlib import Path

NEOWAI_START = "<!-- NEOWAI-CATS-START -->"
NEOWAI_END = "<!-- NEOWAI-CATS-END -->"

_BLOCK_PATTERN = re.compile(
    re.escape(NEOWAI_START) + r"\n?(.*?)\n?" + re.escape(NEOWAI_END),
    re.DOTALL,
)


def read_neowai_block(path: Path) -> str:
    path = Path(path)
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    match = _BLOCK_PATTERN.search(content)
    return match.group(1).strip() if match else ""


def write_neowai_block(path: Path, block_content: str) -> None:
    path = Path(path)
    new_block = f"{NEOWAI_START}\n{block_content}\n{NEOWAI_END}"

    if not path.exists():
        path.write_text(new_block + "\n", encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    if _BLOCK_PATTERN.search(content):
        replaced = _BLOCK_PATTERN.sub(new_block, content)
    else:
        replaced = content.rstrip("\n") + "\n\n" + new_block + "\n"

    # Backup original before overwrite
    backup = path.with_suffix(".md.bak")
    if not backup.exists():
        backup.write_text(content, encoding="utf-8")

    path.write_text(replaced, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_claude_md_writer.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli/claude_md_writer.py tests/cli/test_claude_md_writer.py
git commit -m "feat: ClaudeMdWriter for NEOWAI-CATS block injection

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: nest_init CLI 智能初始化

**Files:**
- Create: `src/cli/nest_init.py`
- Create: `tests/cli/test_nest_init.py`
- Modify: `src/cli/main.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/cli/test_nest_init.py
import json
from pathlib import Path
from click.testing import CliRunner

from src.cli.main import cli


def test_neowai_init_in_empty_dir(tmp_path, monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Mock cat registry
        monkeypatch.setattr(
            "src.cli.nest_init.CatRegistry",
            lambda: type("MockReg", (), {
                "get_all_ids": lambda self: ["orange"],
                "get": lambda self, cid: type("Obj", (), {"cat_id": "orange", "name": "阿橘", "personality": "活泼", "role_description": "dev", "capabilities": [], "permissions": []})(),
            })(),
        )
        result = runner.invoke(cli, [""])
        # Click group without subcommand prints help by default; we need to modify main.py first
        # This test verifies the new behavior after main.py change
```

Actually, for the test we need to call `run_nest_init` directly since `cli` is a group and click behavior changes:

```python
# tests/cli/test_nest_init.py
import json
from pathlib import Path

from src.cli.nest_init import run_nest_init


def test_run_nest_init_creates_nest(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.cli.nest_init.CatRegistry",
        lambda: type("MockReg", (), {
            "get_all_ids": lambda self: ["orange"],
            "get": lambda self, cid: type("Obj", (), {
                "cat_id": "orange",
                "name": "阿橘",
                "personality": "活泼",
                "role_description": "dev",
                "capabilities": ["chat"],
                "permissions": [],
            })(),
        })(),
    )
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        run_nest_init(interactive=False)
        assert (tmp_path / ".neowai" / "config.json").exists()
        assert (tmp_path / "CLAUDE.md").exists()
    finally:
        os.chdir(old_cwd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_nest_init.py -v`

Expected: FAIL with import error

- [ ] **Step 3: Write minimal implementation**

```python
# src/cli/nest_init.py
import os
import click
from pathlib import Path

from src.config.nest_config import load_nest_config, save_nest_config
from src.config.nest_registry import NestRegistry
from src.cli.claude_md_writer import write_neowai_block
from src.models.cat_registry import CatRegistry


def _build_cats_block(valid_cats: list, cat_registry: CatRegistry) -> str:
    lines = ["## NeowAI Cats"]
    for cat_id in valid_cats:
        cat = cat_registry.get(cat_id)
        parts = [f"- **{cat.name}** ({cat_id})"]
        if cat.role_description:
            parts.append(f"  - 角色：{cat.role_description}")
        if cat.personality:
            parts.append(f"  - 性格：{cat.personality}")
        if cat.capabilities:
            parts.append(f"  - 能力：{', '.join(cat.capabilities)}")
        if cat.permissions:
            parts.append(f"  - 权限：{', '.join(cat.permissions)}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def run_nest_init(interactive: bool = True) -> None:
    project_path = Path.cwd()
    nest_dir = project_path / ".neowai"
    config_path = nest_dir / "config.json"
    claude_md_path = project_path / "CLAUDE.md"

    cat_registry = CatRegistry()
    # Ensure registry is bootstrapped from current directory config
    try:
        from src.models.registry_init import initialize_registries
        initialize_registries(str(project_path / "cat-config.json"))
    except Exception:
        pass

    valid_cats = {cid: None for cid in cat_registry.get_all_ids()}
    if not valid_cats:
        click.echo("⚠️  当前目录没有可用的 cat-config.json，无法初始化 NeowAI 项目。")
        return

    registry = NestRegistry()
    already_initialized = registry.is_registered(str(project_path)) or config_path.exists()

    if not already_initialized:
        click.echo(f"🐱 正在初始化 NeowAI 猫窝: {project_path}")
        cfg, warnings = load_nest_config(
            config_path,
            project_name=project_path.name,
            valid_cats=valid_cats,
            interactive=interactive,
        )
        if warnings:
            for w in warnings:
                click.echo(f"  ⚠️ {w}")
        save_nest_config(config_path, cfg)
        try:
            block = _build_cats_block(cfg.cats, cat_registry)
            write_neowai_block(claude_md_path, block)
            click.echo("  ✅ CLAUDE.md 已更新")
        except OSError as e:
            click.echo(f"  ⚠️ CLAUDE.md 写入失败: {e}，后续调用将使用临时 system prompt")
        registry.register(str(project_path))
        click.echo("  ✅ 初始化完成！")
        click.echo("\n  你可以通过 `neowai web` 启动 Web UI，")
        click.echo("  或 `neowai chat` 开始命令行对话。")
    else:
        cfg, warnings = load_nest_config(
            config_path,
            project_name=project_path.name,
            valid_cats=valid_cats,
            interactive=False,
        )
        if warnings and interactive:
            click.echo("⚠️  config.json 存在一些问题：")
            for w in warnings:
                click.echo(f"  - {w}")
            if click.confirm("是否自动修复并保存？"):
                save_nest_config(config_path, cfg)
                click.echo("✅ 已修复")

        click.echo(f"🐱 项目已激活: {project_path}")
        click.echo(f"   默认猫: {cfg.default_cat}")
        click.echo(f"   可用猫: {', '.join(cfg.cats)}")
        if not warnings:
            click.echo("\n  提示: 使用 `neowai web` 启动 Web UI 或 `neowai chat` 开始对话")
```

Now modify `src/cli/main.py` to bind the default command:

```python
# src/cli/main.py — modify the cli() group and add a default command hook
import sys

# ... existing imports ...
from src.cli.nest_init import run_nest_init

# Keep existing bootstrap_registries and cli definitions

# Add a default handler when no subcommand is given
def invoke_cli(ctx):
    if ctx.invoked_subcommand is None:
        run_nest_init(interactive=True)
    else:
        return ctx.invoke(cli)

# We need to override the group's invocation behavior
def main():
    if len(sys.argv) == 1:
        run_nest_init(interactive=True)
    else:
        cli()

# At the bottom replace the standard __main__ guard pattern if present
```

Since `main.py` currently uses `@click.group()`, the simplest change is to detect no-args at the bottom:

Find the bottom of `src/cli/main.py` and add:

```python
if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        run_nest_init()
    else:
        cli()
```

But the entrypoint in `pyproject.toml` or `setup.py` might call `cli()` directly. Safer approach: wrap `cli` invocation:

Replace the existing `if __name__ == "__main__":` or add at bottom:

```python
def main():
    import sys
    if len(sys.argv) == 1:
        run_nest_init(interactive=True)
    else:
        cli()

if __name__ == "__main__":
    main()
```

If there is no `__main__` block, just append this.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_nest_init.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/cli/nest_init.py tests/cli/test_nest_init.py src/cli/main.py
git commit -m "feat: neowai CLI smart init with CLAUDE.md block injection

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: InvocationOptions 新增 cwd 字段

**Files:**
- Modify: `src/models/types.py`

- [ ] **Step 1: 在 InvocationOptions 中添加 cwd 字段**

```python
# src/models/types.py 中 InvocationOptions 类
@dataclass
class InvocationOptions:
    system_prompt: Optional[str] = None
    timeout: float = 300.0
    session_id: Optional[str] = None
    effort: Optional[str] = None
    mcp_config: Optional[Dict[str, Any]] = None
    extra_args: List[str] = field(default_factory=list)
    cwd: Optional[str] = None   # NEW
```

- [ ] **Step 2: 确保 py_compile 通过**

Run: `python -m py_compile src/models/types.py`

Expected: no output (success)

- [ ] **Step 3: Commit**

```bash
git add src/models/types.py
git commit -m "feat: add cwd field to InvocationOptions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Provider 层传入 cwd

**Files:**
- Modify: `src/providers/claude_provider.py`
- Modify: `src/providers/codex_provider.py`
- Modify: `src/providers/gemini_provider.py`
- Modify: `src/providers/opencode_provider.py`

- [ ] **Step 1: ClaudeProvider 传入 cwd**

In `src/providers/claude_provider.py`, change `invoke()`:

```python
    async def invoke(self, prompt: str, options: InvocationOptions = None) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()
        args = self._build_args(prompt, options)
        timeout = options.timeout or 300.0
        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=timeout, env=self.build_env(), cwd=options.cwd
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id)
        finally:
            yield AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)
```

- [ ] **Step 2: CodexProvider 传入 cwd**

Read `src/providers/codex_provider.py`, modify `invoke()` similarly:

```python
async for event in spawn_cli(self.config.cli_command, args, timeout=timeout, env=self.build_env(), cwd=options.cwd):
```

- [ ] **Step 3: GeminiProvider 传入 cwd**

Same change in `src/providers/gemini_provider.py`.

- [ ] **Step 4: OpenCodeProvider 传入 cwd**

Same change in `src/providers/opencode_provider.py`.

- [ ] **Step 5: Run py_compile on all four files**

Run:
```bash
python -m py_compile src/providers/claude_provider.py
python -m py_compile src/providers/codex_provider.py
python -m py_compile src/providers/gemini_provider.py
python -m py_compile src/providers/opencode_provider.py
```

Expected: no output

- [ ] **Step 6: Commit**

```bash
git add src/providers/claude_provider.py src/providers/codex_provider.py src/providers/gemini_provider.py src/providers/opencode_provider.py
git commit -m "feat: pass cwd through all providers to spawn_cli

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: A2AController 和 ws.py 传入 project_path

**Files:**
- Modify: `src/collaboration/a2a_controller.py` (`_call_cat` method)
- Modify: `src/web/routes/ws.py`

- [ ] **Step 1: A2AController._call_cat 传入 cwd**

In `src/collaboration/a2a_controller.py`, find `_call_cat()` signature and the `invoke()` call:

Change line 258 from:
```python
        options = InvocationOptions(system_prompt=system_prompt, session_id=session_id)
```
to:
```python
        options = InvocationOptions(
            system_prompt=system_prompt,
            session_id=session_id,
            cwd=thread.project_path,
        )
```

- [ ] **Step 2: ws.py 确保 thread 有 project_path**

In `src/web/routes/ws.py`, in `_handle_send_message`, after loading `thread`, add a guard:

```python
    if not thread.project_path:
        await websocket.send_json({
            "type": "error",
            "message": "当前 Thread 未绑定项目目录，请先选择项目"
        })
        return
```

- [ ] **Step 3: 运行相关测试**

Run: `pytest tests/ -k "thread" --no-header -q`

Expected: existing tests pass (or only pre-existing failures)

- [ ] **Step 4: Commit**

```bash
git add src/collaboration/a2a_controller.py src/web/routes/ws.py
git commit -m "feat: pass thread.project_path as cwd into A2AController

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Thread project_path 必填 + API/Web 适配

**Files:**
- Modify: `src/web/schemas.py`
- Modify: `src/thread/models.py`
- Modify: `src/thread/thread_manager.py`
- Modify: `src/thread/stores/sqlite_store.py`
- Modify: `web/src/api/client.ts` (type for ThreadCreate)
- Modify: `web/src/components/thread/ThreadSidebar.tsx` (create thread dialog)

- [ ] **Step 1: schemas.py — project_path 必填**

```python
# src/web/schemas.py
class ThreadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cat_id: str = Field(default="orange")
    project_path: str = Field(..., min_length=1, description="Project directory path for this thread")
```

- [ ] **Step 2: thread/models.py — create() 必填**

In `src/thread/models.py`, change `Thread.create()` signature:

```python
    @classmethod
    def create(cls, name: str, current_cat_id: str = DEFAULT_CAT_ID, project_path: Optional[str] = None) -> "Thread":
```

to:

```python
    @classmethod
    def create(cls, name: str, current_cat_id: str = DEFAULT_CAT_ID, project_path: str = "") -> "Thread":
```

And in the constructor body, set:
```python
            project_path=project_path or "",
```

- [ ] **Step 3: thread_manager.py — create() 必填**

```python
    async def create(self, name: str, current_cat_id: str = "orange", project_path: str = "") -> Thread:
        thread = Thread.create(name, current_cat_id, project_path)
        await self._store.save_thread(thread)
        return thread
```

- [ ] **Step 4: sqlite_store.py — get_thread 加载 project_path**

In `src/thread/stores/sqlite_store.py`, find `get_thread()` row → Thread conversion and ensure `project_path=row[6] or ""` is used. Also check `list_threads()`.

Example fix in `get_thread`:

```python
        row = await cursor.fetchone()
        if not row:
            return None
        thread = Thread(
            id=row[0],
            name=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            current_cat_id=row[4],
            is_archived=bool(row[5]),
            project_path=row[6] or "",
            messages=[],
        )
```

And `list_threads` similarly.

- [ ] **Step 5: web frontend — ThreadCreate 类型调整**

In `web/src/api/client.ts`, find `createThread` payload type and ensure `project_path: string` is required. Example:

```typescript
export interface ThreadCreateRequest {
  name: string;
  cat_id?: string;
  project_path: string;
}
```

- [ ] **Step 6: ThreadSidebar 创建弹窗增加项目选择**

In `web/src/components/thread/ThreadSidebar.tsx`, locate the create-thread dialog/modal.

Add a `<select>` or input for `project_path`. If `NestRegistry` API doesn't exist yet, hardcode a simple text input with a default of `"/Users/wangzhao/Documents/claude_projects/catwork"` (or better, use `window.prompt` style for Phase 1), but at minimum require the user to enter a path.

Since Phase 1 doesn't include the Projects API yet, use a simple text input in the create dialog:

```tsx
// Inside the create thread dialog state
const [projectPath, setProjectPath] = useState("");

// In the form
<input
  type="text"
  value={projectPath}
  onChange={(e) => setProjectPath(e.target.value)}
  placeholder="项目目录绝对路径"
  required
/>

// On submit
createThread({ name, cat_id: selectedCat, project_path: projectPath });
```

- [ ] **Step 7: Run backend tests**

Run: `pytest tests/web/test_threads.py -v` (or `tests/web/...` relevant thread tests)

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/web/schemas.py src/thread/models.py src/thread/thread_manager.py src/thread/stores/sqlite_store.py web/src/api/client.ts web/src/components/thread/ThreadSidebar.tsx
git commit -m "feat: make project_path required for Thread creation

- Schema, model, manager, and store updates
- Frontend create dialog adds project_path input

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 9: Phase 1 集成验证

- [ ] **Step 1: 运行全部新测试**

```bash
pytest tests/config/test_nest_config.py tests/config/test_nest_registry.py tests/cli/test_claude_md_writer.py tests/cli/test_nest_init.py -v
```

Expected: ALL PASS

- [ ] **Step 2: 运行 backend 测试套件**

```bash
pytest tests/ -q --no-header
```

Expected: existing failures only (check against pre-existing baseline)

- [ ] **Step 3: TypeScript 编译检查**

```bash
cd web && npx tsc --noEmit
```

Expected: clean (or only pre-existing errors)

- [ ] **Step 4: Final commit if any fixes needed**

Make any small fixes and commit.

---

## Self-Review

**Spec coverage check:**
- `neowai` 智能初始化 → Task 4 ✅
- `.neowai/` 猫窝目录 + `config.json` → Task 1 ✅
- `CLAUDE.md` 区块注入 → Task 3 ✅
- Thread `project_path` 必填 → Task 8 ✅
- provider `cwd` 透传 → Task 5, 6, 7 ✅

**Placeholder scan:** No TBD/TODO/"implement later" found. ✅

**Type consistency:** `InvocationOptions.cwd` used consistently across all providers and `A2AController`. `project_path` is `str` everywhere. ✅

**Gap identified but intentionally deferred:** Web UI Projects tab (`ProjectSettings.tsx`) and Projects API are not in Phase 1 because Phase 1 focus is the backend infrastructure (cwd, nest, CLAUDE.md). The frontend only gets a minimal `project_path` text input in Thread creation. The full Projects settings tab will come in Phase 2 or as a fast follow.
