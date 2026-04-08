# Phase 3.1: Thread 多会话管理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 Thread 多会话管理系统，支持创建、列出、切换、归档 thread，chat 使用当前 thread 的上下文。

**Architecture:** 采用 ThreadManager 单例模式管理所有 thread，内存 Dict 存储运行时状态，JSON 文件持久化到 `~/.meowai/threads.json`，每个 thread 维护独立的消息历史和当前猫配置。

**Tech Stack:** Python 3.9+, dataclasses, pytest, click (CLI), pathlib (存储路径)

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `src/thread/models.py` | Thread 和 Message 数据模型 |
| `src/thread/thread_manager.py` | ThreadManager 单例，核心管理逻辑 |
| `src/thread/persistence.py` | JSON 持久化（保存/加载） |
| `src/cli/thread_commands.py` | Thread 相关 CLI 命令 |
| `src/cli/main.py` | 集成 thread 命令和状态显示 |
| `tests/thread/test_models.py` | 模型测试 |
| `tests/thread/test_thread_manager.py` | ThreadManager 测试 |
| `tests/thread/test_persistence.py` | 持久化测试 |

---

## Task 1: Thread 数据模型

**Files:**
- Create: `src/thread/models.py`
- Test: `tests/thread/test_models.py`

**Context:** 定义 Thread 和 Message 数据类，用于存储会话信息和消息历史。

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p src/thread tests/thread
```

- [ ] **Step 2: 编写 Thread 和 Message 模型**

```python
# src/thread/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


