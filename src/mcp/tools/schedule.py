"""Schedule MCP tools for task scheduling."""

import json
from typing import Any, Dict, List, Optional

from src.scheduler import TaskRunner, ScheduledTask, TaskTrigger


class ScheduleTools:
    """MCP tools for schedule management."""

    def __init__(self, task_runner: TaskRunner):
        self._task_runner = task_runner

    async def list_schedule_templates(self) -> Dict[str, Any]:
        """List available schedule templates.

        Returns:
            Dict with available templates and their descriptions.
        """
        templates = {
            "daily_digest": {
                "name": "每日摘要",
                "description": "每天生成一次对话摘要",
                "default_schedule": "0 9 * * *",  # 9 AM daily
                "parameters": {
                    "target_thread": "Thread ID to post digest to",
                    "summary_type": "brief|detailed",
                },
            },
            "health_check": {
                "name": "健康检查",
                "description": "定期执行系统健康检查",
                "default_schedule": "0 */6 * * *",  # Every 6 hours
                "parameters": {
                    "check_type": "basic|full",
                    "alert_on_failure": "boolean",
                },
            },
            "cleanup": {
                "name": "数据清理",
                "description": "清理过期数据和临时文件",
                "default_schedule": "0 3 * * 0",  # 3 AM Sunday
                "parameters": {
                    "retention_days": "number of days to keep",
                    "cleanup_types": "list of types to clean",
                },
            },
            "custom": {
                "name": "自定义任务",
                "description": "执行自定义配置的任务",
                "default_schedule": "0 */12 * * *",
                "parameters": {
                    "command": "command to execute",
                    "args": "list of arguments",
                },
            },
        }

        return {
            "templates": templates,
            "count": len(templates),
        }

    async def preview_scheduled_task(
        self,
        template: str,
        schedule: str,
        trigger: str = "cron",
        count: int = 5,
    ) -> Dict[str, Any]:
        """Preview next execution times for a scheduled task.

        Args:
            template: Task template name
            schedule: Schedule expression (cron or interval seconds)
            trigger: "cron" or "interval"
            count: Number of future executions to show

        Returns:
            Dict with preview information.
        """
        try:
            from datetime import datetime

            if trigger == "cron":
                from croniter import croniter

                cron = croniter(schedule)
                next_runs = []
                for _ in range(count):
                    next_time = cron.get_next(datetime)
                    next_runs.append(next_time.isoformat())

                return {
                    "template": template,
                    "trigger": trigger,
                    "schedule": schedule,
                    "next_executions": next_runs,
                    "valid": True,
                }
            else:
                # Interval
                try:
                    interval_seconds = int(schedule)
                    from time import time

                    now = time()
                    next_runs = [
                        datetime.fromtimestamp(now + interval_seconds * (i + 1)).isoformat()
                        for i in range(count)
                    ]

                    return {
                        "template": template,
                        "trigger": trigger,
                        "schedule": f"{interval_seconds} seconds",
                        "next_executions": next_runs,
                        "valid": True,
                    }
                except ValueError:
                    return {
                        "template": template,
                        "trigger": trigger,
                        "schedule": schedule,
                        "error": "Invalid interval (must be integer seconds)",
                        "valid": False,
                    }

        except Exception as e:
            return {
                "template": template,
                "trigger": trigger,
                "schedule": schedule,
                "error": str(e),
                "valid": False,
            }

    async def register_scheduled_task(
        self,
        name: str,
        template: str,
        schedule: str,
        trigger: str = "cron",
        description: str = "",
        actor_role: str = "default",
        cost_tier: str = "standard",
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a new scheduled task.

        Args:
            name: Task name
            template: Task template
            schedule: Schedule expression
            trigger: "cron" or "interval"
            description: Task description
            actor_role: Role to resolve actor
            cost_tier: Cost tier for actor resolution
            config: Task-specific configuration

        Returns:
            Dict with registration result.
        """
        import uuid

        task_id = f"task_{uuid.uuid4().hex[:8]}"

        try:
            trigger_type = TaskTrigger(trigger)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid trigger type: {trigger}",
            }

        task = ScheduledTask(
            id=task_id,
            name=name,
            description=description,
            trigger=trigger_type,
            schedule=schedule,
            enabled=True,
            actor_role=actor_role,
            cost_tier=cost_tier,
            task_template=template,
            task_config=config or {},
        )

        # Register with a no-op handler (will be replaced by actual executor)
        async def default_handler(task: ScheduledTask) -> None:
            """Default handler - logs the execution."""
            print(f"Executing scheduled task: {task.name} ({task.id})")

        self._task_runner.register_task(task, default_handler)

        return {
            "success": True,
            "task_id": task_id,
            "name": name,
            "template": template,
            "schedule": schedule,
            "trigger": trigger,
        }

    async def remove_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """Remove a scheduled task.

        Args:
            task_id: Task ID to remove

        Returns:
            Dict with removal result.
        """
        success = self._task_runner.unregister_task(task_id)

        if success:
            return {
                "success": True,
                "task_id": task_id,
                "message": "Task removed successfully",
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "error": "Task not found",
            }

    async def list_scheduled_tasks(self) -> Dict[str, Any]:
        """List all scheduled tasks.

        Returns:
            Dict with task list.
        """
        tasks = self._task_runner.list_tasks()

        task_list = []
        for task in tasks:
            task_list.append({
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
                "actor_role": task.actor_role,
                "cost_tier": task.cost_tier,
            })

        return {
            "tasks": task_list,
            "count": len(task_list),
        }

    async def enable_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """Enable a scheduled task.

        Args:
            task_id: Task ID to enable

        Returns:
            Dict with result.
        """
        success = self._task_runner.enable_task(task_id)

        return {
            "success": success,
            "task_id": task_id,
            "enabled": True,
        }

    async def disable_scheduled_task(self, task_id: str) -> Dict[str, Any]:
        """Disable a scheduled task.

        Args:
            task_id: Task ID to disable

        Returns:
            Dict with result.
        """
        success = self._task_runner.disable_task(task_id)

        return {
            "success": success,
            "task_id": task_id,
            "enabled": False,
        }


def get_schedule_tools(task_runner: TaskRunner) -> Dict[str, Any]:
    """Get all schedule tool handlers."""
    tools = ScheduleTools(task_runner)

    return {
        "list_schedule_templates": tools.list_schedule_templates,
        "preview_scheduled_task": tools.preview_scheduled_task,
        "register_scheduled_task": tools.register_scheduled_task,
        "remove_scheduled_task": tools.remove_scheduled_task,
        "list_scheduled_tasks": tools.list_scheduled_tasks,
        "enable_scheduled_task": tools.enable_scheduled_task,
        "disable_scheduled_task": tools.disable_scheduled_task,
    }
