"""Tests for SessionManager (B2)."""
import time
import pytest
from unittest.mock import MagicMock

from src.session.manager import SessionManager, Session, SessionStatus


@pytest.fixture
def manager(tmp_path):
    db_path = str(tmp_path / "sessions.db")
    return SessionManager(db_path=db_path)


class TestSessionCreation:
    def test_create_session(self, manager):
        session = manager.create(
            user_id="u1", cat_id="orange", thread_id="t1", session_id="s1"
        )
        assert session.user_id == "u1"
        assert session.cat_id == "orange"
        assert session.thread_id == "t1"
        assert session.session_id == "s1"
        assert session.status == SessionStatus.ACTIVE

    def test_create_generates_timestamp(self, manager):
        before = time.time()
        session = manager.create(
            user_id="u1", cat_id="orange", thread_id="t1", session_id="s1"
        )
        after = time.time()
        assert before <= session.created_at <= after

    def test_duplicate_session_id_raises(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        with pytest.raises(ValueError):
            manager.create(user_id="u2", cat_id="inky", thread_id="t2", session_id="s1")


class TestSessionGet:
    def test_get_existing_session(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        session = manager.get("s1")
        assert session is not None
        assert session.cat_id == "orange"

    def test_get_nonexistent_returns_none(self, manager):
        assert manager.get("nonexistent") is None

    def test_get_by_key(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        session = manager.get_by_key(user_id="u1", cat_id="orange", thread_id="t1")
        assert session is not None
        assert session.session_id == "s1"

    def test_get_by_key_returns_active(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        # Create a new active session (old one gets sealed)
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s2")
        session = manager.get_by_key(user_id="u1", cat_id="orange", thread_id="t1")
        assert session.session_id == "s2"


class TestSessionStatus:
    def test_seal_session(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.seal("s1")
        session = manager.get("s1")
        assert session.status == SessionStatus.SEALED

    def test_seal_transition_through_sealing(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.update_status("s1", SessionStatus.SEALING)
        session = manager.get("s1")
        assert session.status == SessionStatus.SEALING

    def test_get_active_only_returns_active(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.seal("s1")
        active = manager.get_by_key(user_id="u1", cat_id="orange", thread_id="t1")
        assert active is None


class TestSessionDelete:
    def test_delete_session(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.delete("s1")
        assert manager.get("s1") is None

    def test_delete_nonexistent_noop(self, manager):
        manager.delete("nonexistent")  # Should not raise


class TestReconcileStuckSessions:
    def test_reconcile_seals_stuck_sealing(self, manager):
        import sqlite3
        session = manager.create(
            user_id="u1", cat_id="orange", thread_id="t1", session_id="s1"
        )
        manager.update_status("s1", SessionStatus.SEALING)
        # Manually update seal_started_at to simulate old session
        with sqlite3.connect(manager._db_path) as conn:
            conn.execute(
                "UPDATE sessions SET seal_started_at = ? WHERE session_id = ?",
                (time.time() - 400, "s1")
            )
            conn.commit()

        count = manager.reconcile_stuck(threshold_seconds=300)
        assert count == 1

        session = manager.get("s1")
        assert session.status == SessionStatus.SEALED

    def test_reconcile_ignores_recent_sealing(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.update_status("s1", SessionStatus.SEALING)
        # Sealing just started

        count = manager.reconcile_stuck(threshold_seconds=300)
        assert count == 0

    def test_reconcile_ignores_active(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        # Session is active, not stuck

        count = manager.reconcile_stuck(threshold_seconds=300)
        assert count == 0


class TestSessionPersistence:
    def test_sessions_persist_across_instances(self, tmp_path):
        db_path = str(tmp_path / "sessions.db")
        manager1 = SessionManager(db_path=db_path)
        manager1.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")

        # Create new instance
        manager2 = SessionManager(db_path=db_path)
        session = manager2.get("s1")
        assert session is not None
        assert session.cat_id == "orange"

    def test_list_sessions_by_thread(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.create(user_id="u1", cat_id="inky", thread_id="t1", session_id="s2")
        manager.create(user_id="u1", cat_id="orange", thread_id="t2", session_id="s3")

        sessions = manager.list_by_thread("t1")
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert session_ids == {"s1", "s2"}

    def test_list_sessions_by_cat(self, manager):
        manager.create(user_id="u1", cat_id="orange", thread_id="t1", session_id="s1")
        manager.create(user_id="u1", cat_id="orange", thread_id="t2", session_id="s2")
        manager.create(user_id="u1", cat_id="inky", thread_id="t1", session_id="s3")

        sessions = manager.list_by_cat("orange")
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert session_ids == {"s1", "s2"}
