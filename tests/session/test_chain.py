import pytest
from src.session.chain import SessionChain, SessionRecord, SessionStatus


class TestSessionChain:
    def test_create_chain(self):
        chain = SessionChain()
        record = chain.create("opus", "thread-1", "session-abc")
        assert record.cat_id == "opus"
        assert record.session_id == "session-abc"
        assert record.status == SessionStatus.ACTIVE

    def test_get_active(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-abc")
        active = chain.get_active("opus", "thread-1")
        assert active is not None
        assert active.session_id == "session-abc"

    def test_seal_session(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-abc")
        chain.seal("opus", "thread-1")
        assert chain.get_active("opus", "thread-1") is None

    def test_create_after_seal(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "session-old")
        chain.seal("opus", "thread-1")
        chain.create("opus", "thread-1", "session-new")
        active = chain.get_active("opus", "thread-1")
        assert active.session_id == "session-new"

    def test_consecutive_failures_triggers_seal(self):
        chain = SessionChain()
        record = chain.create("opus", "thread-1", "session-abc")
        record.consecutive_restore_failures = 3
        assert chain.should_auto_seal("opus", "thread-1") is True

    def test_no_chain_returns_none(self):
        chain = SessionChain()
        assert chain.get_active("opus", "thread-1") is None

    def test_different_threads_independent(self):
        chain = SessionChain()
        chain.create("opus", "thread-1", "s1")
        chain.create("opus", "thread-2", "s2")
        chain.seal("opus", "thread-1")
        assert chain.get_active("opus", "thread-1") is None
        assert chain.get_active("opus", "thread-2") is not None

    def test_no_auto_seal_below_threshold(self):
        chain = SessionChain()
        record = chain.create("opus", "thread-1", "session-abc")
        record.consecutive_restore_failures = 2
        assert chain.should_auto_seal("opus", "thread-1") is False
