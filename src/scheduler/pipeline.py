"""Pipeline — 7-step execution pipeline for scheduled tasks."""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Coroutine
import asyncio


class PipelineStep(str, Enum):
    ENABLED_CHECK = "enabled_check"
    GOVERNANCE = "governance"
    OVERLAP = "overlap"
    GATE = "gate"
    ACTOR_RESOLVE = "actor_resolve"
    EXECUTE = "execute"
    LEDGER = "ledger"


@dataclass
class PipelineContext:
    """Context passed through pipeline steps."""

    task_id: str
    task_name: str
    task_config: Dict[str, Any]
    actor_role: str
    cost_tier: str
    # Resolved during pipeline
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    execution_result: Optional[Any] = None
    error: Optional[str] = None
    # Metadata
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    step_times: Dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    task_id: str
    context: PipelineContext
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class ActorResolver:
    """Resolves role + cost_tier to specific cat_id."""

    def __init__(self, cat_registry=None):
        self._cat_registry = cat_registry
        self._role_mappings: Dict[str, List[str]] = {}

    def register_role_mapping(self, role: str, cat_ids: List[str]) -> None:
        """Register which cats can fulfill a role."""
        self._role_mappings[role] = cat_ids

    def resolve(
        self,
        role: str,
        cost_tier: str,
        exclude_ids: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Resolve actor for role and cost tier.

        Args:
            role: The required role (e.g., "researcher", "developer")
            cost_tier: Cost preference ("low", "standard", "high")
            exclude_ids: Cats to exclude (e.g., already tried)

        Returns:
            Selected cat_id or None if no match
        """
        exclude_ids = exclude_ids or []
        candidates = self._role_mappings.get(role, [])

        # Filter out excluded
        candidates = [c for c in candidates if c not in exclude_ids]

        if not candidates:
            return None

        # TODO: Implement cost-based selection when cat_registry has pricing
        # For now, return first available
        return candidates[0] if candidates else None


class EmissionGuard:
    """Prevents task from triggering itself (infinite loop prevention)."""

    def __init__(self, ttl_seconds: float = 300.0):
        self._recent_emissions: Dict[str, float] = {}
        self._ttl = ttl_seconds

    def check_and_record(self, task_id: str, target_thread: str) -> bool:
        """Check if this task recently emitted to the same thread.

        Returns:
            True if allowed, False if suppressed (recent emission)
        """
        key = f"{task_id}:{target_thread}"
        now = time.time()

        # Clean old entries
        self._cleanup(now)

        if key in self._recent_emissions:
            return False

        self._recent_emissions[key] = now
        return True

    def _cleanup(self, now: float) -> None:
        """Remove expired entries."""
        expired = [
            k for k, v in self._recent_emissions.items() if now - v > self._ttl
        ]
        for k in expired:
            del self._recent_emissions[k]


class PipelineLedger:
    """Records task execution history."""

    def __init__(self, max_entries: int = 1000):
        self._entries: List[Dict[str, Any]] = []
        self._max_entries = max_entries

    def record(self, result: PipelineResult) -> None:
        """Record a pipeline execution result."""
        entry = {
            "task_id": result.task_id,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": time.time(),
            "error": result.error,
            "actor_id": result.context.actor_id,
        }
        self._entries.append(entry)

        # Trim if needed
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def get_history(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get execution history."""
        if task_id:
            return [e for e in self._entries if e["task_id"] == task_id]
        return self._entries.copy()

    def get_stats(self, task_id: str) -> Dict[str, Any]:
        """Get execution statistics for a task."""
        entries = [e for e in self._entries if e["task_id"] == task_id]
        if not entries:
            return {"total": 0, "success_rate": 0.0}

        total = len(entries)
        successful = sum(1 for e in entries if e["success"])
        avg_time = sum(e["execution_time_ms"] for e in entries) / total

        return {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total,
            "avg_execution_time_ms": avg_time,
        }


class Pipeline:
    """7-step execution pipeline for scheduled tasks."""

    def __init__(
        self,
        actor_resolver: Optional[ActorResolver] = None,
        emission_guard: Optional[EmissionGuard] = None,
        ledger: Optional[PipelineLedger] = None,
        governance: Optional[Any] = None,
    ):
        self._actor_resolver = actor_resolver or ActorResolver()
        self._emission_guard = emission_guard or EmissionGuard()
        self._ledger = ledger or PipelineLedger()
        self._governance = governance
        self._overlap_flags: Dict[str, bool] = {}
        self._executors: Dict[str, Callable[[PipelineContext], Coroutine]] = {}

    def register_executor(
        self, template: str, executor: Callable[[PipelineContext], Coroutine]
    ) -> None:
        """Register an executor for a task template."""
        self._executors[template] = executor

    async def execute(self, task_config: Dict[str, Any]) -> PipelineResult:
        """Execute task through 7-step pipeline.

        Steps:
        1. ENABLED_CHECK - Task is enabled
        2. GOVERNANCE - Global/per-task governance allows
        3. OVERLAP - No overlapping execution
        4. GATE - Emission guard (prevent self-triggering)
        5. ACTOR_RESOLVE - Resolve role to cat_id
        6. EXECUTE - Run the task
        7. LEDGER - Record execution
        """
        task_id = task_config.get("id", "unknown")
        task_name = task_config.get("name", "Unknown Task")
        actor_role = task_config.get("actor_role", "default")
        cost_tier = task_config.get("cost_tier", "standard")
        template = task_config.get("task_template", "default")

        context = PipelineContext(
            task_id=task_id,
            task_name=task_name,
            task_config=task_config.get("config", {}),
            actor_role=actor_role,
            cost_tier=cost_tier,
            started_at=time.time(),
        )

        try:
            # Step 1: ENABLED_CHECK
            if not task_config.get("enabled", True):
                raise PipelineError("Task is disabled", PipelineStep.ENABLED_CHECK)
            context.step_times["enabled_check"] = time.time()

            # Step 2: GOVERNANCE
            if self._governance and hasattr(self._governance, "is_paused"):
                if self._governance.is_paused():
                    raise PipelineError(
                        "Execution paused by governance", PipelineStep.GOVERNANCE
                    )
                if hasattr(self._governance, "is_task_enabled"):
                    if not self._governance.is_task_enabled(task_id):
                        raise PipelineError(
                            "Task disabled by governance", PipelineStep.GOVERNANCE
                        )
            context.step_times["governance"] = time.time()

            # Step 3: OVERLAP
            if self._overlap_flags.get(task_id, False):
                raise PipelineError(
                    "Task already running (overlap guard)", PipelineStep.OVERLAP
                )
            self._overlap_flags[task_id] = True
            context.step_times["overlap"] = time.time()

            # Step 4: GATE
            target_thread = task_config.get("target_thread")
            if target_thread:
                if not self._emission_guard.check_and_record(task_id, target_thread):
                    raise PipelineError(
                        "Emission suppressed (recent trigger)", PipelineStep.GATE
                    )
            context.step_times["gate"] = time.time()

            # Step 5: ACTOR_RESOLVE
            actor_id = self._actor_resolver.resolve(actor_role, cost_tier)
            if not actor_id:
                raise PipelineError(
                    f"No actor found for role: {actor_role}", PipelineStep.ACTOR_RESOLVE
                )
            context.actor_id = actor_id
            context.actor_name = actor_id  # TODO: Get display name
            context.step_times["actor_resolve"] = time.time()

            # Step 6: EXECUTE
            executor = self._executors.get(template)
            if not executor:
                raise PipelineError(
                    f"No executor for template: {template}", PipelineStep.EXECUTE
                )

            context.execution_result = await executor(context)
            context.step_times["execute"] = time.time()

            # Step 7: LEDGER
            context.completed_at = time.time()
            execution_time_ms = (context.completed_at - context.started_at) * 1000

            result = PipelineResult(
                success=True,
                task_id=task_id,
                context=context,
                execution_time_ms=execution_time_ms,
            )
            self._ledger.record(result)
            context.step_times["ledger"] = time.time()

            return result

        except PipelineError as e:
            context.error = str(e)
            context.completed_at = time.time()
            execution_time_ms = (context.completed_at - context.started_at) * 1000

            result = PipelineResult(
                success=False,
                task_id=task_id,
                context=context,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
            self._ledger.record(result)
            return result

        except Exception as e:
            context.error = str(e)
            context.completed_at = time.time()
            execution_time_ms = (context.completed_at - context.started_at) * 1000

            result = PipelineResult(
                success=False,
                task_id=task_id,
                context=context,
                error=f"Unexpected error: {e}",
                execution_time_ms=execution_time_ms,
            )
            self._ledger.record(result)
            return result

        finally:
            # Clear overlap flag
            self._overlap_flags[task_id] = False

    def get_stats(self, task_id: str) -> Dict[str, Any]:
        """Get execution statistics for a task."""
        return self._ledger.get_stats(task_id)

    def get_history(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self._ledger.get_history(task_id)


class PipelineError(Exception):
    """Error during pipeline execution."""

    def __init__(self, message: str, step: PipelineStep):
        super().__init__(message)
        self.step = step
        self.message = message
