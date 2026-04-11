"""Mission Hub API routes for project task management."""

from datetime import datetime
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query
import uuid

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


# === In-memory storage (TODO: replace with database) ===

_missions: Dict[str, MissionTask] = {}


def _ensure_default_tasks():
    """Ensure default tasks exist."""
    if not _missions:
        defaults = [
            MissionTask(
                id="m1",
                title="实现消息编辑功能",
                description="支持用户编辑已发送的消息",
                status="doing",
                priority="P0",
                ownerCat="orange",
                tags=["聊天", "核心"],
                createdAt="2026-04-10",
                progress=60,
            ),
            MissionTask(
                id="m2",
                title="添加 Signal 收件箱页面",
                description="展示聚合文章，支持学习模式",
                status="done",
                priority="P1",
                ownerCat="patch",
                tags=["Signal"],
                createdAt="2026-04-09",
                progress=100,
            ),
            MissionTask(
                id="m3",
                title="富文本块组件",
                description="Card, Diff, Checklist, Media blocks",
                status="done",
                priority="P1",
                ownerCat="inky",
                tags=["UI", "聊天"],
                createdAt="2026-04-09",
                progress=100,
            ),
            MissionTask(
                id="m4",
                title="右侧面板开发",
                description="Token统计、Session链、任务面板、队列管理",
                status="doing",
                priority="P0",
                ownerCat="inky",
                tags=["UI", "面板"],
                createdAt="2026-04-10",
                progress=80,
            ),
            MissionTask(
                id="m5",
                title="Workspace IDE 面板",
                description="文件树 + 代码查看器 + 终端",
                status="backlog",
                priority="P2",
                tags=["Workspace", "IDE"],
                createdAt="2026-04-11",
            ),
            MissionTask(
                id="m6",
                title="Split Pane 多线程视图",
                description="2x2 分屏同时查看多个线程",
                status="backlog",
                priority="P2",
                tags=["聊天", "UI"],
                createdAt="2026-04-11",
            ),
            MissionTask(
                id="m7",
                title="语音输入输出",
                description="Whisper API 集成 + TTS 流式播放",
                status="backlog",
                priority="P3",
                tags=["语音"],
                createdAt="2026-04-11",
            ),
            MissionTask(
                id="m8",
                title="消息分支功能",
                description="从任意消息分支出新线程",
                status="todo",
                priority="P1",
                ownerCat="orange",
                tags=["聊天", "线程"],
                createdAt="2026-04-10",
            ),
            MissionTask(
                id="m9",
                title="历史搜索模态框",
                description="全文搜索历史对话",
                status="done",
                priority="P1",
                tags=["搜索"],
                createdAt="2026-04-10",
                progress=100,
            ),
            MissionTask(
                id="m10",
                title="依赖图可视化",
                description="DAGre + React Flow 任务依赖关系图",
                status="blocked",
                priority="P2",
                tags=["Mission", "图表"],
                createdAt="2026-04-10",
                dueDate="2026-04-15",
            ),
        ]
        for task in defaults:
            _missions[task.id] = task


# === API Endpoints ===

@router.get("/tasks", response_model=TasksResponse)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
) -> TasksResponse:
    """List all mission tasks with optional filtering."""
    _ensure_default_tasks()

    tasks = list(_missions.values())

    if status:
        tasks = [t for t in tasks if t.status == status]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if tag:
        tasks = [t for t in tasks if tag in t.tags]

    return TasksResponse(tasks=tasks, total=len(tasks))


@router.post("/tasks", response_model=MissionTask)
async def create_task(request: TaskCreateRequest) -> MissionTask:
    """Create a new mission task."""
    _ensure_default_tasks()

    task = MissionTask(
        id=str(uuid.uuid4())[:8],
        title=request.title,
        description=request.description,
        status=request.status,
        priority=request.priority,
        ownerCat=request.ownerCat,
        tags=request.tags,
        createdAt=datetime.now().strftime("%Y-%m-%d"),
        dueDate=request.dueDate,
        progress=request.progress,
    )
    _missions[task.id] = task
    return task


@router.get("/tasks/{task_id}", response_model=MissionTask)
async def get_task(task_id: str) -> MissionTask:
    """Get a single task by ID."""
    _ensure_default_tasks()

    if task_id not in _missions:
        raise HTTPException(status_code=404, detail="Task not found")
    return _missions[task_id]


@router.patch("/tasks/{task_id}", response_model=MissionTask)
async def update_task(task_id: str, request: TaskUpdateRequest) -> MissionTask:
    """Update a task."""
    _ensure_default_tasks()

    if task_id not in _missions:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _missions[task_id]
    update_data = request.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(task, key, value)

    return task


@router.post("/tasks/{task_id}/status")
async def update_task_status(task_id: str, update: TaskStatusUpdate) -> dict:
    """Update task status."""
    _ensure_default_tasks()

    if task_id not in _missions:
        raise HTTPException(status_code=404, detail="Task not found")

    _missions[task_id].status = update.status
    return {"success": True, "id": task_id, "status": update.status}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str) -> dict:
    """Delete a task."""
    _ensure_default_tasks()

    if task_id not in _missions:
        raise HTTPException(status_code=404, detail="Task not found")

    del _missions[task_id]
    return {"success": True}


@router.get("/stats", response_model=TaskStats)
async def get_stats() -> TaskStats:
    """Get task statistics."""
    _ensure_default_tasks()

    tasks = list(_missions.values())
    by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for t in tasks:
        if t.priority in by_priority:
            by_priority[t.priority] += 1

    return TaskStats(
        total=len(tasks),
        backlog=sum(1 for t in tasks if t.status == "backlog"),
        todo=sum(1 for t in tasks if t.status == "todo"),
        doing=sum(1 for t in tasks if t.status == "doing"),
        blocked=sum(1 for t in tasks if t.status == "blocked"),
        done=sum(1 for t in tasks if t.status == "done"),
        by_priority=by_priority,
    )
