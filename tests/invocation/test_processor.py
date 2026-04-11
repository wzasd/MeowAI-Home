"""Tests for QueueProcessor (A2)."""
import time
import pytest
from src.invocation.queue import InvocationQueue
from src.invocation.processor import QueueProcessor


class TestTryExecuteNext:
    def test_success_dequeues_and_occupies_slot(self):
        q = InvocationQueue()
        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        proc = QueueProcessor(q)
        entry = proc.try_execute_next("t1", "u1")
        assert entry is not None
        assert entry.status == "processing"
        assert "t1:opus" in proc._processing_slots

    def test_returns_none_when_queue_empty(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        result = proc.try_execute_next("t1", "u1")
        assert result is None

    def test_multi_cat_entry_occupies_first_free_slot(self):
        q = InvocationQueue()
        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus", "sonnet"], source="user", intent="execute",
        )
        proc = QueueProcessor(q)
        entry = proc.try_execute_next("t1", "u1")
        assert entry is not None
        # Should have exactly one slot occupied (the first free one)
        assert len(proc._processing_slots) == 1

    def test_all_slots_busy_returns_none(self):
        """When all target_cats slots are busy, return None."""
        q = InvocationQueue()
        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        proc = QueueProcessor(q)
        # Manually occupy the slot
        proc._processing_slots.add("t1:opus")
        result = proc.try_execute_next("t1", "u1")
        assert result is None


class TestPausedSlots:
    def test_paused_slot_blocks_execution(self):
        q = InvocationQueue()
        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        proc = QueueProcessor(q)
        proc._paused_slots["t1:opus"] = "failed"
        result = proc.try_execute_next("t1", "u1")
        assert result is None

    def test_paused_slot_skipped_multi_cat(self):
        """With multi-cat entry, paused cat is skipped, next cat taken."""
        q = InvocationQueue()
        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus", "sonnet"], source="user", intent="execute",
        )
        proc = QueueProcessor(q)
        proc._paused_slots["t1:opus"] = "failed"
        entry = proc.try_execute_next("t1", "u1")
        assert entry is not None
        assert "t1:sonnet" in proc._processing_slots
        assert "t1:opus" not in proc._processing_slots


class TestOnComplete:
    def test_success_frees_slot(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        proc._processing_slots.add("t1:opus")
        proc.on_complete("t1", "opus", succeeded=True)
        assert "t1:opus" not in proc._processing_slots
        assert "t1:opus" not in proc._paused_slots

    def test_failure_pauses_slot(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        proc._processing_slots.add("t1:opus")
        proc.on_complete("t1", "opus", succeeded=False)
        assert "t1:opus" not in proc._processing_slots
        assert "t1:opus" in proc._paused_slots
        assert proc._paused_slots["t1:opus"] == "failed"

    def test_complete_nonexistent_slot_is_noop(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        proc.on_complete("t1", "opus", succeeded=True)
        # Should not raise
        assert len(proc._processing_slots) == 0
        assert len(proc._paused_slots) == 0


class TestIsSlotFree:
    def test_free_slot(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        assert proc.is_slot_free("t1", "opus") is True

    def test_busy_slot(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        proc._processing_slots.add("t1:opus")
        assert proc.is_slot_free("t1", "opus") is False

    def test_paused_slot(self):
        q = InvocationQueue()
        proc = QueueProcessor(q)
        proc._paused_slots["t1:opus"] = "failed"
        assert proc.is_slot_free("t1", "opus") is False


class TestProcessorIntegration:
    def test_full_lifecycle_enqueue_execute_complete(self):
        """Full cycle: enqueue -> execute -> complete -> slot freed."""
        q = InvocationQueue()
        proc = QueueProcessor(q)

        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        entry = proc.try_execute_next("t1", "u1")
        assert entry is not None
        assert not proc.is_slot_free("t1", "opus")

        proc.on_complete("t1", "opus", succeeded=True)
        assert proc.is_slot_free("t1", "opus")

    def test_failure_then_retry_blocked(self):
        """After failure, slot is paused and blocks retry."""
        q = InvocationQueue()
        proc = QueueProcessor(q)

        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        entry = proc.try_execute_next("t1", "u1")
        proc.on_complete("t1", "opus", succeeded=False)

        # Enqueue another message for same cat
        q.enqueue(
            thread_id="t1", user_id="u1", content="retry",
            target_cats=["opus"], source="user", intent="execute",
        )
        result = proc.try_execute_next("t1", "u1")
        assert result is None  # blocked by paused slot

    def test_independent_threads_dont_interfere(self):
        """Slots for different threads are independent."""
        q = InvocationQueue()
        proc = QueueProcessor(q)

        q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        q.enqueue(
            thread_id="t2", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )

        e1 = proc.try_execute_next("t1", "u1")
        e2 = proc.try_execute_next("t2", "u1")
        assert e1 is not None
        assert e2 is not None
        assert not proc.is_slot_free("t1", "opus")
        assert not proc.is_slot_free("t2", "opus")
        assert proc.is_slot_free("t1", "sonnet")  # different cat
