# Phase 3.2: 会话持久化与恢复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 SQLite 持久化存储，支持 `--resume` 恢复会话和历史搜索。

**Architecture:** 将 JSON 存储迁移到 SQLite，使用 aiosqlite 支持异步操作，添加 MessageStore 和 ThreadStore 接口，支持消息分页查询和全文搜索。

**Tech Stack:** Python 3.9+, aiosqlite, sqlite3, pytest-asyncio

---

## 文件结构

| 文件 | 责任 |
|------|------|
| `src/thread/stores/base.py` | Store 抽象接口 |
| `src/thread/stores/sqlite_store.py` | SQLite 实现 |
| `src/thread/stores/migration.py` | JSON 到 SQLite 迁移 |
| `src/thread/stores/__init__.py` | 导出 |
| `tests/thread/stores/test_sqlite_store.py` | Store 测试 |
| `src/cli/main.py` | 添加 `--resume` 选项 |

---

## Task 1: SQLite Store 接口

**Files:**
- Create: `src/thread/stores/base.py`
- Create: `src/thread/stores/__init__.py`

**Context:** 定义 Store 抽象接口，用于替换现有的 JSON 持久化。

- [ ] **Step 1: 创建目录**

```bash
mkdir -p src/thread/stores tests/thread/stores
```

- [ ] **Step 2: 实现抽象接口**

Create `src/thread/stores/base.py`:

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from src.thread.models import Thread, Message


