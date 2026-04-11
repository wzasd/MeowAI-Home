"""Tests for InvocationQueue."""
import time
import pytest
from src.invocation.queue import InvocationQueue, QueueEntry, EnqueueResult


def make_entry(**overrides):
    defaults = dict(
        id="test-id",
        thread_id="t1",
        user_id="u1",
        content="hello",
        target_cats=["opus"],
        status="queued",
        created_at=time.time(),
        source="user",
        intent="execute",
    )
    defaults.update(overrides)
    return QueueEntry(**defaults)


class TestQueueEntry:
    def test_create_entry(self):
        entry = make_entry()
        assert entry.thread_id == "t1"
        assert entry.target_cats == ["opus"]

    def test_entry_with_multiple_cats(self):
        entry = make_entry(target_cats=["opus", "sonnet"])
        assert len(entry.target_cats) == 2


class TestEnqueue:
    def test_enqueue_new_entry(self):
        q = InvocationQueue()
        result = q.enqueue(
            thread_id="t1", user_id="u1", content="hello",
            target_cats=["opus"], source="user", intent="execute",
        )
        assert result.outcome == "enqueued"
        assert result.entry is not None
        assert result.queue_position == 0

    def test_enqueue_returns_position(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u1", content="msg2",
                           target_cats=["sonnet"], source="user", intent="execute")
        assert result.outcome == "enqueued"
        assert result.queue_position == 1

    def test_tail_merge_same_source_intent_targets(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u1", content="msg2",
                           target_cats=["opus"], source="user", intent="execute")
        assert result.outcome == "merged"
        assert "msg1" in result.entry.content
        assert "msg2" in result.entry.content

    def test_no_merge_different_source(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u2", content="msg2",
                           target_cats=["opus"], source="connector", intent="execute")
        assert result.outcome == "enqueued"

    def test_no_merge_different_intent(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u1", content="msg2",
                           target_cats=["opus"], source="user", intent="ideate")
        assert result.outcome == "enqueued"

    def test_no_merge_different_targets(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u1", content="msg2",
                           target_cats=["sonnet"], source="user", intent="execute")
        assert result.outcome == "enqueued"

    def test_queue_full_at_max_depth(self):
        q = InvocationQueue()
        for i in range(5):
            q.enqueue(thread_id="t1", user_id="u1", content=f"msg{i}",
                      target_cats=[f"cat{i}"], source="user", intent="execute")
        result = q.enqueue(thread_id="t1", user_id="u1", content="overflow",
                           target_cats=["opus"], source="user", intent="execute")
        assert result.outcome == "full"

    def test_different_threads_independent_queues(self):
        q = InvocationQueue()
        r1 = q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                       target_cats=["opus"], source="user", intent="execute")
        r2 = q.enqueue(thread_id="t2", user_id="u1", content="msg2",
                       target_cats=["opus"], source="user", intent="execute")
        assert r1.outcome == "enqueued"
        assert r2.outcome == "enqueued"
        assert r1.entry.id != r2.entry.id


class TestDequeue:
    def test_dequeue_fifo_order(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="first",
                  target_cats=["opus"], source="user", intent="execute")
        q.enqueue(thread_id="t1", user_id="u1", content="second",
                  target_cats=["sonnet"], source="user", intent="execute")
        entry = q.dequeue("t1", "u1")
        assert entry is not None
        assert entry.content == "first"

    def test_dequeue_empty_queue(self):
        q = InvocationQueue()
        result = q.dequeue("t1", "u1")
        assert result is None

    def test_dequeue_marks_processing(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg",
                  target_cats=["opus"], source="user", intent="execute")
        entry = q.dequeue("t1", "u1")
        assert entry.status == "processing"

    def test_dequeue_skips_already_processing(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="msg1",
                  target_cats=["opus"], source="user", intent="execute")
        first = q.dequeue("t1", "u1")
        assert first is not None
        second = q.dequeue("t1", "u1")
        assert second is None


class TestStaleCleanup:
    def test_stale_queued_entries_marked_failed(self):
        q = InvocationQueue()
        entry = make_entry(created_at=time.time() - 120)  # 2 min old
        q._queues["t1:u1"] = [entry]
        q.cleanup_stale()
        # Entry marked as failed, not removed (for audit)
        assert entry.status == "failed"
        assert "stale" in entry.error.lower()

    def test_recent_entries_kept(self):
        q = InvocationQueue()
        q.enqueue(thread_id="t1", user_id="u1", content="fresh",
                  target_cats=["opus"], source="user", intent="execute")
        q.cleanup_stale()
        assert len(q._queues.get("t1:u1", [])) == 1

    def test_stale_processing_entries_marked_failed(self):
        q = InvocationQueue()
        entry = make_entry(status="processing", created_at=time.time() - 700,
                           processing_started_at=time.time() - 700)
        q._queues["t1:u1"] = [entry]
        q.cleanup_stale()
        # Entry marked as failed, not removed (for audit)
        assert entry.status == "failed"
        assert "stale" in entry.error.lower()
