"""Tests for EventAuditLog (A4)."""
import json
import os
import time
import pytest
from pathlib import Path

from src.invocation.audit import EventAuditLog, AuditEvent, AuditEventType


@pytest.fixture
def audit_dir(tmp_path):
    """Provide a temporary directory for audit logs."""
    return str(tmp_path / "audit")


@pytest.fixture
def audit_log(audit_dir):
    return EventAuditLog(log_dir=audit_dir)


def make_event(
    event_type=AuditEventType.CAT_INVOKED,
    thread_id="t1",
    cat_id="opus",
    timestamp=None,
    metadata=None,
):
    return AuditEvent(
        event_type=event_type,
        thread_id=thread_id,
        cat_id=cat_id,
        timestamp=timestamp or time.time(),
        metadata=metadata,
    )


class TestAuditEvent:
    def test_to_dict_basic(self):
        event = make_event()
        d = event.to_dict()
        assert d["event_type"] == "cat_invoked"
        assert d["thread_id"] == "t1"
        assert d["cat_id"] == "opus"
        assert "timestamp" in d
        assert d["metadata"] == {}

    def test_to_dict_with_metadata(self):
        event = make_event(metadata={"duration_ms": 500})
        d = event.to_dict()
        assert d["metadata"]["duration_ms"] == 500

    def test_to_dict_preserves_unicode(self):
        event = make_event(metadata={"msg": "猫咪"})
        d = event.to_dict()
        assert d["metadata"]["msg"] == "猫咪"


class TestEventAuditLogAppend:
    def test_append_creates_file(self, audit_log, audit_dir):
        event = make_event()
        audit_log.append(event)
        files = list(Path(audit_dir).glob("audit-*.ndjson"))
        assert len(files) == 1

    def test_append_writes_ndjson_line(self, audit_log, audit_dir):
        ts = time.time()
        event = make_event(timestamp=ts)
        audit_log.append(event)
        from datetime import datetime
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        path = Path(audit_dir) / f"audit-{date_str}.ndjson"
        data = json.loads(path.read_text().strip())
        assert data["event_type"] == "cat_invoked"

    def test_append_multiple_events(self, audit_log, audit_dir):
        audit_log.append(make_event(thread_id="t1"))
        audit_log.append(make_event(thread_id="t2"))
        audit_log.append(make_event(thread_id="t3"))
        # Same date file should have 3 lines
        files = list(Path(audit_dir).glob("audit-*.ndjson"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 3

    def test_append_different_dates_shards_files(self, audit_log, audit_dir):
        # Two events on different dates
        now = time.time()
        yesterday = now - 86400
        audit_log.append(make_event(timestamp=now))
        audit_log.append(make_event(timestamp=yesterday))
        files = list(Path(audit_dir).glob("audit-*.ndjson"))
        assert len(files) == 2


class TestEventAuditLogQuery:
    def test_query_by_thread_id(self, audit_log):
        audit_log.append(make_event(thread_id="t1", cat_id="opus"))
        audit_log.append(make_event(thread_id="t2", cat_id="sonnet"))
        results = audit_log.query(thread_id="t1")
        assert len(results) == 1
        assert results[0]["thread_id"] == "t1"

    def test_query_by_cat_id(self, audit_log):
        audit_log.append(make_event(cat_id="opus"))
        audit_log.append(make_event(cat_id="sonnet"))
        audit_log.append(make_event(cat_id="opus"))
        results = audit_log.query(cat_id="opus")
        assert len(results) == 2

    def test_query_by_event_type(self, audit_log):
        audit_log.append(make_event(event_type=AuditEventType.CAT_INVOKED))
        audit_log.append(make_event(event_type=AuditEventType.CAT_RESPONDED))
        audit_log.append(make_event(event_type=AuditEventType.CAT_INVOKED))
        results = audit_log.query(event_type=AuditEventType.CAT_INVOKED)
        assert len(results) == 2

    def test_query_by_date(self, audit_log):
        now = time.time()
        audit_log.append(make_event(timestamp=now))
        from datetime import datetime
        date_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        results = audit_log.query(date=date_str)
        assert len(results) == 1

    def test_query_by_date_no_match(self, audit_log):
        audit_log.append(make_event())
        results = audit_log.query(date="2020-01-01")
        assert len(results) == 0

    def test_query_combined_filters(self, audit_log):
        audit_log.append(make_event(
            thread_id="t1", cat_id="opus",
            event_type=AuditEventType.CAT_INVOKED,
        ))
        audit_log.append(make_event(
            thread_id="t1", cat_id="sonnet",
            event_type=AuditEventType.CAT_INVOKED,
        ))
        audit_log.append(make_event(
            thread_id="t2", cat_id="opus",
            event_type=AuditEventType.CAT_INVOKED,
        ))
        results = audit_log.query(thread_id="t1", cat_id="opus")
        assert len(results) == 1

    def test_query_no_filters_returns_all(self, audit_log):
        audit_log.append(make_event(thread_id="t1"))
        audit_log.append(make_event(thread_id="t2"))
        results = audit_log.query()
        assert len(results) == 2

    def test_query_all_event_types(self, audit_log):
        """Verify all AuditEventType values work."""
        for et in AuditEventType:
            audit_log.append(make_event(event_type=et, thread_id=f"t-{et.value}"))
        results = audit_log.query(event_type=AuditEventType.A2A_HANDOFF)
        assert len(results) == 1
        assert results[0]["event_type"] == "a2a_handoff"

    def test_query_nonexistent_date_file(self, audit_log):
        results = audit_log.query(date="2099-12-31")
        assert results == []