class ThreadStore(ABC):
    """Thread 存储抽象接口"""

    @abstractmethod
    async def save_thread(self, thread: Thread) -> None:
        """保存或更新 thread"""
        pass

    @abstractmethod
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        pass

    @abstractmethod
    async def list_threads(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        pass

    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """删除 thread"""
        pass

    @abstractmethod
    async def search_threads(self, query: str) -> List[Thread]:
        """搜索 threads"""
        pass


class MessageStore(ABC):
    """Message 存储抽象接口"""

    @abstractmethod
    async def add_message(self, thread_id: str, message: Message) -> None:
        """添加消息"""
        pass

    @abstractmethod
    async def get_messages(self, thread_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """分页获取消息"""
        pass

    @abstractmethod
    async def search_messages(self, thread_id: str, query: str) -> List[Message]:
        """搜索消息内容"""
        pass
```

- [ ] **Step 3: 创建 init 文件**

Create `src/thread/stores/__init__.py`:

```python
from src.thread.stores.base import ThreadStore, MessageStore

__all__ = ["ThreadStore", "MessageStore"]
```

- [ ] **Step 4: 提交**

```bash
git add src/thread/stores/
git commit -m "feat: add ThreadStore and MessageStore abstract interfaces

- Define base interfaces for persistence layer
- Support async operations
- Include search capabilities

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: SQLite Store 实现

**Files:**
- Create: `src/thread/stores/sqlite_store.py`
- Test: `tests/thread/stores/test_sqlite_store.py`

**Context:** 实现基于 SQLite 的存储，替换 JSON 持久化。

- [ ] **Step 1: 实现 SQLiteStore**

Create `src/thread/stores/sqlite_store.py`:

```python
import json
import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.thread.models import Thread, Message
from src.thread.stores.base import ThreadStore, MessageStore

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"


class SQLiteStore(ThreadStore, MessageStore):
    """SQLite 存储实现"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_dir()

    def _ensure_dir(self):
        """确保目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_db(self):
        """获取数据库连接"""
        return await aiosqlite.connect(self.db_path)

    async def initialize(self):
        """初始化数据库表"""
        async with await self._get_db() as db:
            # Threads 表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    current_cat_id TEXT NOT NULL,
                    is_archived INTEGER DEFAULT 0
                )
            """)

            # Messages 表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    cat_id TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
                )
            """)

            # 索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_thread
                ON messages(thread_id, timestamp)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_threads_updated
                ON threads(updated_at DESC)
            """)

            await db.commit()

    async def save_thread(self, thread: Thread) -> None:
        """保存 thread"""
        async with await self._get_db() as db:
            await db.execute("""
                INSERT OR REPLACE INTO threads
                (id, name, created_at, updated_at, current_cat_id, is_archived)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                thread.id,
                thread.name,
                thread.created_at.isoformat(),
                thread.updated_at.isoformat(),
                thread.current_cat_id,
                1 if thread.is_archived else 0
            ))
            await db.commit()

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """获取 thread"""
        async with await self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM threads WHERE id = ?", (thread_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            # 获取消息
            messages = await self.get_messages(thread_id, limit=10000)

            return Thread(
                id=row[0],
                name=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3]),
                current_cat_id=row[4],
                is_archived=bool(row[5]),
                messages=messages
            )

    async def list_threads(self, include_archived: bool = False) -> List[Thread]:
        """列出 threads"""
        async with await self._get_db() as db:
            if include_archived:
                cursor = await db.execute(
                    "SELECT * FROM threads ORDER BY updated_at DESC"
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM threads WHERE is_archived = 0 ORDER BY updated_at DESC"
                )

            rows = await cursor.fetchall()
            threads = []

            for row in rows:
                thread_id = row[0]
                messages = await self.get_messages(thread_id, limit=100)

                threads.append(Thread(
                    id=row[0],
                    name=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                    updated_at=datetime.fromisoformat(row[3]),
                    current_cat_id=row[4],
                    is_archived=bool(row[5]),
                    messages=messages
                ))

            return threads

    async def delete_thread(self, thread_id: str) -> bool:
        """删除 thread（级联删除消息）"""
        async with await self._get_db() as db:
            await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
            await db.commit()
            return True

    async def search_threads(self, query: str) -> List[Thread]:
        """搜索 thread 名称"""
        async with await self._get_db() as db:
            cursor = await db.execute(
                "SELECT * FROM threads WHERE name LIKE ? ORDER BY updated_at DESC",
                (f"%{query}%",)
            )
            rows = await cursor.fetchall()
            # ... 类似 list_threads 构建 Thread 对象
            threads = []
            for row in rows:
                thread_id = row[0]
                messages = await self.get_messages(thread_id, limit=100)
                threads.append(Thread(
                    id=row[0],
                    name=row[1],
                    created_at=datetime.fromisoformat(row[2]),
                    updated_at=datetime.fromisoformat(row[3]),
                    current_cat_id=row[4],
                    is_archived=bool(row[5]),
                    messages=messages
                ))
            return threads

    async def add_message(self, thread_id: str, message: Message) -> None:
        """添加消息"""
        async with await self._get_db() as db:
            await db.execute("""
                INSERT INTO messages (thread_id, role, content, cat_id, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                thread_id,
                message.role,
                message.content,
                message.cat_id,
                message.timestamp.isoformat()
            ))
            await db.commit()

    async def get_messages(self, thread_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """分页获取消息"""
        async with await self._get_db() as db:
            cursor = await db.execute(
                """SELECT role, content, cat_id, timestamp FROM messages
                   WHERE thread_id = ?
                   ORDER BY timestamp ASC
                   LIMIT ? OFFSET ?""",
                (thread_id, limit, offset)
            )
            rows = await cursor.fetchall()

            return [
                Message(
                    role=row[0],
                    content=row[1],
                    cat_id=row[2],
                    timestamp=datetime.fromisoformat(row[3])
                )
                for row in rows
            ]

    async def search_messages(self, thread_id: str, query: str) -> List[Message]:
        """搜索消息内容"""
        async with await self._get_db() as db:
            cursor = await db.execute(
                """SELECT role, content, cat_id, timestamp FROM messages
                   WHERE thread_id = ? AND content LIKE ?
                   ORDER BY timestamp ASC""",
                (thread_id, f"%{query}%")
            )
            rows = await cursor.fetchall()

            return [
                Message(
                    role=row[0],
                    content=row[1],
                    cat_id=row[2],
                    timestamp=datetime.fromisoformat(row[3])
                )
                for row in rows
            ]
```

- [ ] **Step 2: 编写测试**

Create `tests/thread/stores/test_sqlite_store.py`:

```python
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.thread.models import Thread, Message
from src.thread.stores.sqlite_store import SQLiteStore


@pytest.fixture
async def store():
    """创建临时 store"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SQLiteStore(db_path)
        await store.initialize()
        yield store


@pytest.mark.asyncio
async def test_save_and_get_thread(store):
    """测试保存和获取 thread"""
    thread = Thread.create("测试", current_cat_id="orange")
    await store.save_thread(thread)

    fetched = await store.get_thread(thread.id)
    assert fetched is not None
    assert fetched.name == "测试"
    assert fetched.current_cat_id == "orange"


@pytest.mark.asyncio
async def test_list_threads(store):
    """测试列出 threads"""
    t1 = Thread.create("Thread 1")
    t2 = Thread.create("Thread 2")
    await store.save_thread(t1)
    await store.save_thread(t2)

    threads = await store.list_threads()
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_add_and_get_messages(store):
    """测试消息存储"""
    thread = Thread.create("Test")
    await store.save_thread(thread)

    msg = Message(role="user", content="Hello", cat_id=None)
    await store.add_message(thread.id, msg)

    messages = await store.get_messages(thread.id)
    assert len(messages) == 1
    assert messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_search_messages(store):
    """测试消息搜索"""
    thread = Thread.create("Test")
    await store.save_thread(thread)

    await store.add_message(thread.id, Message(role="user", content="Hello world"))
    await store.add_message(thread.id, Message(role="assistant", content="Goodbye"))

    results = await store.search_messages(thread.id, "Hello")
    assert len(results) == 1
    assert results[0].content == "Hello world"
```

- [ ] **Step 3: 安装依赖并运行测试**

```bash
pip install aiosqlite pytest-asyncio
```

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

```bash
pytest tests/thread/stores/test_sqlite_store.py -v
```

Expected: 4 tests passing

- [ ] **Step 4: 提交**

```bash
git add src/thread/stores/ tests/thread/stores/ pyproject.toml
git commit -m "feat: add SQLite store implementation

- SQLiteStore with ThreadStore and MessageStore interfaces
- Async operations with aiosqlite
- Message pagination and search
- Full test coverage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: JSON 到 SQLite 迁移

**Files:**
- Create: `src/thread/stores/migration.py`
- Create: `tests/thread/stores/test_migration.py`

**Context:** 从 JSON 文件迁移数据到 SQLite。

- [ ] **Step 1: 实现迁移工具**

Create `src/thread/stores/migration.py`:

```python
import json
from pathlib import Path
from typing import Optional

from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence
from src.thread.stores.sqlite_store import SQLiteStore


async def migrate_json_to_sqlite(
    json_path: Optional[Path] = None,
    sqlite_path: Optional[Path] = None
) -> int:
    """从 JSON 迁移到 SQLite

    Returns:
        迁移的 thread 数量
    """
    # 加载 JSON
    json_store = ThreadPersistence(json_path)
    threads = json_store.load()

    if not threads:
        return 0

    # 初始化 SQLite
    sqlite_store = SQLiteStore(sqlite_path)
    await sqlite_store.initialize()

    # 迁移每个 thread
    count = 0
    for thread in threads.values():
        await sqlite_store.save_thread(thread)
        # 迁移消息
        for msg in thread.messages:
            await sqlite_store.add_message(thread.id, msg)
        count += 1

    return count


def check_needs_migration(sqlite_path: Path = None) -> bool:
    """检查是否需要迁移"""
    sqlite_path = sqlite_path or SQLiteStore().db_path
    json_path = ThreadPersistence().storage_path

    # 如果 SQLite 不存在但 JSON 存在，需要迁移
    return not sqlite_path.exists() and json_path.exists()
```

- [ ] **Step 2: 编写测试**

Create `tests/thread/stores/test_migration.py`:

```python
import pytest
import tempfile
from pathlib import Path

from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence
from src.thread.stores.sqlite_store import SQLiteStore
from src.thread.stores.migration import migrate_json_to_sqlite


@pytest.mark.asyncio
async def test_migration():
    """测试数据迁移"""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "threads.json"
        sqlite_path = Path(tmpdir) / "meowai.db"

        # 创建 JSON 数据
        store = ThreadPersistence(json_path)
        thread = Thread.create("Test Thread", current_cat_id="orange")
        thread.add_message("user", "Hello")
        store.save({thread.id: thread})

        # 迁移
        count = await migrate_json_to_sqlite(json_path, sqlite_path)
        assert count == 1

        # 验证 SQLite 数据
        sqlite_store = SQLiteStore(sqlite_path)
        await sqlite_store.initialize()

        migrated = await sqlite_store.get_thread(thread.id)
        assert migrated.name == "Test Thread"
        assert len(migrated.messages) == 1
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/thread/stores/test_migration.py -v
```

- [ ] **Step 4: 提交**

```bash
git add src/thread/stores/migration.py tests/thread/stores/test_migration.py
git commit -m "feat: add JSON to SQLite migration

- migrate_json_to_sqlite function
- check_needs_migration helper
- Data migration with message history

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: ThreadManager 适配 SQLite

**Files:**
- Modify: `src/thread/thread_manager.py`
- Modify: `tests/thread/test_thread_manager.py`

**Context:** 修改 ThreadManager 使用 SQLite 而不是 JSON。

- [ ] **Step 1: 修改 ThreadManager**

Modify `src/thread/thread_manager.py`:

```python
from typing import Dict, List, Optional
from datetime import datetime, timezone
import asyncio

from src.thread.models import Thread
from src.thread.stores.sqlite_store import SQLiteStore
from src.thread.stores.migration import check_needs_migration, migrate_json_to_sqlite


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

        self._store = SQLiteStore()
        self._current_thread_id: Optional[str] = None

        # 初始化数据库
        asyncio.run(self._init_db())

        ThreadManager._initialized = True

    async def _init_db(self):
        """初始化数据库"""
        # 检查是否需要迁移
        if check_needs_migration():
            print("🔄 正在从旧格式迁移数据...")
            count = await migrate_json_to_sqlite()
            print(f"✅ 已迁移 {count} 个 threads")

        await self._store.initialize()

    async def create(self, name: str, current_cat_id: str = "orange") -> Thread:
        """创建新 thread"""
        thread = Thread.create(name, current_cat_id)
        await self._store.save_thread(thread)
        return thread

    async def get(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        return await self._store.get_thread(thread_id)

    async def list(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        return await self._store.list_threads(include_archived)

    def switch(self, thread_id: str) -> bool:
        """切换到指定 thread"""
        # 简化为同步检查
        self._current_thread_id = thread_id
        return True

    def get_current(self) -> Optional[Thread]:
        """获取当前 thread"""
        if self._current_thread_id:
            # 异步获取
            return asyncio.run(self._store.get_thread(self._current_thread_id))
        return None

    async def rename(self, thread_id: str, new_name: str) -> bool:
        """重命名 thread"""
        thread = await self._store.get_thread(thread_id)
        if thread:
            thread.name = new_name
            thread.updated_at = datetime.now(timezone.utc)
            await self._store.save_thread(thread)
            return True
        return False

    async def delete(self, thread_id: str) -> bool:
        """删除 thread"""
        if self._current_thread_id == thread_id:
            self._current_thread_id = None
        return await self._store.delete_thread(thread_id)

    async def archive(self, thread_id: str) -> bool:
        """归档 thread"""
        thread = await self._store.get_thread(thread_id)
        if thread:
            thread.is_archived = True
            await self._store.save_thread(thread)
            return True
        return False

    async def update_thread(self, thread: Thread):
        """更新 thread"""
        await self._store.save_thread(thread)
        # 更新消息
        for msg in thread.messages:
            await self._store.add_message(thread.id, msg)

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
        cls._initialized = False
```

- [ ] **Step 2: 更新测试**（适配 async）

- [ ] **Step 3: 提交**

```bash
git add src/thread/thread_manager.py tests/thread/test_thread_manager.py
git commit -m "refactor: ThreadManager uses SQLite backend

- Replace JSON persistence with SQLite
- Auto-migration from JSON on first run
- Async operations for all methods

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 添加 `--resume` 选项

**Files:**
- Modify: `src/cli/main.py`
- Modify: `src/cli/thread_commands.py`

**Context:** 添加 `--resume` 恢复上次会话。

- [ ] **Step 1: 添加 resume 逻辑**

Add to `src/cli/main.py`:

```python
@cli.command()
@click.option('--cat', default=None, help='覆盖默认猫')
@click.option('--thread', 'thread_id', help='指定 thread ID')
@click.option('--resume', is_flag=True, help='恢复上次会话')
def chat(cat: str, thread_id: str, resume: bool):
    """与猫猫开始对话"""
    from src.thread import ThreadManager

    manager = ThreadManager()
    # ... existing code

    if resume:
        # 获取最近的 thread
        threads = asyncio.run(manager.list())
        if threads:
            thread = threads[0]
            manager.switch(thread.id)
            click.echo(f"🔄 恢复会话: {thread.name}")
        else:
            click.echo("暂无历史会话，创建新 thread")
            thread = asyncio.run(manager.create("默认会话"))
            manager.switch(thread.id)
```

- [ ] **Step 2: 提交**

```bash
git add src/cli/main.py
git commit -m "feat: add --resume option to chat command

- Resume last conversation with --resume
- Auto-create if no history exists

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 集成测试和最终提交

**Files:**
- Create: `tests/integration/test_sqlite_persistence.py`
- Modify: `README.md`

- [ ] **Step 1: 编写集成测试**

- [ ] **Step 2: 更新 README**

Add to README:
```markdown
## 会话持久化 (Phase 3.2)

- 数据存储在 SQLite (`~/.meowai/meowai.db`)
- 自动从 JSON 格式迁移
- 支持消息搜索

```bash
meowai chat --resume  # 恢复上次会话
```
```

- [ ] **Step 3: 运行所有测试**

```bash
pytest tests/thread/ tests/integration/ -v
```

- [ ] **Step 4: 提交并打标签**

```bash
git add tests/integration/test_sqlite_persistence.py README.md
git commit -m "test: add Phase 3.2 integration tests

- SQLite persistence tests
- Migration tests
- Updated README

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"

git tag -a v0.3.1 -m "Release v0.3.1 - Phase 3.2 SQLite Persistence"
```

---

## 实施总结

| Task | 描述 | 预估时间 |
|------|------|----------|
| 3.2.1 | SQLite Store 接口 | 30 分钟 |
| 3.2.2 | SQLite Store 实现 | 1.5 小时 |
| 3.2.3 | JSON 到 SQLite 迁移 | 45 分钟 |
| 3.2.4 | ThreadManager 适配 | 1 小时 |
| 3.2.5 | `--resume` 选项 | 30 分钟 |
| 3.2.6 | 集成测试和文档 | 45 分钟 |

**总计**: ~5 小时

---

**执行选项:**

1. **Subagent-Driven (推荐)** - 每个 task 独立子代理
2. **Inline Execution** - 本会话内批量执行

选择后使用对应的 skill 开始实施。
