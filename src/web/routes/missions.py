"""Mission Hub API routes for project task management."""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request
import uuid

from src.missions.store import MissionStore
from src.thread import ThreadManager
from src.thread.models import Message
from src.web.dependencies import get_mission_store, get_thread_manager
from src.web.routes.ws import manager as ws_manager

router = APIRouter(prefix="/missions", tags=["missions"])

# === Types ===

TaskStatus = Literal["backlog", "todo", "doing", "blocked", "done"]
Priority = Literal["P0", "P1", "P2", "P3"]


# === Models ===

class MissionTask(BaseModel):
    """Mission task model."""
    id: str = ""
    title: str
    description: str = ""
    status: TaskStatus = "backlog"
    priority: Priority = "P2"
    ownerCat: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    createdAt: str = ""
    dueDate: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    thread_ids: List[str] = Field(default_factory=list)
    workflow_id: Optional[str] = None
    session_ids: List[str] = Field(default_factory=list)
    pr_url: Optional[str] = None
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    worktree_path: Optional[str] = None
    last_activity_at: Optional[float] = None


class TaskCreateRequest(BaseModel):
    """Create task request."""
    title: str
    description: str = ""
    status: TaskStatus = "backlog"
    priority: Priority = "P2"
    ownerCat: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    dueDate: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)


