"""Skill chain execution tests"""
import pytest
from src.skills.chain import ChainContext, ChainTracker


class TestChainContext:
    def test_creation(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd", "debug"])
        assert ctx.thread_id == "t1"
        assert ctx.chain_id == "c123"
        assert ctx.skills == ["tdd", "debug"]
        assert ctx.current_index == 0

    def test_current_skill_first(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd", "debug", "test"])
        assert ctx.current_skill == "tdd"

    def test_current_skill_advance(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd", "debug"])
        ctx.advance({"output": "ok"})
        assert ctx.current_skill == "debug"

    def test_current_skill_complete(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd"])
        ctx.advance({"output": "ok"})
        assert ctx.current_skill is None

    def test_is_complete_false(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd", "debug"])
        assert ctx.is_complete is False

    def test_is_complete_true(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["tdd"])
        ctx.advance({"output": "ok"})
        assert ctx.is_complete is True

    def test_results_accumulate(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["a", "b"])
        ctx.advance({"r1": "x"})
        ctx.advance({"r2": "y"})
        assert len(ctx.results) == 2
        assert ctx.results == [{"r1": "x"}, {"r2": "y"}]

    def test_metadata_preserved(self):
        ctx = ChainContext(thread_id="t1", chain_id="c123", skills=["a"],
                          metadata={"user": "alice", "priority": 5})
        ctx.advance({"r": "ok"})
        assert ctx.metadata == {"user": "alice", "priority": 5}


class TestChainTrackerStart:
    def test_start_chain(self):
        tracker = ChainTracker()
        chain = tracker.start_chain("t1", ["tdd", "debug"])
        assert chain.thread_id == "t1"
        assert chain.skills == ["tdd", "debug"]
        assert chain.chain_id is not None

    def test_exceeds_max_depth_raises(self):
        tracker = ChainTracker(max_depth=3)
        with pytest.raises(ValueError, match="exceeds max"):
            tracker.start_chain("t1", ["a", "b", "c", "d"])

    def test_exactly_max_depth_ok(self):
        tracker = ChainTracker(max_depth=3)
        chain = tracker.start_chain("t1", ["a", "b", "c"])
        assert chain.skills == ["a", "b", "c"]


class TestChainTrackerGetActive:
    def test_get_active_returns_chain(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a", "b"])
        active = tracker.get_active("t1")
        assert active is not None
        assert active.thread_id == "t1"

    def test_get_active_no_chain(self):
        tracker = ChainTracker()
        assert tracker.get_active("t1") is None

    def test_get_active_completed_chain(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a"])
        tracker.advance("t1", {"r": "ok"})
        assert tracker.get_active("t1") is None


class TestChainTrackerAdvance:
    def test_advance_moves_to_next(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a", "b", "c"])
        chain = tracker.advance("t1", {"r1": "x"})
        assert chain.current_skill == "b"

    def test_advance_removes_completed(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a"])
        chain = tracker.advance("t1", {"r": "ok"})
        assert chain is None  # Completed chain removed

    def test_advance_nonexistent_thread(self):
        tracker = ChainTracker()
        assert tracker.advance("t1", {"r": "x"}) is None


class TestChainTrackerMultipleThreads:
    def test_multiple_threads_independent(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a", "b"])
        tracker.start_chain("t2", ["c", "d"])
        assert tracker.get_active("t1").skills == ["a", "b"]
        assert tracker.get_active("t2").skills == ["c", "d"]


class TestChainTrackerCancel:
    def test_cancel_removes_chain(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a", "b"])
        assert tracker.cancel_chain("t1") is True
        assert tracker.get_active("t1") is None

    def test_cancel_no_chain(self):
        tracker = ChainTracker()
        assert tracker.cancel_chain("t1") is False

    def test_list_active(self):
        tracker = ChainTracker()
        tracker.start_chain("t1", ["a"])
        tracker.start_chain("t2", ["b"])
        assert sorted(tracker.list_active()) == ["t1", "t2"]
