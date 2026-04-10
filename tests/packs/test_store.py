"""Pack store tests"""
import pytest
import tempfile
from pathlib import Path
from src.packs.store import PackStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield PackStore(str(Path(tmpdir) / "packs.db"))


class TestPackStoreActivate:
    def test_activate_creates_record(self, store):
        aid = store.activate("tdd-pack", "thread-1", ["tester", "implementer"])
        assert aid > 0

    def test_activate_same_pack_thread_updates(self, store):
        aid1 = store.activate("tdd-pack", "thread-1", ["a", "b"])
        aid2 = store.activate("tdd-pack", "thread-1", ["c", "d"])
        # Should update existing record
        active = store.get_active("thread-1")
        assert len(active) == 1
        assert active[0]["agents"] == ["c", "d"]

    def test_activate_different_threads(self, store):
        store.activate("tdd-pack", "thread-1", ["a"])
        store.activate("tdd-pack", "thread-2", ["b"])
        assert len(store.list_all_active()) == 2


class TestPackStoreDeactivate:
    def test_deactivate_existing(self, store):
        store.activate("tdd-pack", "thread-1", ["a"])
        assert store.deactivate("tdd-pack", "thread-1") is True
        assert store.get_active("thread-1") == []

    def test_deactivate_nonexistent(self, store):
        assert store.deactivate("missing", "thread-1") is False


class TestPackStoreGetActive:
    def test_get_active_returns_list(self, store):
        store.activate("pack-1", "t1", ["a", "b"])
        store.activate("pack-2", "t1", ["c"])
        active = store.get_active("t1")
        assert len(active) == 2
        names = {a["pack_name"] for a in active}
        assert names == {"pack-1", "pack-2"}

    def test_get_active_no_packs(self, store):
        assert store.get_active("t1") == []

    def test_get_active_includes_agents(self, store):
        store.activate("pack-1", "t1", ["agent-1", "agent-2"])
        active = store.get_active("t1")
        assert active[0]["agents"] == ["agent-1", "agent-2"]


class TestPackStoreIsActive:
    def test_is_active_true(self, store):
        store.activate("pack-1", "t1", ["a"])
        assert store.is_active("pack-1", "t1") is True

    def test_is_active_false(self, store):
        assert store.is_active("pack-1", "t1") is False


class TestPackStoreListAll:
    def test_list_all_active(self, store):
        store.activate("pack-1", "t1", ["a"])
        store.activate("pack-2", "t2", ["b"])
        all_active = store.list_all_active()
        assert len(all_active) == 2

    def test_list_all_empty(self, store):
        assert store.list_all_active() == []