class TaskUpdateRequest(BaseModel):
    """Update task request."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    ownerCat: Optional[str] = None
    tags: Optional[List[str]] = None
    dueDate: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)


class TaskStatusUpdate(BaseModel):
    """Update task status request."""
    status: TaskStatus


class TasksResponse(BaseModel):
    """Tasks list response."""
    tasks: List[MissionTask]
    total: int


class TaskStats(BaseModel):
    """Task statistics."""
    total: int
    backlog: int
    todo: int
    doing: int
    blocked: int
    done: int
    by_priority: Dict[str, int]


async def _broadcast_task_update(thread_ids: List[str], task: Dict[str, object]) -> None:
    """Broadcast task update via WebSocket to all bound threads."""
    for tid in thread_ids:
        await ws_manager.broadcast(
            tid,
            {
                "type": "task_updated",
                "task": task,
            },
        )


async def _push_system_message(
    thread_id: str,
    content: str,
    tm: ThreadManager,
) -> None:
    """Push a system message to the bound thread."""
    try:
        msg = Message(role="assistant", content=content, cat_id="system")
        await tm.add_message(thread_id, msg)
        await ws_manager.broadcast(
            thread_id,
            {
                "type": "message_sent",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "cat_id": "system",
                    "metadata": {"source": "mission_update"},
                },
            },
        )
    except Exception:
        pass


def _task_from_dict(data: Dict[str, object]) -> MissionTask:
    return MissionTask(
        id=data.get("id", ""),
        title=data["title"],
        description=data.get("description", ""),
        status=data.get("status", "backlog"),
        priority=data.get("priority", "P2"),
        ownerCat=data.get("ownerCat"),
        tags=data.get("tags", []),
        createdAt=data.get("createdAt", ""),
        dueDate=data.get("dueDate"),
        progress=data.get("progress"),
        thread_ids=data.get("thread_ids", []),
        workflow_id=data.get("workflow_id"),
        session_ids=data.get("session_ids", []),
        pr_url=data.get("pr_url"),
        branch=data.get("branch"),
        commit_hash=data.get("commit_hash"),
        worktree_path=data.get("worktree_path"),
        last_activity_at=data.get("last_activity_at"),
    )


# === API Endpoints ===

@router.get("/tasks", response_model=TasksResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    store: MissionStore = Depends(get_mission_store),
) -> TasksResponse:
    """List all mission tasks with optional filtering."""
    rows = await store.list_tasks(status=status, priority=priority, tag=tag)
    tasks = [_task_from_dict(r) for r in rows]
    return TasksResponse(tasks=tasks, total=len(tasks))


@router.post("/tasks", response_model=MissionTask)
async def create_task(
    request: TaskCreateRequest,
    store: MissionStore = Depends(get_mission_store),
    tm: ThreadManager = Depends(get_thread_manager),
) -> MissionTask:
    """Create a new mission task and auto-bind a dedicated thread."""
    task_data = request.model_dump()
    task_row = await store.create_task(task_data)
    task_id = task_row["id"]

    # Auto-create a dedicated thread for this task
    thread = await tm.create(name=f"任务: {request.title}", current_cat_id="orange", project_path="")
    thread.active_task_id = task_id
    await tm.update_thread(thread)

    # Update task with thread_ids
    task_row = await store.update_task(task_id, {"thread_ids": [thread.id]})

    # Push system message to thread
    await _push_system_message(
        thread.id,
        f"【系统】任务「{request.title}」已创建，状态：{request.status}，优先级：{request.priority}。",
        tm,
    )

    return _task_from_dict(task_row)


@router.get("/tasks/{task_id}", response_model=MissionTask)
async def get_task(
    task_id: str,
    store: MissionStore = Depends(get_mission_store),
) -> MissionTask:
    """Get a single task by ID."""
    row = await store.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_from_dict(row)


@router.patch("/tasks/{task_id}", response_model=MissionTask)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    store: MissionStore = Depends(get_mission_store),
    tm: ThreadManager = Depends(get_thread_manager),
) -> MissionTask:
    """Update a task and notify bound thread."""
    row = await store.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        return _task_from_dict(row)

    updated = await store.update_task(task_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build notification content for changed fields
    changed_parts = []
    for key, value in updates.items():
        if key == "status":
            changed_parts.append(f"状态 → {value}")
        elif key == "priority":
            changed_parts.append(f"优先级 → {value}")
        elif key == "ownerCat":
            changed_parts.append(f"负责人 → @{value}" if value else "负责人 → 未分配")
        elif key == "progress":
            changed_parts.append(f"进度 → {value}%")
        elif key == "title":
            changed_parts.append(f"标题 → {value}")

    thread_ids = updated.get("thread_ids", [])
    if thread_ids and changed_parts:
        content = f"【系统】任务更新：{', '.join(changed_parts)}"
        for tid in thread_ids:
            await _push_system_message(tid, content, tm)
        await _broadcast_task_update(thread_ids, updated)

    return _task_from_dict(updated)


@router.post("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    update: TaskStatusUpdate,
    store: MissionStore = Depends(get_mission_store),
    tm: ThreadManager = Depends(get_thread_manager),
) -> dict:
    """Update task status and notify bound thread."""
    row = await store.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    updated = await store.update_task(task_id, {"status": update.status})
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    thread_ids = updated.get("thread_ids", [])
    if thread_ids:
        content = f"【系统】任务状态变更为：{update.status}"
        for tid in thread_ids:
            await _push_system_message(tid, content, tm)
        await _broadcast_task_update(thread_ids, updated)

    return {"success": True, "id": task_id, "status": update.status}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    store: MissionStore = Depends(get_mission_store),
    tm: ThreadManager = Depends(get_thread_manager),
) -> dict:
    """Delete a task and notify bound thread."""
    row = await store.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")

    thread_ids = row.get("thread_ids", [])
    success = await store.delete_task(task_id)

    for tid in thread_ids:
        await _push_system_message(tid, "【系统】该任务已被删除。", tm)
        await ws_manager.broadcast(
            tid,
            {"type": "task_deleted", "task_id": task_id},
        )

    return {"success": success}


@router.get("/stats", response_model=TaskStats)
async def get_stats(
    store: MissionStore = Depends(get_mission_store),
) -> TaskStats:
    """Get task statistics."""
    tasks = await store.list_tasks()
    by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for t in tasks:
        p = t.get("priority")
        if p in by_priority:
            by_priority[p] += 1

    return TaskStats(
        total=len(tasks),
        backlog=sum(1 for t in tasks if t.get("status") == "backlog"),
        todo=sum(1 for t in tasks if t.get("status") == "todo"),
        doing=sum(1 for t in tasks if t.get("status") == "doing"),
        blocked=sum(1 for t in tasks if t.get("status") == "blocked"),
        done=sum(1 for t in tasks if t.get("status") == "done"),
        by_priority=by_priority,
    )
