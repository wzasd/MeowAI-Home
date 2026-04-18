"""Tasks API routes for task management (SQLite-backed)."""
import aiosqlite
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from pathlib import Path
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS thread_tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'todo',
    ownerCat TEXT,
    description TEXT,
    threadId TEXT,
    createdAt TEXT
);
CREATE INDEX IF NOT EXISTS idx_thread_tasks_thread ON thread_tasks(threadId);
CREATE INDEX IF NOT EXISTS idx_thread_tasks_status ON thread_tasks(status);
"""


async def _get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DEFAULT_DB_PATH)
    await db.executescript(_INIT_SQL)
    return db


class TaskItem(BaseModel):
    id: str = ""
    title: str
    status: Literal["todo", "doing", "blocked", "done"]
    ownerCat: Optional[str] = None
    description: Optional[str] = None
    threadId: Optional[str] = None
    createdAt: str = ""


@router.get("/entries")
async def list_tasks(threadId: Optional[str] = None):
    """Get tasks, optionally filtered by thread."""
    db = await _get_db()
    sql = "SELECT id, title, status, ownerCat, description, threadId, createdAt FROM thread_tasks"
    params = []
    if threadId:
        sql += " WHERE threadId = ?"
        params.append(threadId)
    sql += " ORDER BY createdAt DESC"
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    await db.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "ownerCat": row[3],
            "description": row[4],
            "threadId": row[5],
            "createdAt": row[6],
        }
        for row in rows
    ]


@router.post("/entries")
async def create_task(task: TaskItem):
    """Create a new task."""
    if not task.id:
        task.id = str(uuid.uuid4())[:8]
    if not task.createdAt:
        task.createdAt = datetime.now().isoformat()

    db = await _get_db()
    await db.execute(
        """
        INSERT INTO thread_tasks (id, title, status, ownerCat, description, threadId, createdAt)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (task.id, task.title, task.status, task.ownerCat, task.description, task.threadId, task.createdAt),
    )
    await db.commit()
    await db.close()
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status,
        "ownerCat": task.ownerCat,
        "description": task.description,
        "threadId": task.threadId,
        "createdAt": task.createdAt,
    }


@router.post("/entries/{taskId}/status")
async def update_task_status(taskId: str, status: Literal["todo", "doing", "blocked", "done"]):
    """Update task status."""
    db = await _get_db()
    cursor = await db.execute("SELECT 1 FROM thread_tasks WHERE id = ?", (taskId,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Task not found")
    await db.execute("UPDATE thread_tasks SET status = ? WHERE id = ?", (status, taskId))
    await db.commit()
    await db.close()
    return {"success": True}


@router.delete("/entries/{taskId}")
async def delete_task(taskId: str):
    """Delete a task."""
    db = await _get_db()
    cursor = await db.execute("SELECT 1 FROM thread_tasks WHERE id = ?", (taskId,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Task not found")
    await db.execute("DELETE FROM thread_tasks WHERE id = ?", (taskId,))
    await db.commit()
    await db.close()
    return {"success": True}
