import pytest
from src.invocation.tracker import InvocationTracker


class TestInvocationTracker:
    def test_start(self):
        tracker = InvocationTracker()
        controller = tracker.start("thread-1", "opus")
        assert controller is not None
        assert tracker.is_active("thread-1", "opus")

    def test_start_replaces_existing(self):
        tracker = InvocationTracker()
        old = tracker.start("thread-1", "opus")
        new = tracker.start("thread-1", "opus")
        assert old.is_cancelled()
        assert tracker.is_active("thread-1", "opus")

    def test_complete(self):
        tracker = InvocationTracker()
        ctrl = tracker.start("thread-1", "opus")
        tracker.complete("thread-1", "opus", ctrl)
        assert not tracker.is_active("thread-1", "opus")

    def test_cancel(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.cancel("thread-1", "opus")
        assert not tracker.is_active("thread-1", "opus")

    def test_cancel_all_for_thread(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.start("thread-1", "codex")
        tracker.cancel_all("thread-1")
        assert not tracker.is_active("thread-1", "opus")
        assert not tracker.is_active("thread-1", "codex")

    def test_different_threads_independent(self):
        tracker = InvocationTracker()
        tracker.start("thread-1", "opus")
        tracker.start("thread-2", "opus")
        tracker.cancel("thread-1", "opus")
        assert not tracker.is_active("thread-1", "opus")
        assert tracker.is_active("thread-2", "opus")

    def test_complete_wrong_controller_noop(self):
        tracker = InvocationTracker()
        ctrl1 = tracker.start("thread-1", "opus")
        ctrl2 = tracker.start("thread-1", "opus")  # replaces ctrl1
        tracker.complete("thread-1", "opus", ctrl1)  # wrong controller
        assert tracker.is_active("thread-1", "opus")  # still active
