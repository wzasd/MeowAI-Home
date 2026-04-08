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
        self._db: Optional[aiosqlite.Connection] = None

    def _ensure_dir(self):
        """确保存储目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _get_db(self) -> aiosqlite.Connection:
        """获取数据库连接（单例模式）"""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            # 启用外键约束
            await self._db.execute("PRAGMA foreign_keys = ON")
        return self._db

    async def initialize(self):
        """初始化数据库表"""
        db = await self._get_db()

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

    async def close(self):
        """关闭数据库连接"""
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def save_thread(self, thread: Thread) -> None:
        """保存 thread"""
        db = await self._get_db()
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
        db = await self._get_db()
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
        db = await self._get_db()

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
        """删除 thread"""
        db = await self._get_db()
        await db.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
        await db.commit()
        return True

    async def search_threads(self, query: str) -> List[Thread]:
        """搜索 thread 名称"""
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM threads WHERE name LIKE ? ORDER BY updated_at DESC",
            (f"%{query}%",)
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

    async def add_message(self, thread_id: str, message: Message) -> None:
        """添加消息"""
        db = await self._get_db()
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
        db = await self._get_db()
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
        db = await self._get_db()
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