@dataclass
class Message:
    """单条消息"""
    role: str  # "user" | "assistant"
    content: str
    cat_id: Optional[str] = None  # 如果是猫回复，记录是哪只
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "cat_id": self.cat_id,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(
            role=data["role"],
            content=data["content"],
            cat_id=data.get("cat_id"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class Thread:
    """对话线程"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    current_cat_id: str = "orange"  # 默认使用阿橘
    is_archived: bool = False

    @classmethod
    def create(cls, name: str, current_cat_id: str = "orange") -> "Thread":
        """创建新 thread"""
        now = datetime.now()
        return cls(
            id=str(uuid.uuid4())[:8],  # 短ID便于使用
            name=name,
            created_at=now,
            updated_at=now,
            current_cat_id=current_cat_id,
            messages=[]
        )

    def add_message(self, role: str, content: str, cat_id: Optional[str] = None):
        """添加消息并更新更新时间"""
        self.messages.append(Message(role=role, content=content, cat_id=cat_id))
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "current_cat_id": self.current_cat_id,
            "is_archived": self.is_archived
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Thread":
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            current_cat_id=data.get("current_cat_id", "orange"),
            is_archived=data.get("is_archived", False)
        )
```

- [ ] **Step 3: 编写模型测试**

```python
# tests/thread/test_models.py
import pytest
from datetime import datetime
from src.thread.models import Message, Thread


def test_message_creation():
    """测试消息创建"""
    msg = Message(role="user", content="Hello", cat_id=None)
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.cat_id is None
    assert isinstance(msg.timestamp, datetime)


def test_message_to_dict():
    """测试消息序列化"""
    msg = Message(role="assistant", content="Hi", cat_id="orange")
    data = msg.to_dict()
    assert data["role"] == "assistant"
    assert data["content"] == "Hi"
    assert data["cat_id"] == "orange"
    assert "timestamp" in data


def test_message_from_dict():
    """测试消息反序列化"""
    data = {
        "role": "user",
        "content": "Test",
        "cat_id": None,
        "timestamp": datetime.now().isoformat()
    }
    msg = Message.from_dict(data)
    assert msg.role == "user"
    assert msg.content == "Test"


def test_thread_create():
    """测试 thread 创建"""
    thread = Thread.create("测试会话", current_cat_id="inky")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "inky"
    assert len(thread.id) == 8  # 短ID
    assert len(thread.messages) == 0
    assert thread.is_archived is False


def test_thread_add_message():
    """测试添加消息"""
    thread = Thread.create("Test")
    thread.add_message("user", "Hello")
    thread.add_message("assistant", "Hi", cat_id="orange")

    assert len(thread.messages) == 2
    assert thread.messages[0].role == "user"
    assert thread.messages[1].cat_id == "orange"


def test_thread_to_dict():
    """测试 thread 序列化"""
    thread = Thread.create("Test")
    thread.add_message("user", "Hello")
    data = thread.to_dict()

    assert data["name"] == "Test"
    assert data["current_cat_id"] == "orange"
    assert len(data["messages"]) == 1
    assert "id" in data


def test_thread_from_dict():
    """测试 thread 反序列化"""
    data = {
        "id": "abc123",
        "name": "Test Thread",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [
            {"role": "user", "content": "Hi", "cat_id": None, "timestamp": datetime.now().isoformat()}
        ],
        "current_cat_id": "patch",
        "is_archived": False
    }
    thread = Thread.from_dict(data)
    assert thread.id == "abc123"
    assert thread.name == "Test Thread"
    assert thread.current_cat_id == "patch"
    assert len(thread.messages) == 1
```

- [ ] **Step 4: 运行测试验证**

```bash
pytest tests/thread/test_models.py -v
```

Expected: 7 tests passing

- [ ] **Step 5: 提交**

```bash
git add src/thread/models.py tests/thread/test_models.py
git commit -m "feat: add Thread and Message models with serialization

- Message dataclass with role, content, cat_id, timestamp
- Thread dataclass with id, name, messages, current_cat_id
- to_dict/from_dict for JSON serialization
- Full test coverage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: JSON 持久化

**Files:**
- Create: `src/thread/persistence.py`
- Test: `tests/thread/test_persistence.py`

**Context:** 实现 thread 的 JSON 文件存储，保存到 `~/.meowai/threads.json`。

- [ ] **Step 1: 实现 Persistence 类**

```python
# src/thread/persistence.py
import json
from pathlib import Path
from typing import Dict, List
from src.thread.models import Thread


DEFAULT_STORAGE_PATH = Path.home() / ".meowai" / "threads.json"


class ThreadPersistence:
    """Thread JSON 持久化"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self._ensure_dir()

    def _ensure_dir(self):
        """确保存储目录存在"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, threads: Dict[str, Thread]) -> None:
        """保存所有 threads 到 JSON"""
        data = {
            "version": 1,
            "threads": {tid: t.to_dict() for tid, t in threads.items()}
        }
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> Dict[str, Thread]:
        """从 JSON 加载所有 threads"""
        if not self.storage_path.exists():
            return {}

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            threads = {}
            for tid, tdata in data.get("threads", {}).items():
                threads[tid] = Thread.from_dict(tdata)
            return threads
        except (json.JSONDecodeError, KeyError) as e:
            # 文件损坏，返回空
            print(f"Warning: Failed to load threads: {e}")
            return {}

    def exists(self) -> bool:
        """检查存储文件是否存在"""
        return self.storage_path.exists()
```

- [ ] **Step 2: 编写持久化测试**

```python
# tests/thread/test_persistence.py
import pytest
import tempfile
from pathlib import Path
from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence


def test_persistence_save_and_load():
    """测试保存和加载"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        persistence = ThreadPersistence(storage_path)

        # 创建 thread
        thread = Thread.create("测试会话", current_cat_id="orange")
        thread.add_message("user", "Hello")
        threads = {thread.id: thread}

        # 保存
        persistence.save(threads)
        assert persistence.exists()

        # 加载
        loaded = persistence.load()
        assert len(loaded) == 1
        assert thread.id in loaded
        assert loaded[thread.id].name == "测试会话"
        assert len(loaded[thread.id].messages) == 1


def test_persistence_load_empty():
    """测试加载不存在的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "nonexistent.json"
        persistence = ThreadPersistence(storage_path)

        loaded = persistence.load()
        assert loaded == {}
        assert not persistence.exists()


def test_persistence_multiple_threads():
    """测试多个 threads"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        persistence = ThreadPersistence(storage_path)

        t1 = Thread.create("会话1", current_cat_id="orange")
        t2 = Thread.create("会话2", current_cat_id="inky")
        threads = {t1.id: t1, t2.id: t2}

        persistence.save(threads)
        loaded = persistence.load()

        assert len(loaded) == 2
        assert loaded[t1.id].current_cat_id == "orange"
        assert loaded[t2.id].current_cat_id == "inky"


def test_persistence_corrupted_file():
    """测试损坏的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        storage_path.write_text("invalid json")
        persistence = ThreadPersistence(storage_path)

        loaded = persistence.load()
        assert loaded == {}  # 返回空而不是崩溃
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/thread/test_persistence.py -v
```

Expected: 4 tests passing

- [ ] **Step 4: 提交**

```bash
git add src/thread/persistence.py tests/thread/test_persistence.py
git commit -m "feat: add Thread JSON persistence

- ThreadPersistence class for save/load
- Store to ~/.meowai/threads.json
- Handle corrupted files gracefully
- Full test coverage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: ThreadManager 单例

**Files:**
- Create: `src/thread/thread_manager.py`
- Create: `src/thread/__init__.py`
- Test: `tests/thread/test_thread_manager.py`

**Context:** 实现 ThreadManager 单例，管理所有 thread 的生命周期和当前 thread。

- [ ] **Step 1: 创建 __init__.py**

```python
# src/thread/__init__.py
from src.thread.models import Message, Thread
from src.thread.thread_manager import ThreadManager

__all__ = ["Message", "Thread", "ThreadManager"]
```

- [ ] **Step 2: 实现 ThreadManager**

```python
# src/thread/thread_manager.py
from typing import Dict, List, Optional
from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence


class ThreadManager:
    """Thread 管理器（单例）"""

    _instance: Optional["ThreadManager"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ThreadManager._initialized:
            return

        self._threads: Dict[str, Thread] = {}
        self._current_thread_id: Optional[str] = None
        self._persistence = ThreadPersistence()

        # 从磁盘加载
        self._load()

        ThreadManager._initialized = True

    def _load(self):
        """从磁盘加载 threads"""
        self._threads = self._persistence.load()

    def _save(self):
        """保存到磁盘"""
        self._persistence.save(self._threads)

    def create(self, name: str, current_cat_id: str = "orange") -> Thread:
        """创建新 thread"""
        thread = Thread.create(name, current_cat_id)
        self._threads[thread.id] = thread
        self._save()
        return thread

    def get(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        return self._threads.get(thread_id)

    def list(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        threads = list(self._threads.values())
        if not include_archived:
            threads = [t for t in threads if not t.is_archived]
        # 按更新时间倒序
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)

    def switch(self, thread_id: str) -> bool:
        """切换到指定 thread"""
        if thread_id in self._threads:
            self._current_thread_id = thread_id
            return True
        return False

    def get_current(self) -> Optional[Thread]:
        """获取当前 thread"""
        if self._current_thread_id:
            return self._threads.get(self._current_thread_id)
        return None

    def rename(self, thread_id: str, new_name: str) -> bool:
        """重命名 thread"""
        if thread_id in self._threads:
            self._threads[thread_id].name = new_name
            self._threads[thread_id].updated_at = datetime.now()
            self._save()
            return True
        return False

    def delete(self, thread_id: str) -> bool:
        """删除 thread"""
        if thread_id in self._threads:
            del self._threads[thread_id]
            if self._current_thread_id == thread_id:
                self._current_thread_id = None
            self._save()
            return True
        return False

    def archive(self, thread_id: str) -> bool:
        """归档 thread"""
        if thread_id in self._threads:
            self._threads[thread_id].is_archived = True
            self._save()
            return True
        return False

    def update_thread(self, thread: Thread):
        """更新 thread（保存修改）"""
        if thread.id in self._threads:
            self._threads[thread.id] = thread
            self._save()

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
        cls._initialized = False


# 导入 datetime 用于 rename
from datetime import datetime
```

- [ ] **Step 3: 编写 ThreadManager 测试**

```python
# tests/thread/test_thread_manager.py
import pytest
import tempfile
from pathlib import Path
from src.thread.thread_manager import ThreadManager
from src.thread.persistence import ThreadPersistence


@pytest.fixture
def temp_manager():
    """创建使用临时存储的 ThreadManager"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        # 先重置单例
        ThreadManager.reset()
        manager = ThreadManager()
        manager._persistence = ThreadPersistence(storage_path)
        manager._threads = {}
        manager._current_thread_id = None
        yield manager
        ThreadManager.reset()


def test_singleton(temp_manager):
    """测试单例模式"""
    manager1 = temp_manager
    manager2 = ThreadManager()
    assert manager1 is manager2


def test_create_thread(temp_manager):
    """测试创建 thread"""
    thread = temp_manager.create("测试会话", current_cat_id="orange")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "orange"
    assert len(thread.id) == 8


def test_get_thread(temp_manager):
    """测试获取 thread"""
    thread = temp_manager.create("Test")
    fetched = temp_manager.get(thread.id)
    assert fetched is not None
    assert fetched.name == "Test"


def test_list_threads(temp_manager):
    """测试列出 threads"""
    temp_manager.create("Thread 1")
    temp_manager.create("Thread 2")
    threads = temp_manager.list()
    assert len(threads) == 2


def test_list_excludes_archived(temp_manager):
    """测试列出时排除归档"""
    t1 = temp_manager.create("Active")
    t2 = temp_manager.create("Archived")
    temp_manager.archive(t2.id)

    threads = temp_manager.list(include_archived=False)
    assert len(threads) == 1
    assert threads[0].name == "Active"


def test_switch_thread(temp_manager):
    """测试切换 thread"""
    t1 = temp_manager.create("Thread 1")
    t2 = temp_manager.create("Thread 2")

    assert temp_manager.switch(t1.id) is True
    assert temp_manager.get_current().id == t1.id

    assert temp_manager.switch(t2.id) is True
    assert temp_manager.get_current().id == t2.id


def test_switch_nonexistent(temp_manager):
    """测试切换到不存在的 thread"""
    assert temp_manager.switch("nonexistent") is False


def test_rename_thread(temp_manager):
    """测试重命名"""
    thread = temp_manager.create("Old Name")
    assert temp_manager.rename(thread.id, "New Name") is True
    assert temp_manager.get(thread.id).name == "New Name"


def test_delete_thread(temp_manager):
    """测试删除"""
    thread = temp_manager.create("To Delete")
    assert temp_manager.delete(thread.id) is True
    assert temp_manager.get(thread.id) is None


def test_delete_current_thread(temp_manager):
    """测试删除当前 thread"""
    thread = temp_manager.create("Current")
    temp_manager.switch(thread.id)
    temp_manager.delete(thread.id)
    assert temp_manager.get_current() is None


def test_archive_thread(temp_manager):
    """测试归档"""
    thread = temp_manager.create("To Archive")
    assert temp_manager.archive(thread.id) is True
    assert temp_manager.get(thread.id).is_archived is True
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/thread/test_thread_manager.py -v
```

Expected: 12 tests passing

- [ ] **Step 5: 提交**

```bash
git add src/thread/__init__.py src/thread/thread_manager.py tests/thread/test_thread_manager.py
git commit -m "feat: add ThreadManager singleton

- Singleton pattern for global thread management
- create/get/list/switch/rename/delete/archive methods
- Auto persistence on changes
- Reset method for test isolation
- Full test coverage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Thread CLI 命令

**Files:**
- Create: `src/cli/thread_commands.py`
- Modify: `src/cli/main.py` (添加 thread 命令组)

**Context:** 添加 `meowai thread` 命令组。

- [ ] **Step 1: 实现 Thread CLI**

```python
# src/cli/thread_commands.py
import click
from datetime import datetime
from src.thread import ThreadManager


def format_thread(thread, is_current=False):
    """格式化 thread 显示"""
    prefix = "* " if is_current else "  "
    status = " [已归档]" if thread.is_archived else ""
    msg_count = len(thread.messages)
    time_str = thread.updated_at.strftime("%m-%d %H:%M")
    return f"{prefix}{thread.id} | {thread.name}{status} | {msg_count}条消息 | {time_str}"


@click.group(name="thread")
def thread_cli():
    """Thread 多会话管理"""
    pass


@thread_cli.command(name="create")
@click.argument("name")
@click.option("--cat", default="@dev", help="默认使用的猫 (@dev/@review/@research)")
def create_thread(name, cat):
    """创建新 thread"""
    manager = ThreadManager()

    # 解析 cat mention
    cat_map = {"@dev": "orange", "@review": "inky", "@research": "patch"}
    cat_id = cat_map.get(cat, "orange")

    thread = manager.create(name, current_cat_id=cat_id)
    manager.switch(thread.id)  # 自动切换到新 thread

    click.echo(f"✅ 创建 thread: {thread.name} ({thread.id})")
    click.echo(f"   默认猫: {cat}")
    click.echo(f"   已自动切换到此 thread")


@thread_cli.command(name="list")
@click.option("--all", "-a", is_flag=True, help="显示所有 threads（包括归档）")
def list_threads(all):
    """列出所有 threads"""
    manager = ThreadManager()
    threads = manager.list(include_archived=all)
    current = manager.get_current()

    if not threads:
        click.echo("暂无 thread，使用 `meowai thread create <name>` 创建")
        return

    click.echo(f"\n{'ID':<10} {'名称':<20} {'状态':<10} {'消息数':<8} {'更新时间'}")
    click.echo("-" * 70)

    for thread in threads:
        current_mark = " *" if current and thread.id == current.id else ""
        status = "已归档" if thread.is_archived else "活跃"
        time_str = thread.updated_at.strftime("%m-%d %H:%M")
        click.echo(f"{thread.id}{current_mark:<3} {thread.name:<20} {status:<10} {len(thread.messages):<8} {time_str}")

    click.echo()


@thread_cli.command(name="switch")
@click.argument("thread_id")
def switch_thread(thread_id):
    """切换到指定 thread"""
    manager = ThreadManager()

    if manager.switch(thread_id):
        thread = manager.get_current()
        click.echo(f"✅ 已切换到: {thread.name} ({thread.id})")
        click.echo(f"   消息数: {len(thread.messages)}")
        click.echo(f"   默认猫: @{get_cat_mention(thread.current_cat_id)}")
    else:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        click.echo("   使用 `meowai thread list` 查看所有 threads")


@thread_cli.command(name="rename")
@click.argument("thread_id")
@click.argument("new_name")
def rename_thread(thread_id, new_name):
    """重命名 thread"""
    manager = ThreadManager()

    if manager.rename(thread_id, new_name):
        click.echo(f"✅ 已重命名为: {new_name}")
    else:
        click.echo(f"❌ Thread 不存在: {thread_id}")


@thread_cli.command(name="delete")
@click.argument("thread_id")
@click.option("--force", is_flag=True, help="强制删除，不提示")
def delete_thread(thread_id, force):
    """删除 thread"""
    manager = ThreadManager()
    thread = manager.get(thread_id)

    if not thread:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        return

    if not force:
        click.confirm(f"确定删除 thread '{thread.name}'? 此操作不可撤销。", abort=True)

    manager.delete(thread_id)
    click.echo(f"✅ 已删除: {thread.name}")


@thread_cli.command(name="archive")
@click.argument("thread_id")
def archive_thread(thread_id):
    """归档 thread"""
    manager = ThreadManager()
    thread = manager.get(thread_id)

    if not thread:
        click.echo(f"❌ Thread 不存在: {thread_id}")
        return

    manager.archive(thread_id)
    click.echo(f"✅ 已归档: {thread.name}")
    click.echo("   使用 `meowai thread list --all` 查看")


@thread_cli.command(name="info")
def thread_info():
    """显示当前 thread 信息"""
    manager = ThreadManager()
    thread = manager.get_current()

    if not thread:
        click.echo("当前没有活跃的 thread")
        click.echo("使用 `meowai thread create <name>` 创建，或 `meowai thread switch <id>` 切换")
        return

    click.echo(f"\n当前 Thread: {thread.name}")
    click.echo(f"  ID: {thread.id}")
    click.echo(f"  消息数: {len(thread.messages)}")
    click.echo(f"  默认猫: @{get_cat_mention(thread.current_cat_id)}")
    click.echo(f"  状态: {'已归档' if thread.is_archived else '活跃'}")
    click.echo(f"  创建时间: {thread.created_at.strftime('%Y-%m-%d %H:%M')}")
    click.echo(f"  更新时间: {thread.updated_at.strftime('%Y-%m-%d %H:%M')}")


def get_cat_mention(cat_id: str) -> str:
    """获取 cat 的 mention"""
    mention_map = {"orange": "dev", "inky": "review", "patch": "research"}
    return mention_map.get(cat_id, "dev")
```

- [ ] **Step 2: 修改 main.py 集成 thread 命令**

```python
# src/cli/main.py
import click
import asyncio
from src.router.agent_router import AgentRouter
from src.cli.thread_commands import thread_cli


@click.group()
@click.version_option(version='0.3.0', prog_name='meowai')
def cli():
    """MeowAI Home - 温馨的流浪猫AI收容所 🐱"""
    pass


# 注册 thread 命令
cli.add_command(thread_cli)


@cli.command()
@click.option('--cat', default='@dev', help='默认对话的猫猫（@dev/@review/@research）')
@click.option('--thread', 'thread_id', help='指定 thread ID（默认使用当前 thread）')
def chat(cat: str, thread_id: str = None):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()

    # 确定使用的 thread
    if thread_id:
        if not manager.switch(thread_id):
            click.echo(f"❌ Thread 不存在: {thread_id}")
            return

    thread = manager.get_current()
    if not thread:
        click.echo("🐱 还没有 thread，正在为你创建...")
        # 解析 cat
        cat_map = {"@dev": "orange", "@review": "inky", "@research": "patch"}
        cat_id = cat_map.get(cat, "orange")
        thread = manager.create("默认会话", current_cat_id=cat_id)
        manager.switch(thread.id)

    # 显示当前状态
    click.echo(f"\n🐱 当前 Thread: {thread.name}")
    click.echo(f"   默认猫: @{get_cat_mention(thread.current_cat_id)}")
    click.echo(f"   历史消息: {len(thread.messages)}条")
    click.echo("💡 提示：使用 @dev/@review/@research 指定猫猫，Ctrl+C 退出\n")

    # ... 原有 chat 逻辑，但使用 thread 的上下文
    # TODO: 在后续 task 中集成 thread 上下文


def get_cat_mention(cat_id: str) -> str:
    """获取 cat 的 mention"""
    mention_map = {"orange": "dev", "inky": "review", "patch": "research"}
    return mention_map.get(cat_id, "dev")


if __name__ == '__main__':
    cli()
```

- [ ] **Step 3: 运行测试验证 CLI**

```bash
python -m src.cli.main thread --help
python -m src.cli.main thread create "测试"
python -m src.cli.main thread list
```

- [ ] **Step 4: 提交**

```bash
git add src/cli/thread_commands.py src/cli/main.py
git commit -m "feat: add thread CLI commands

- thread create/list/switch/rename/delete/archive/info commands
- Auto-create thread if none exists on chat
- Show thread info in chat start
- Full thread management via CLI

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Chat 集成 Thread 上下文

**Files:**
- Modify: `src/cli/main.py` (重写 chat 命令)
- Modify: `src/cats/base.py` (如果需要)

**Context:** Chat 使用当前 thread 的消息历史作为上下文。

- [ ] **Step 1: 修改 chat 命令使用 thread 上下文**

```python
# src/cli/main.py - chat 命令更新

@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫（@dev/@review/@research）')
@click.option('--thread', 'thread_id', help='指定 thread ID')
def chat(cat: str, thread_id: str):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()
    router = AgentRouter()

    # 确定使用的 thread
    if thread_id:
        if not manager.switch(thread_id):
            click.echo(f"❌ Thread 不存在: {thread_id}")
            return
        thread = manager.get_current()
    else:
        thread = manager.get_current()
        if not thread:
            click.echo("🐱 还没有 thread，正在创建...")
            thread = manager.create("默认会话")
            manager.switch(thread.id)

    # 确定使用的猫
    cat_id = cat.lstrip('@') if cat else thread.current_cat_id

    # 显示状态
    click.echo(f"\n🐱 Thread: {thread.name} | 猫: @{cat_id}")
    click.echo(f"   历史: {len(thread.messages)}条消息")
    click.echo("   (按 Ctrl+C 退出)\n")

    try:
        while True:
            message = click.prompt("你", type=str)

            # 如果没有 @mention，添加默认
            if '@' not in message:
                message = f"@{cat_id} {message}"

            # 添加用户消息到 thread
            thread.add_message("user", message)

            # 路由消息
            try:
                agents = router.route_message(message)

                for agent_info in agents:
                    service = agent_info["service"]
                    name = agent_info["name"]
                    breed_id = agent_info["breed_id"]

                    click.echo(f"\n{name}: ", nl=False)

                    # 构建包含历史上下文的系统提示
                    system_prompt = build_thread_aware_prompt(
                        service, thread, breed_id
                    )

                    # 流式响应
                    async def stream_response():
                        chunks = []
                        async for chunk in service.chat_stream(message, system_prompt):
                            chunks.append(chunk)
                            click.echo(chunk, nl=False)
                        click.echo()
                        return "".join(chunks)

                    response = asyncio.run(stream_response())

                    # 添加猫回复到 thread
                    thread.add_message("assistant", response, cat_id=breed_id)
                    click.echo()

                # 保存 thread
                manager.update_thread(thread)

            except Exception as e:
                click.echo(f"\n❌ 错误: {str(e)}\n")

    except KeyboardInterrupt:
        click.echo(f"\n\n🐱 再见喵～对话已保存到 thread: {thread.name}\n")
        manager.update_thread(thread)


def build_thread_aware_prompt(service, thread, breed_id):
    """构建包含 thread 历史的系统提示"""
    base_prompt = service.build_system_prompt()

    if not thread.messages:
        return base_prompt

    # 添加历史上下文（最近 10 条）
    history_lines = ["\n## 对话历史"]
    for msg in thread.messages[-10:]:
        if msg.role == "user":
            history_lines.append(f"用户: {msg.content}")
        else:
            cat_name = msg.cat_id or "猫"
            history_lines.append(f"{cat_name}: {msg.content[:100]}...")

    return base_prompt + "\n" + "\n".join(history_lines)
```

- [ ] **Step 2: 运行集成测试**

```bash
python -m src.cli.main thread create "测试会话"
python -m src.cli.main chat
# 输入几条消息
# Ctrl+C 退出
python -m src.cli.main thread info
# 验证消息已保存
```

- [ ] **Step 3: 提交**

```bash
git add src/cli/main.py
git commit -m "feat: integrate thread context into chat

- Chat uses current thread's message history
- Build thread-aware system prompt with recent context
- Auto-save messages to thread after each turn
- Persist on exit (Ctrl+C)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 集成测试和文档

**Files:**
- Create: `tests/integration/test_thread_cli.py`
- Modify: `README.md`

- [ ] **Step 1: 编写集成测试**

```python
# tests/integration/test_thread_cli.py
import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from src.cli.main import cli
from src.thread import ThreadManager


@pytest.fixture
def isolated_env():
    """隔离的测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        ThreadManager.reset()
        manager = ThreadManager()
        manager._persistence.storage_path = storage_path
        manager._threads = {}
        manager._current_thread_id = None

        runner = CliRunner()
        yield runner, manager

        ThreadManager.reset()


def test_thread_create(isolated_env):
    """测试创建 thread"""
    runner, manager = isolated_env
    result = runner.invoke(cli, ['thread', 'create', 'Test Thread'])

    assert result.exit_code == 0
    assert "创建 thread" in result.output
    assert len(manager.list()) == 1


def test_thread_list(isolated_env):
    """测试列出 threads"""
    runner, manager = isolated_env
    manager.create("Thread 1")
    manager.create("Thread 2")

    result = runner.invoke(cli, ['thread', 'list'])
    assert result.exit_code == 0
    assert "Thread 1" in result.output
    assert "Thread 2" in result.output


def test_thread_switch(isolated_env):
    """测试切换 thread"""
    runner, manager = isolated_env
    thread = manager.create("Test")

    result = runner.invoke(cli, ['thread', 'switch', thread.id])
    assert result.exit_code == 0
    assert "已切换到" in result.output
    assert manager.get_current().id == thread.id


def test_thread_delete(isolated_env):
    """测试删除 thread"""
    runner, manager = isolated_env
    thread = manager.create("To Delete")

    result = runner.invoke(cli, ['thread', 'delete', thread.id, '--force'])
    assert result.exit_code == 0
    assert "已删除" in result.output
    assert manager.get(thread.id) is None
```

- [ ] **Step 2: 运行所有测试**

```bash
pytest tests/thread/ tests/integration/test_thread_cli.py -v
```

Expected: 所有测试通过

- [ ] **Step 3: 更新 README**

```markdown
## Thread 多会话管理

支持多个独立对话线程，每个 thread 有自己的上下文历史：

```bash
# Thread 管理
meowai thread create "项目A" [--cat @dev]   # 创建 thread
meowai thread list                          # 列出 threads
meowai thread switch <id>                   # 切换 thread
meowai thread rename <id> "新名称"          # 重命名
meowai thread archive <id>                  # 归档
meowai thread delete <id> [--force]         # 删除
meowai thread info                          # 当前 thread 信息

# 对话（使用当前 thread）
meowai chat                                 # 进入交互模式
meowai chat --thread <id>                   # 使用指定 thread
```
```

- [ ] **Step 4: 最终提交**

```bash
git add tests/integration/test_thread_cli.py README.md
git commit -m "test: add thread integration tests and docs

- Integration tests for thread CLI commands
- Update README with thread management features
- Phase 3.1 complete

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 实施总结

| Task | 描述 | 文件 | 测试 |
|------|------|------|------|
| 3.1.1 | Thread 数据模型 | `src/thread/models.py` | 7 tests |
| 3.1.2 | JSON 持久化 | `src/thread/persistence.py` | 4 tests |
| 3.1.3 | ThreadManager | `src/thread/thread_manager.py` | 12 tests |
| 3.1.4 | CLI 命令 | `src/cli/thread_commands.py` | - |
| 3.1.5 | Chat 集成 | `src/cli/main.py` | - |
| 3.1.6 | 集成测试 | `tests/integration/test_thread_cli.py` | 4 tests |

**总计**: ~27 个测试，预计实施时间 6-8 小时。

---

**实施选项**:

1. **Subagent-Driven (推荐)** - 每个 task 独立子代理 + 两阶段审查
2. **Inline Execution** - 本会话内批量执行

选择后使用对应的 skill 开始实施。
