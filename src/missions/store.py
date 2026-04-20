"""SQLite-backed Mission Store for task-project linking."""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"


class MissionStore:
    """Persistent SQLite store for mission tasks."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA foreign_keys = ON")
        return self._db

    async def initialize(self):
        """Initialize the missions table."""
        db = await self._get_db()
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS missions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'backlog',
                priority TEXT DEFAULT 'P2',
                ownerCat TEXT,
                tags TEXT DEFAULT '[]',
                createdAt TEXT,
                dueDate TEXT,
                progress INTEGER,
                thread_ids TEXT DEFAULT '[]',
                workflow_id TEXT,
                session_ids TEXT DEFAULT '[]',
                pr_url TEXT,
                branch TEXT,
                commit_hash TEXT,
                worktree_path TEXT,
                last_activity_at REAL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status)"
        )
        # Migrate from legacy thread_id column if present
        await self._migrate_thread_ids(db)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_missions_threads ON missions(thread_ids)"
        )
        await db.commit()

    async def _migrate_thread_ids(self, db: aiosqlite.Connection):
        """Migrate legacy thread_id to thread_ids JSON array."""
        cursor = await db.execute("PRAGMA table_info(missions)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "thread_ids" not in columns and "thread_id" in columns:
            await db.execute("ALTER TABLE missions ADD COLUMN thread_ids TEXT DEFAULT '[]'")
            # Migrate existing data
            cursor2 = await db.execute("SELECT id, thread_id FROM missions WHERE thread_id IS NOT NULL AND thread_id != ''")
            rows = await cursor2.fetchall()
            for task_id, thread_id in rows:
                await db.execute(
                    "UPDATE missions SET thread_ids = ? WHERE id = ?",
                    (json.dumps([thread_id], ensure_ascii=False), task_id),
                )
            await db.commit()

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "title": row[1],
            "description": row[2] or "",
            "status": row[3] or "backlog",
            "priority": row[4] or "P2",
            "ownerCat": row[5] or None,
            "tags": json.loads(row[6]) if row[6] else [],
            "createdAt": row[7] or "",
            "dueDate": row[8] or None,
            "progress": row[9] if row[9] is not None else None,
            "thread_ids": json.loads(row[10]) if row[10] else [],
            "workflow_id": row[11] or None,
            "session_ids": json.loads(row[12]) if row[12] else [],
            "pr_url": row[13] or None,
            "branch": row[14] or None,
            "commit_hash": row[15] or None,
            "worktree_path": row[16] or None,
            "last_activity_at": row[17] or None,
        }

    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new task."""
        db = await self._get_db()
        now = datetime.now().strftime("%Y-%m-%d")
        task_id = task_data.get("id") or self._gen_id()
        row = (
            task_id,
            task_data["title"],
            task_data.get("description", ""),
            task_data.get("status", "backlog"),
            task_data.get("priority", "P2"),
            task_data.get("ownerCat"),
            json.dumps(task_data.get("tags", []), ensure_ascii=False),
            task_data.get("createdAt") or now,
            task_data.get("dueDate"),
            task_data.get("progress"),
            json.dumps(task_data.get("thread_ids", []), ensure_ascii=False),
            task_data.get("workflow_id"),
            json.dumps(task_data.get("session_ids", []), ensure_ascii=False),
            task_data.get("pr_url"),
            task_data.get("branch"),
            task_data.get("commit_hash"),
            task_data.get("worktree_path"),
            task_data.get("last_activity_at"),
        )
        await db.execute(
            """
            INSERT INTO missions
            (id, title, description, status, priority, ownerCat, tags, createdAt,
             dueDate, progress, thread_ids, workflow_id, session_ids, pr_url,
             branch, commit_hash, worktree_path, last_activity_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        await db.commit()
        return self._row_to_dict((task_id, *row[1:]))

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return self._row_to_dict(row) if row else None

    async def get_tasks_by_thread(self, thread_id: str) -> List[Dict[str, Any]]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM missions WHERE thread_ids LIKE ?", (f'%"{thread_id}"%',)
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        db = await self._get_db()
        allowed = {
            "title",
            "description",
            "status",
            "priority",
            "ownerCat",
            "tags",
            "dueDate",
            "progress",
            "thread_ids",
            "workflow_id",
            "session_ids",
            "pr_url",
            "branch",
            "commit_hash",
            "worktree_path",
            "last_activity_at",
        }
        fields = []
        values = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key in ("tags", "session_ids", "thread_ids"):
                value = json.dumps(value, ensure_ascii=False)
            fields.append(f"{key} = ?")
            values.append(value)
        if not fields:
            return await self.get_task(task_id)
        values.append(task_id)
        await db.execute(
            f"UPDATE missions SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()
        return await self.get_task(task_id)

    async def delete_task(self, task_id: str) -> bool:
        db = await self._get_db()
        cursor = await db.execute("DELETE FROM missions WHERE id = ?", (task_id,))
        await db.commit()
        return cursor.rowcount > 0

    async def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        db = await self._get_db()
        where = []
        params = []
        if status:
            where.append("status = ?")
            params.append(status)
        if priority:
            where.append("priority = ?")
            params.append(priority)
        if tag:
            where.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        sql = "SELECT * FROM missions"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY createdAt DESC"
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    async def bind_thread(self, task_id: str, thread_id: str) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        thread_ids = task.get("thread_ids", [])
        if thread_id not in thread_ids:
            thread_ids.append(thread_id)
        await self.update_task(
            task_id, {"thread_ids": thread_ids, "last_activity_at": datetime.now().timestamp()}
        )
        return True

    async def bind_session(self, task_id: str, session_id: str) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        session_ids = task.get("session_ids", [])
        if session_id not in session_ids:
            session_ids.append(session_id)
        await self.update_task(
            task_id, {"session_ids": session_ids, "last_activity_at": datetime.now().timestamp()}
        )
        return True

    async def update_artifact(
        self,
        task_id: str,
        branch: Optional[str] = None,
        commit_hash: Optional[str] = None,
        pr_url: Optional[str] = None,
    ) -> bool:
        task = await self.get_task(task_id)
        if not task:
            return False
        updates: Dict[str, Any] = {"last_activity_at": datetime.now().timestamp()}
        if branch is not None:
            updates["branch"] = branch
        if commit_hash is not None:
            updates["commit_hash"] = commit_hash
        if pr_url is not None:
            updates["pr_url"] = pr_url
        await self.update_task(task_id, updates)
        return True

    async def list_active_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        db = await self._get_db()
        cursor = await db.execute(
            "SELECT * FROM missions WHERE status IN ('todo', 'doing') ORDER BY last_activity_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _gen_id(self) -> str:
        import uuid

        return str(uuid.uuid4())[:8]
