"""Scheduler REST API endpoints for scheduled task management."""

import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.scheduler.runner import TaskRunner, ScheduledTask, TaskTrigger, TaskStatus
from src.scheduler.templates import list_templates, get_template

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


# === Models ===

class ScheduledTaskCreate(BaseModel):
    name: str
    description: str = ""
    trigger: str  # "interval" | "cron"
    schedule: str  # seconds for interval, cron expr for cron
    enabled: bool = True
    actor_role: str = "default"
    cost_tier: str = "standard"
    task_template: str = "default"
    task_config: Optional[Dict[str, Any]] = None


class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    actor_role: Optional[str] = None
    cost_tier: Optional[str] = None
    task_template: Optional[str] = None
    task_config: Optional[Dict[str, Any]] = None


class ScheduledTaskResponse(BaseModel):
    id: str
    name: str
    description: str
    trigger: str
    schedule: str
    enabled: bool
    status: str
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int
    error_count: int
    last_error: Optional[str] = None
    created_at: float
    updated_at: float
    actor_role: str
    cost_tier: str
    task_template: str
    task_config: Optional[Dict[str, Any]] = None


class TaskListResponse(BaseModel):
    tasks: List[ScheduledTaskResponse]


class TemplateListResponse(BaseModel):
    templates: List[Dict[str, Any]]


class TriggerNowRequest(BaseModel):
    pass


class TriggerNowResponse(BaseModel):
    success: bool
    task_id: str
    message: str


class TaskLogEntry(BaseModel):
    task_id: str
    success: bool
    execution_time_ms: float
    timestamp: float
    error: Optional[str] = None
    actor_id: Optional[str] = None


class TaskLogsResponse(BaseModel):
    logs: List[TaskLogEntry]


class GovernanceAction(BaseModel):
    action: str  # "pause_all" | "resume_all"


# === Helpers ===

def _get_task_runner(request: Request) -> TaskRunner:
    runner = getattr(request.app.state, "task_runner", None)
    if runner is None:
        raise HTTPException(status_code=503, detail="Task runner not initialized")
    return runner


def _task_to_dict(task: ScheduledTask) -> Dict[str, Any]:
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "trigger": task.trigger.value,
        "schedule": task.schedule,
        "enabled": task.enabled,
        "status": task.status.value,
        "last_run": task.last_run,
        "next_run": task.next_run,
        "run_count": task.run_count,
        "error_count": task.error_count,
        "last_error": task.last_error,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "actor_role": task.actor_role,
        "cost_tier": task.cost_tier,
        "task_template": task.task_template,
        "task_config": task.task_config,
    }


# === Endpoints ===

@router.get("/templates", response_model=TemplateListResponse)
async def list_scheduler_templates():
    """List available scheduler templates."""
    return {"templates": list_templates()}


@router.get("/tasks", response_model=TaskListResponse)
async def list_scheduler_tasks(request: Request):
    """List all scheduled tasks."""
    runner = _get_task_runner(request)
    tasks = runner.list_tasks()
    return {"tasks": [_task_to_dict(t) for t in tasks]}


@router.post("/tasks", response_model=ScheduledTaskResponse)
async def create_scheduler_task(payload: ScheduledTaskCreate, request: Request):
    """Create a new scheduled task."""
    runner = _get_task_runner(request)

    if payload.trigger not in {TaskTrigger.INTERVAL.value, TaskTrigger.CRON.value}:
        raise HTTPException(status_code=400, detail=f"Invalid trigger: {payload.trigger}")

    task_id = str(uuid.uuid4())[:8]
    task = ScheduledTask(
        id=task_id,
        name=payload.name,
        description=payload.description,
        trigger=TaskTrigger(payload.trigger),
        schedule=payload.schedule,
        enabled=payload.enabled,
        actor_role=payload.actor_role,
        cost_tier=payload.cost_tier,
        task_template=payload.task_template,
        task_config=payload.task_config,
    )

    # Default handler: no-op coroutine (real handlers registered at runtime)
    async def _noop_handler(task: ScheduledTask) -> None:
        pass

    runner.register_task(task, _noop_handler)

    # If enabled, start the task loop
    if task.enabled and hasattr(runner, "_running"):
        import asyncio
        if task_id not in runner._running:
            task.next_run = runner._calculate_next_run(task)
            runner._save_task(task)
            runner._running[task_id] = asyncio.create_task(runner._run_task_loop(task))

    return _task_to_dict(task)


