import aiosqlite
import json
from datetime import datetime
from typing import Optional
from .models import Thread, Message, Role


class ThreadStore:
    def __init__(self, db_path: str = "data/threads.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._create_tables()
        return self._db

    async def _create_tables(self):
        db = await self._get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES threads (id)
            )
        """)
        await db.commit()

    async def save_thread(self, thread: Thread):
        db = await self._get_db()
        try:
            await db.execute(
                "INSERT OR REPLACE INTO threads (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (thread.id, thread.title, thread.created_at.isoformat(), thread.updated_at.isoformat())
            )
            await db.execute("DELETE FROM messages WHERE thread_id = ?", (thread.id,))
            for msg in thread.messages:
                await db.execute(
                    "INSERT INTO messages (id, thread_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (msg.id, thread.id, msg.role.value, msg.content, msg.timestamp.isoformat())
                )
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT id, title, created_at, updated_at FROM threads WHERE id = ?",
            (thread_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        try:
            thread = Thread(
                id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3])
            )
        except (ValueError, TypeError):
            return None

        cursor = await db.execute(
            "SELECT id, role, content, timestamp FROM messages WHERE thread_id = ? ORDER BY timestamp",
            (thread_id,)
        )
        async for row in cursor:
            try:
                msg = Message(
                    id=row[0],
                    role=Role(row[1]),
                    content=row[2],
                    timestamp=datetime.fromisoformat(row[3])
                )
                thread.messages.append(msg)
            except (ValueError, TypeError):
                # Skip malformed messages
                continue

        return thread

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
