"""Queue API routes for invocation queue management (SQLite-backed)."""
import aiosqlite
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from pathlib import Path
import uuid

router = APIRouter(prefix="/queue", tags=["queue"])

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS queue_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    targetCats TEXT NOT NULL,
    status TEXT DEFAULT 'queued',
    threadId TEXT,
    createdAt TEXT
);
CREATE INDEX IF NOT EXISTS idx_queue_thread ON queue_entries(threadId);
CREATE INDEX IF NOT EXISTS idx_queue_status ON queue_entries(status);
"""


async def _get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DEFAULT_DB_PATH)
    await db.executescript(_INIT_SQL)
    return db


class QueueEntry(BaseModel):
    id: str = ""
    content: str
    targetCats: list[str]
    status: Literal["queued", "processing", "paused"]
    createdAt: str = ""
    threadId: Optional[str] = None


@router.get("/entries")
async def list_queue_entries(threadId: Optional[str] = None):
    """Get queue entries, optionally filtered by thread."""
    db = await _get_db()
    sql = "SELECT id, content, targetCats, status, threadId, createdAt FROM queue_entries"
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
            "content": row[1],
            "targetCats": row[2].split(","),
            "status": row[3],
            "threadId": row[4],
            "createdAt": row[5],
        }
        for row in rows
    ]


@router.post("/entries")
async def create_entry(entry: QueueEntry):
    """Create a new queue entry."""
    if not entry.id:
        entry.id = str(uuid.uuid4())[:8]
    if not entry.createdAt:
        entry.createdAt = datetime.now().isoformat()

    db = await _get_db()
    await db.execute(
        """
        INSERT INTO queue_entries (id, content, targetCats, status, threadId, createdAt)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entry.id, entry.content, ",".join(entry.targetCats), entry.status, entry.threadId, entry.createdAt),
    )
    await db.commit()
    await db.close()
    return {
        "id": entry.id,
        "content": entry.content,
        "targetCats": entry.targetCats,
        "status": entry.status,
        "threadId": entry.threadId,
        "createdAt": entry.createdAt,
    }


@router.post("/entries/{entryId}/pause")
async def pause_entry(entryId: str):
    """Pause a pending entry."""
    db = await _get_db()
    cursor = await db.execute("SELECT 1 FROM queue_entries WHERE id = ?", (entryId,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.execute("UPDATE queue_entries SET status = ? WHERE id = ?", ("paused", entryId))
    await db.commit()
    await db.close()
    return {"success": True}


@router.post("/entries/{entryId}/resume")
async def resume_entry(entryId: str):
    """Resume a paused entry."""
    db = await _get_db()
    cursor = await db.execute("SELECT 1 FROM queue_entries WHERE id = ?", (entryId,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.execute("UPDATE queue_entries SET status = ? WHERE id = ?", ("queued", entryId))
    await db.commit()
    await db.close()
    return {"success": True}


@router.delete("/entries/{entryId}")
async def remove_entry(entryId: str):
    """Remove an entry from the queue."""
    db = await _get_db()
    cursor = await db.execute("SELECT 1 FROM queue_entries WHERE id = ?", (entryId,))
    if not await cursor.fetchone():
        await db.close()
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.execute("DELETE FROM queue_entries WHERE id = ?", (entryId,))
    await db.commit()
    await db.close()
    return {"success": True}
