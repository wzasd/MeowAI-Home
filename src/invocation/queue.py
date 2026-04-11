"""Invocation queue — per-thread FIFO with tail merge and stale cleanup."""
import time
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class QueueStatus(str, Enum):
    """Status of a queue entry."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueEntry:
    """An entry in the invocation queue."""
    id: str
    thread_id: str
    user_id: str
    content: str
    target_cats: List[str]
    status: str  # "queued" | "processing"
    created_at: float
    source: str  # "user" | "connector" | "agent"
    intent: str  # "execute" | "ideate"
    merged_message_ids: List[str] = field(default_factory=list)
    processing_started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at

    @property
    def processing_time_seconds(self) -> float:
        """Get processing time if started."""
        if not self.processing_started_at:
            return 0.0
        end_time = self.completed_at or time.time()
        return end_time - self.processing_started_at


@dataclass
class EnqueueResult:
    outcome: str  # "enqueued" | "merged" | "full"
    entry: Optional[QueueEntry] = None
    queue_position: int = 0


DEFAULT_MAX_DEPTH = 5
DEFAULT_STALE_QUEUED_SECONDS = 60.0     # 1 minute
DEFAULT_STALE_PROCESSING_SECONDS = 600.0  # 10 minutes


class InvocationQueue:
    """Per-thread FIFO invocation queue with tail merge."""

    def __init__(
        self,
        max_depth: int = DEFAULT_MAX_DEPTH,
        stale_queued_seconds: float = DEFAULT_STALE_QUEUED_SECONDS,
        stale_processing_seconds: float = DEFAULT_STALE_PROCESSING_SECONDS,
    ):
        self._max_depth = max_depth
        self._stale_queued_seconds = stale_queued_seconds
        self._stale_processing_seconds = stale_processing_seconds
        self._queues: Dict[str, List[QueueEntry]] = {}  # "thread_id:user_id" -> list
        self._lock = threading.RLock()
        self._last_cleanup = time.time()
        self._cleanup_interval = 30.0

    def _key(self, thread_id: str, user_id: str) -> str:
        return f"{thread_id}:{user_id}"

    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self.cleanup_stale()
        self._last_cleanup = now

    def enqueue(
        self,
        thread_id: str,
        user_id: str,
        content: str,
        target_cats: List[str],
        source: str,
        intent: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnqueueResult:
        """Add entry to queue with tail merge."""
        self._maybe_cleanup()

        with self._lock:
            key = self._key(thread_id, user_id)
            queue = self._queues.setdefault(key, [])

            # Try tail merge
            if queue:
                tail = queue[-1]
                if (
                    tail.status == QueueStatus.QUEUED.value
                    and tail.source == source
                    and tail.intent == intent
                    and tail.target_cats == target_cats
                    and source != "connector"
                ):
                    tail.content += f"\n{content}"
                    tail.merged_message_ids.append(str(uuid.uuid4())[:8])
                    tail.metadata["last_merge_at"] = time.time()
                    return EnqueueResult(outcome="merged", entry=tail)

            # Capacity check
            queued_count = sum(1 for e in queue if e.status == QueueStatus.QUEUED.value)
            if queued_count >= self._max_depth:
                return EnqueueResult(outcome="full")

            # Create new entry
            entry = QueueEntry(
                id=str(uuid.uuid4())[:8],
                thread_id=thread_id,
                user_id=user_id,
                content=content,
                target_cats=target_cats,
                status=QueueStatus.QUEUED.value,
                created_at=time.time(),
                source=source,
                intent=intent,
                metadata=metadata or {},
            )
            queue.append(entry)
            return EnqueueResult(outcome="enqueued", entry=entry, queue_position=queued_count)

    def dequeue(self, thread_id: str, user_id: str) -> Optional[QueueEntry]:
        """Get next pending entry from queue."""
        self._maybe_cleanup()

        with self._lock:
            key = self._key(thread_id, user_id)
            queue = self._queues.get(key, [])
            for entry in queue:
                if entry.status == QueueStatus.QUEUED.value:
                    entry.status = QueueStatus.PROCESSING.value
                    entry.processing_started_at = time.time()
                    return entry
            return None

    def complete_entry(
        self,
        entry_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """Mark entry as completed or failed."""
        with self._lock:
            for queue in self._queues.values():
                for entry in queue:
                    if entry.id == entry_id:
                        entry.completed_at = time.time()
                        if error:
                            entry.status = QueueStatus.FAILED.value
                            entry.error = error
                        else:
                            entry.status = QueueStatus.COMPLETED.value
                            entry.result = result
                        return True
            return False

    def cancel_entry(self, entry_id: str) -> bool:
        """Cancel a pending entry."""
        with self._lock:
            for queue in self._queues.values():
                for entry in queue:
                    if entry.id == entry_id:
                        if entry.status == QueueStatus.QUEUED.value:
                            entry.status = QueueStatus.CANCELLED.value
                            entry.completed_at = time.time()
                            return True
                        return False
            return False

    def get_entry(self, entry_id: str) -> Optional[QueueEntry]:
        """Get entry by ID."""
        with self._lock:
            for queue in self._queues.values():
                for entry in queue:
                    if entry.id == entry_id:
                        return entry
            return None

    def remove(self, entry_id: str, thread_id: str, user_id: str) -> bool:
        """Remove entry from queue."""
        with self._lock:
            key = self._key(thread_id, user_id)
            queue = self._queues.get(key, [])
            for i, entry in enumerate(queue):
                if entry.id == entry_id:
                    queue.pop(i)
                    return True
            return False

    def get_queue_depth(self, thread_id: str, user_id: str) -> int:
        """Get number of queued entries."""
        with self._lock:
            key = self._key(thread_id, user_id)
            return sum(1 for e in self._queues.get(key, []) if e.status == QueueStatus.QUEUED.value)

    def list_entries(
        self,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[QueueEntry]:
        """List entries with optional filtering."""
        with self._lock:
            results = []

            if thread_id and user_id:
                key = self._key(thread_id, user_id)
                queues = [(key, self._queues.get(key, []))]
            elif thread_id:
                # Find all entries for this thread across users
                queues = [
                    (k, v) for k, v in self._queues.items()
                    if k.startswith(f"{thread_id}:")
                ]
            else:
                queues = list(self._queues.items())

            for key, queue in queues:
                for entry in queue:
                    if status is None or entry.status == status:
                        results.append(entry)

            return results

    def get_stats(self, thread_id: str, user_id: str) -> Dict[str, Any]:
        """Get statistics for a queue."""
        with self._lock:
            key = self._key(thread_id, user_id)
            queue = self._queues.get(key, [])

            return {
                "thread_id": thread_id,
                "user_id": user_id,
                "total_entries": len(queue),
                "queued": sum(1 for e in queue if e.status == QueueStatus.QUEUED.value),
                "processing": sum(1 for e in queue if e.status == QueueStatus.PROCESSING.value),
                "completed": sum(1 for e in queue if e.status == QueueStatus.COMPLETED.value),
                "failed": sum(1 for e in queue if e.status == QueueStatus.FAILED.value),
                "max_depth": self._max_depth,
            }

    def clear_completed(self, thread_id: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Clear completed/failed/cancelled entries."""
        with self._lock:
            cleared = 0

            if thread_id and user_id:
                keys = [self._key(thread_id, user_id)]
            elif thread_id:
                keys = [k for k in self._queues.keys() if k.startswith(f"{thread_id}:")]
            else:
                keys = list(self._queues.keys())

            for key in keys:
                if key not in self._queues:
                    continue

                queue = self._queues[key]
                original_len = len(queue)
                self._queues[key] = [
                    e for e in queue
                    if e.status not in (QueueStatus.COMPLETED.value, QueueStatus.FAILED.value, QueueStatus.CANCELLED.value)
                ]
                cleared += original_len - len(self._queues[key])

                if not self._queues[key]:
                    del self._queues[key]

            return cleared

    def cleanup_stale(self) -> int:
        """Clean up stale entries."""
        now = time.time()
        stale_count = 0

        with self._lock:
            for key in list(self._queues.keys()):
                queue = self._queues[key]
                for entry in queue:
                    if entry.status == QueueStatus.QUEUED.value:
                        if now - entry.created_at > self._stale_queued_seconds:
                            entry.status = QueueStatus.FAILED.value
                            entry.error = "Stale entry: queued too long"
                            entry.completed_at = now
                            stale_count += 1
                    elif entry.status == QueueStatus.PROCESSING.value:
                        if entry.processing_started_at and now - entry.processing_started_at > self._stale_processing_seconds:
                            entry.status = QueueStatus.FAILED.value
                            entry.error = "Stale entry: processing timeout"
                            entry.completed_at = now
                            stale_count += 1

                # Remove empty queues
                if not queue:
                    del self._queues[key]

        return stale_count