@router.get("/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduler_task(task_id: str, request: Request):
    """Get a single scheduled task."""
    runner = _get_task_runner(request)
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(task)


@router.patch("/tasks/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduler_task(task_id: str, payload: ScheduledTaskUpdate, request: Request):
    """Update a scheduled task."""
    runner = _get_task_runner(request)
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = payload.model_dump(exclude_unset=True)

    if "trigger" in updates:
        if updates["trigger"] not in {TaskTrigger.INTERVAL.value, TaskTrigger.CRON.value}:
            raise HTTPException(status_code=400, detail=f"Invalid trigger: {updates['trigger']}")
        task.trigger = TaskTrigger(updates["trigger"])

    if "name" in updates:
        task.name = updates["name"]
    if "description" in updates:
        task.description = updates["description"]
    if "schedule" in updates:
        task.schedule = updates["schedule"]
    if "enabled" in updates:
        task.enabled = updates["enabled"]
        task.status = TaskStatus.PENDING if task.enabled else TaskStatus.DISABLED
    if "actor_role" in updates:
        task.actor_role = updates["actor_role"]
    if "cost_tier" in updates:
        task.cost_tier = updates["cost_tier"]
    if "task_template" in updates:
        task.task_template = updates["task_template"]
    if "task_config" in updates:
        task.task_config = updates["task_config"]

    task.updated_at = time.time()
    task.next_run = runner._calculate_next_run(task)
    runner._save_task(task)

    # Start/stop loop as needed
    import asyncio
    if task.enabled and task_id not in runner._running:
        runner._running[task_id] = asyncio.create_task(runner._run_task_loop(task))
    elif not task.enabled and task_id in runner._running:
        runner._running[task_id].cancel()
        del runner._running[task_id]

    return _task_to_dict(task)


@router.post("/tasks/{task_id}/enable")
async def enable_scheduler_task(task_id: str, request: Request):
    """Enable a scheduled task."""
    runner = _get_task_runner(request)
    success = runner.enable_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    task = runner.get_task(task_id)
    if task and task_id not in runner._running:
        import asyncio
        task.next_run = runner._calculate_next_run(task)
        runner._save_task(task)
        runner._running[task_id] = asyncio.create_task(runner._run_task_loop(task))

    return {"success": True, "id": task_id, "enabled": True}


@router.post("/tasks/{task_id}/disable")
async def disable_scheduler_task(task_id: str, request: Request):
    """Disable a scheduled task."""
    runner = _get_task_runner(request)
    success = runner.disable_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_id in runner._running:
        runner._running[task_id].cancel()
        del runner._running[task_id]

    return {"success": True, "id": task_id, "enabled": False}


@router.post("/tasks/{task_id}/trigger", response_model=TriggerNowResponse)
async def trigger_scheduler_task(task_id: str, request: Request):
    """Manually trigger a scheduled task immediately."""
    runner = _get_task_runner(request)
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import asyncio
    asyncio.create_task(runner._execute_task(task))

    return {"success": True, "task_id": task_id, "message": "Task triggered"}


@router.delete("/tasks/{task_id}")
async def delete_scheduler_task(task_id: str, request: Request):
    """Delete a scheduled task."""
    runner = _get_task_runner(request)
    success = runner.unregister_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "id": task_id}


@router.get("/tasks/{task_id}/logs", response_model=TaskLogsResponse)
async def get_scheduler_task_logs(task_id: str, request: Request):
    """Get execution logs for a scheduled task."""
    runner = _get_task_runner(request)
    task = runner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If pipeline is available via app state, use its ledger
    pipeline = getattr(request.app.state, "scheduler_pipeline", None)
    if pipeline:
        history = pipeline.get_history(task_id)
        return {
            "logs": [
                {
                    "task_id": entry.get("task_id", task_id),
                    "success": entry.get("success", False),
                    "execution_time_ms": entry.get("execution_time_ms", 0.0),
                    "timestamp": entry.get("timestamp", 0.0),
                    "error": entry.get("error"),
                    "actor_id": entry.get("actor_id"),
                }
                for entry in history
            ]
        }

    # Fallback: return minimal log from task stats
    return {
        "logs": [
            {
                "task_id": task_id,
                "success": task.error_count == 0 and task.run_count > 0,
                "execution_time_ms": 0.0,
                "timestamp": task.last_run or 0.0,
                "error": task.last_error,
                "actor_id": None,
            }
        ] if task.last_run else []
    }


@router.post("/governance")
async def scheduler_governance(action: GovernanceAction, request: Request):
    """Pause or resume all scheduled tasks."""
    runner = _get_task_runner(request)
    if action.action == "pause_all":
        runner.pause_all()
        return {"success": True, "action": "pause_all"}
    elif action.action == "resume_all":
        runner.resume_all()
        return {"success": True, "action": "resume_all"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'pause_all' or 'resume_all'")
