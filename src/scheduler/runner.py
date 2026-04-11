"""TaskRunner — Scheduled task execution with interval and cron triggers."""

import asyncio
import sqlite3
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Callable, Coroutine, Dict, List, Optional, Any
import json
from croniter import croniter


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class TaskTrigger(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """A scheduled task definition."""

    id: str
    name: str
    description: str
    trigger: TaskTrigger
    # For INTERVAL: seconds
    # For CRON: cron expression (e.g., "0 9 * * *")
    schedule: str
    enabled: bool = True
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    # Task configuration
    actor_role: str = "default"  # Role to resolve actor
    cost_tier: str = "standard"  # Cost tier for actor resolution
    task_template: str = "default"  # Template identifier
    task_config: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()


class TaskGovernance:
    """Global governance for task execution."""

    def __init__(self):
        self._global_pause = False
        self._task_switches: Dict[str, bool] = {}

    def pause_all(self) -> None:
        self._global_pause = True

    def resume_all(self) -> None:
        self._global_pause = False

    def is_paused(self) -> bool:
        return self._global_pause

    def enable_task(self, task_id: str) -> None:
        self._task_switches[task_id] = True

    def disable_task(self, task_id: str) -> None:
        self._task_switches[task_id] = False

    def is_task_enabled(self, task_id: str) -> bool:
        return self._task_switches.get(task_id, True)


class TaskRunner:
    """Manages scheduled tasks with SQLite persistence."""

    def __init__(
        self,
        db_path: str = "data/scheduler.db",
        governance: Optional[TaskGovernance] = None,
    ):
        self._db_path = db_path
        self._governance = governance or TaskGovernance()
        self._tasks: Dict[str, ScheduledTask] = {}
        self._handlers: Dict[str, Callable[[ScheduledTask], Coroutine]] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._overlap_guard: Dict[str, bool] = {}  # Prevent re-entry
        self._init_db()
        self._load_tasks()

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    last_run REAL,
                    next_run REAL,
                    run_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    actor_role TEXT DEFAULT 'default',
                    cost_tier TEXT DEFAULT 'standard',
                    task_template TEXT DEFAULT 'default',
                    task_config TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_enabled
                ON scheduled_tasks(enabled)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_next_run
                ON scheduled_tasks(next_run)
            """)
            conn.commit()

    def _load_tasks(self) -> None:
        """Load tasks from database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM scheduled_tasks").fetchall()
            for row in rows:
                task = self._row_to_task(row)
                self._tasks[task.id] = task

    def _row_to_task(self, row: sqlite3.Row) -> ScheduledTask:
        return ScheduledTask(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            trigger=TaskTrigger(row["trigger"]),
            schedule=row["schedule"],
            enabled=bool(row["enabled"]),
            status=TaskStatus(row["status"]),
            last_run=row["last_run"],
            next_run=row["next_run"],
            run_count=row["run_count"],
            error_count=row["error_count"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            actor_role=row["actor_role"] or "default",
            cost_tier=row["cost_tier"] or "standard",
            task_template=row["task_template"] or "default",
            task_config=json.loads(row["task_config"]) if row["task_config"] else None,
        )

    def _task_to_row(self, task: ScheduledTask) -> tuple:
        return (
            task.id,
            task.name,
            task.description,
            task.trigger.value,
            task.schedule,
            1 if task.enabled else 0,
            task.status.value,
            task.last_run,
            task.next_run,
            task.run_count,
            task.error_count,
            task.last_error,
            task.created_at,
            task.updated_at,
            task.actor_role,
            task.cost_tier,
            task.task_template,
            json.dumps(task.task_config) if task.task_config else None,
        )

    def _save_task(self, task: ScheduledTask) -> None:
        """Save task to database."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_tasks
                (id, name, description, trigger, schedule, enabled, status,
                 last_run, next_run, run_count, error_count, last_error,
                 created_at, updated_at, actor_role, cost_tier, task_template, task_config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._task_to_row(task),
            )
            conn.commit()

    def register_task(
        self,
        task: ScheduledTask,
        handler: Callable[[ScheduledTask], Coroutine],
    ) -> None:
        """Register a task with its handler."""
        self._tasks[task.id] = task
        self._handlers[task.id] = handler
        self._save_task(task)

    def unregister_task(self, task_id: str) -> bool:
        """Unregister and delete a task."""
        if task_id not in self._tasks:
            return False

        # Cancel if running
        self.cancel_task(task_id)

        del self._tasks[task_id]
        if task_id in self._handlers:
            del self._handlers[task_id]

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
            conn.commit()

        return True

    def cancel_task(self, task_id: str) -> None:
        """Cancel a running task execution."""
        if task_id in self._running:
            self._running[task_id].cancel()
            del self._running[task_id]

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self) -> List[ScheduledTask]:
        """List all tasks."""
        return list(self._tasks.values())

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        task.enabled = True
        task.status = TaskStatus.PENDING
        task.updated_at = time.time()
        self._save_task(task)
        self._governance.enable_task(task_id)
        return True

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id not in self._tasks:
            return False
        task = self._tasks[task_id]
        task.enabled = False
        task.status = TaskStatus.DISABLED
        task.updated_at = time.time()
        self._save_task(task)
        self._governance.disable_task(task_id)
        self.cancel_task(task_id)
        return True

    def _calculate_next_run(self, task: ScheduledTask) -> Optional[float]:
        """Calculate next run time for a task."""
        now = time.time()

        if task.trigger == TaskTrigger.INTERVAL:
            try:
                interval_seconds = int(task.schedule)
                if task.last_run:
                    return task.last_run + interval_seconds
                return now + interval_seconds
            except ValueError:
                return None

        elif task.trigger == TaskTrigger.CRON:
            try:
                cron = croniter(task.schedule, now)
                return cron.get_next(float)
            except Exception:
                return None

        return None

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a single task with guards."""
        task_id = task.id

        # Check enabled
        if not task.enabled:
            return

        # Check governance
        if self._governance.is_paused():
            return
        if not self._governance.is_task_enabled(task_id):
            return

        # Overlap guard
        if self._overlap_guard.get(task_id, False):
            return

        self._overlap_guard[task_id] = True
        task.status = TaskStatus.RUNNING
        task.updated_at = time.time()
        self._save_task(task)

        try:
            handler = self._handlers.get(task_id)
            if handler:
                await handler(task)

            task.last_run = time.time()
            task.run_count += 1
            task.error_count = 0
            task.last_error = None
            task.status = TaskStatus.PENDING if task.enabled else TaskStatus.DISABLED
        except Exception as e:
            task.error_count += 1
            task.last_error = str(e)
            task.status = TaskStatus.ERROR
        finally:
            self._overlap_guard[task_id] = False
            task.next_run = self._calculate_next_run(task)
            task.updated_at = time.time()
            self._save_task(task)

    async def _run_task_loop(self, task: ScheduledTask) -> None:
        """Run a task's scheduling loop."""
        while task.enabled and task.id in self._tasks:
            try:
                # Calculate sleep time
                now = time.time()
                next_run = task.next_run or self._calculate_next_run(task)

                if next_run and next_run > now:
                    sleep_duration = next_run - now
                    # Cap at 60 seconds to check for changes
                    sleep_duration = min(sleep_duration, 60)
                    await asyncio.sleep(sleep_duration)
                else:
                    await asyncio.sleep(1)

                # Check if it's time to run
                now = time.time()
                if task.next_run and now >= task.next_run:
                    await self._execute_task(task)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)  # Wait before retrying on error

    async def start(self) -> None:
        """Start the task runner."""
        # Initialize next_run for all pending tasks
        for task in self._tasks.values():
            if task.enabled and task.next_run is None:
                task.next_run = self._calculate_next_run(task)
                self._save_task(task)

        # Start task loops
        for task_id, task in self._tasks.items():
            if task.enabled and task_id not in self._running:
                self._running[task_id] = asyncio.create_task(
                    self._run_task_loop(task)
                )

    async def stop(self) -> None:
        """Stop all task loops."""
        for task in self._running.values():
            task.cancel()

        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
        self._running.clear()

    def pause_all(self) -> None:
        """Pause all task execution."""
        self._governance.pause_all()

    def resume_all(self) -> None:
        """Resume all task execution."""
        self._governance.resume_all()
