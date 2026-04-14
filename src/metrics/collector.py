import asyncio
import time
from typing import Optional
from dataclasses import dataclass


@dataclass
class InvocationRecord:
    cat_id: str
    thread_id: Optional[str]
    project_path: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    duration_ms: int = 0


class MetricsCollector:
    """调用指标采集器"""

    def __init__(self, store=None):
        from src.metrics.sqlite_store import MetricsSQLiteStore
        self._store = store or MetricsSQLiteStore()
        self._starts: dict[str, float] = {}

    def record_start(self, invocation_id: str) -> None:
        self._starts[invocation_id] = time.time()

    async def record_finish(self, invocation_id: str, record: InvocationRecord) -> None:
        start = self._starts.pop(invocation_id, None)
        if start:
            record.duration_ms = int((time.time() - start) * 1000)
        try:
            await self._store.save(record)
        except Exception:
            pass
