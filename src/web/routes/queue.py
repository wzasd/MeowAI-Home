"""Queue API routes for invocation queue management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/queue", tags=["queue"])


class QueueEntry(BaseModel):
    id: str = ""
    content: str
    targetCats: list[str]
    status: Literal["queued", "processing", "paused"]
    createdAt: str = ""
    threadId: Optional[str] = None


# In-memory storage (replace with database in production)
_queue_entries: dict[str, QueueEntry] = {}


@router.get("/entries")
async def list_queue_entries(threadId: Optional[str] = None):
    """Get queue entries, optionally filtered by thread."""
    entries = list(_queue_entries.values())
    if threadId:
        entries = [e for e in entries if e.threadId == threadId]
    # Sort by created time descending
    entries.sort(key=lambda x: x.createdAt, reverse=True)
    return entries


@router.post("/entries")
async def create_entry(entry: QueueEntry):
    """Create a new queue entry."""
    if not entry.id:
        entry.id = str(uuid.uuid4())[:8]
    if not entry.createdAt:
        entry.createdAt = datetime.now().isoformat()
    _queue_entries[entry.id] = entry
    return entry


@router.post("/entries/{entryId}/pause")
async def pause_entry(entryId: str):
    """Pause a queue entry."""
    if entryId not in _queue_entries:
        raise HTTPException(status_code=404, detail="Entry not found")
    _queue_entries[entryId].status = "paused"
    return {"success": True}


@router.post("/entries/{entryId}/resume")
async def resume_entry(entryId: str):
    """Resume a paused queue entry."""
    if entryId not in _queue_entries:
        raise HTTPException(status_code=404, detail="Entry not found")
    entry = _queue_entries[entryId]
    entry.status = "queued" if entry.status == "paused" else entry.status
    return {"success": True}


@router.delete("/entries/{entryId}")
async def remove_entry(entryId: str):
    """Remove a queue entry."""
    if entryId not in _queue_entries:
        raise HTTPException(status_code=404, detail="Entry not found")
    del _queue_entries[entryId]
    return {"success": True}
