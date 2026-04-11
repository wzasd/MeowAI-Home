"""QueueProcessor — consumes invocation queue with per-slot mutex."""
import logging
import threading
from typing import Dict, Optional, Set, Callable, Any
from src.invocation.queue import InvocationQueue, QueueEntry


logger = logging.getLogger(__name__)


ExecutionHandler = Callable[[QueueEntry], Any]


class QueueProcessor:
    """Consumes queue entries, manages per-slot (thread_id:cat_id) mutex.

    Features:
    - Per-slot mutex: thread_id:cat_id prevents concurrent execution
    - Pause-on-failure: slot paused on failure, others continue
    - Auto-execute: A2A dispatch triggers next execution
    """

    def __init__(
        self,
        queue: InvocationQueue,
        execution_handler: Optional[ExecutionHandler] = None,
    ):
        self._queue = queue
        self._execution_handler = execution_handler
        self._processing_slots: Set[str] = set()  # "thread_id:cat_id"
        self._paused_slots: Dict[str, str] = {}   # "thread_id:cat_id" -> reason
        self._slot_lock = threading.Lock()

    def try_execute_next(
        self,
        thread_id: str,
        user_id: str,
    ) -> Optional[QueueEntry]:
        """Try to dequeue and occupy a free slot.

        Returns:
            QueueEntry if found and slot occupied, None otherwise
        """
        with self._slot_lock:
            entry = self._queue.dequeue(thread_id, user_id)
            if entry is None:
                return None

            # Check if any target cat has a free slot
            for cat_id in entry.target_cats:
                slot_key = f"{thread_id}:{cat_id}"
                if self._is_slot_free_unsafe(slot_key):
                    self._processing_slots.add(slot_key)
                    return entry

            # No free slot - complete entry with error
            self._queue.complete_entry(
                entry.id,
                error="No free slot available (all targets busy or paused)",
            )
            return None

    def execute_entry(
        self,
        entry: QueueEntry,
        handler: Optional[ExecutionHandler] = None,
    ) -> bool:
        """Execute an entry and handle completion.

        Args:
            entry: Queue entry to execute
            handler: Optional override execution handler

        Returns:
            True if execution succeeded
        """
        exec_handler = handler or self._execution_handler
        if exec_handler is None:
            logger.error("No execution handler provided")
            self._mark_slots_complete(entry, succeeded=False)
            return False

        try:
            result = exec_handler(entry)
            self._queue.complete_entry(entry.id, result=result)
            self._mark_slots_complete(entry, succeeded=True)
            return True

        except Exception as e:
            logger.exception("Execution failed for entry %s", entry.id)
            self._queue.complete_entry(entry.id, error=str(e))
            self._mark_slots_complete(entry, succeeded=False)
            return False

    def _mark_slots_complete(self, entry: QueueEntry, succeeded: bool) -> None:
        """Mark slots as complete, pause on failure."""
        for cat_id in entry.target_cats:
            slot_key = f"{entry.thread_id}:{cat_id}"
            self.on_complete(entry.thread_id, cat_id, succeeded)

    def on_complete(self, thread_id: str, cat_id: str, succeeded: bool) -> None:
        """Mark slot as complete. On failure, pause the slot.

        Args:
            thread_id: Thread identifier
            cat_id: Cat identifier
            succeeded: Whether execution succeeded
        """
        slot_key = f"{thread_id}:{cat_id}"
        self._processing_slots.discard(slot_key)

        if not succeeded:
            self._paused_slots[slot_key] = "failed"
            logger.warning("Slot %s paused due to failure", slot_key)

    def resume_slot(self, thread_id: str, cat_id: str) -> bool:
        """Resume a paused slot.

        Returns:
            True if slot was paused and is now resumed
        """
        slot_key = f"{thread_id}:{cat_id}"
        if slot_key in self._paused_slots:
            del self._paused_slots[slot_key]
            logger.info("Slot %s resumed", slot_key)
            return True
        return False

    def is_slot_free(self, thread_id: str, cat_id: str) -> bool:
        """Check if slot is available (not processing and not paused)."""
        slot_key = f"{thread_id}:{cat_id}"
        return self._is_slot_free_unsafe(slot_key)

    def _is_slot_free_unsafe(self, slot_key: str) -> bool:
        """Check slot without acquiring lock."""
        return (
            slot_key not in self._processing_slots
            and slot_key not in self._paused_slots
        )

    def is_slot_paused(self, thread_id: str, cat_id: str) -> bool:
        """Check if slot is paused."""
        slot_key = f"{thread_id}:{cat_id}"
        return slot_key in self._paused_slots

    def get_slot_status(self, thread_id: str, cat_id: str) -> Dict[str, Any]:
        """Get status of a slot."""
        slot_key = f"{thread_id}:{cat_id}"

        if slot_key in self._processing_slots:
            return {"status": "processing"}
        elif slot_key in self._paused_slots:
            return {
                "status": "paused",
                "reason": self._paused_slots[slot_key],
            }
        else:
            return {"status": "free"}

    def get_paused_slots(self) -> Dict[str, str]:
        """Get all paused slots with reasons."""
        return dict(self._paused_slots)

    def process_next(
        self,
        thread_id: str,
        user_id: str,
        handler: Optional[ExecutionHandler] = None,
    ) -> Optional[Any]:
        """Process next entry from queue.

        Args:
            thread_id: Thread identifier
            user_id: User identifier
            handler: Optional execution handler

        Returns:
            Execution result if entry processed, None if queue empty
        """
        entry = self.try_execute_next(thread_id, user_id)
        if entry is None:
            return None

        success = self.execute_entry(entry, handler)
        if success:
            entry_data = self._queue.get_entry(entry.id)
            return entry_data.result if entry_data else None
        return None

    def auto_execute(
        self,
        thread_id: str,
        user_id: str,
        max_iterations: int = 10,
        handler: Optional[ExecutionHandler] = None,
    ) -> int:
        """Auto-execute entries from queue until empty or max iterations.

        Args:
            thread_id: Thread identifier
            user_id: User identifier
            max_iterations: Maximum number of entries to process
            handler: Optional execution handler

        Returns:
            Number of entries processed
        """
        count = 0
        for _ in range(max_iterations):
            result = self.process_next(thread_id, user_id, handler)
            if result is None:
                break
            count += 1

        return count
