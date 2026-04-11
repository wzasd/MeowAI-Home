"""Tasks API routes for task management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskItem(BaseModel):
    id: str = ""
    title: str
    status: Literal["todo", "doing", "blocked", "done"]
    ownerCat: Optional[str] = None
    description: Optional[str] = None
    threadId: Optional[str] = None
    createdAt: str = ""


# In-memory storage (replace with database in production)
_tasks: dict[str, TaskItem] = {}


@router.get("/entries")
async def list_tasks(threadId: Optional[str] = None):
    """Get tasks, optionally filtered by thread."""
    entries = list(_tasks.values())
    if threadId:
        entries = [e for e in entries if e.threadId == threadId]
    return entries


@router.post("/entries")
async def create_task(task: TaskItem):
    """Create a new task."""
    if not task.id:
        task.id = str(uuid.uuid4())[:8]
    if not task.createdAt:
        task.createdAt = datetime.now().isoformat()
    _tasks[task.id] = task
    return task


@router.post("/entries/{taskId}/status")
async def update_task_status(taskId: str, status: Literal["todo", "doing", "blocked", "done"]):
    """Update task status."""
    if taskId not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    _tasks[taskId].status = status
    return {"success": True}


@router.delete("/entries/{taskId}")
async def delete_task(taskId: str):
    """Delete a task."""
    if taskId not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    del _tasks[taskId]
    return {"success": True}
