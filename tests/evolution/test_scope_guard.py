"""Scope Guard tests"""
import pytest
import tempfile
from pathlib import Path
from src.memory import MemoryDB, EpisodicMemory
from src.evolution.scope_guard import ScopeGuard, DriftResult


@pytest.fixture
def episodic():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDB(str(Path(tmpdir) / "test.db"))
        yield EpisodicMemory(db)


class TestScopeGuardNoDrift:
    def test_no_drift_same_topic(self, episodic):
        episodic.store("t1", "user", "React React React component", importance=5)
        episodic.store("t1", "assistant", "React React React design", importance=5)
        guard = ScopeGuard(episodic, threshold=0.1)
        result = guard.check_drift("React state management", "t1")
        assert result.is_drift is False

    def test_empty_thread_no_drift(self, episodic):
        guard = ScopeGuard(episodic)
        result = guard.check_drift("hello", "empty_thread")
        assert result.is_drift is False

    def test_short_message_no_drift(self, episodic):
        episodic.store("t1", "user", "React 开发讨论", importance=5)
        guard = ScopeGuard(episodic)
        result = guard.check_drift("ok", "t1")
        assert result.is_drift is False


class TestScopeGuardDrift:
    def test_detects_drift(self, episodic):
        episodic.store("t1", "user", "我们讨论排序算法的时间复杂度", importance=5)
        episodic.store("t1", "assistant", "快速排序平均 O(n log n)...", importance=5)
        guard = ScopeGuard(episodic)
        result = guard.check_drift("今天中午吃什么好呢", "t1")
        assert result.is_drift is True
        assert result.similarity < 0.3

    def test_custom_threshold(self, episodic):
        episodic.store("t1", "user", "React 组件开发", importance=5)
        guard = ScopeGuard(episodic, threshold=0.8)
        result = guard.check_drift("Vue 的响应式系统", "t1")
        assert result.is_drift is True

    def test_drift_warning_format(self, episodic):
        guard = ScopeGuard(episodic)
        drift = DriftResult(is_drift=True, similarity=0.1, thread_topic="排序 算法", warning="", confidence=0.8)
        warning = guard.build_drift_warning(drift)
        assert "话题偏移" in warning
        assert "排序" in warning

    def test_no_warning_when_no_drift(self, episodic):
        guard = ScopeGuard(episodic)
        drift = DriftResult(is_drift=False, similarity=0.9, thread_topic="", warning="", confidence=0.9)
        assert guard.build_drift_warning(drift) == ""

    def test_recent_window_respected(self, episodic):
        # Store episodes with low importance about algorithms
        for i in range(5):
            episodic.store("t1", "user", f"algorithm sorting {i}", importance=1)
        # Last 2 episodes with higher importance about food
        episodic.store("t1", "user", "food food food", importance=10)
        episodic.store("t1", "user", "food dinner", importance=10)
        guard = ScopeGuard(episodic, threshold=0.1)
        # With window=2, topic should be about food (high importance), so food message not drift
        result = guard.check_drift("food is good", "t1", recent_window=2)
        assert result.is_drift is False
