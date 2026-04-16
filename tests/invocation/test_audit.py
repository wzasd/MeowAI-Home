"""Tests for AuditLog."""
import json
import pytest
from pathlib import Path

from src.invocation.audit import AuditLog, AuditEntry


@pytest.fixture
def audit_dir(tmp_path):
    """Provide a temporary directory for audit logs."""
    return str(tmp_path / "audit")


@pytest.fixture
def audit_log(audit_dir):
    return AuditLog(log_dir=audit_dir)


def make_entry(
    id="e1",
    level="info",
    category="file",
    actor="opus",
    action="read",
    details="detail",
    threadId="t1",
):
    return AuditEntry(
        id=id,
        timestamp="2024-01-01T00:00:00",
        level=level,
        category=category,
        actor=actor,
        action=action,
        details=details,
        threadId=threadId,
    )


class TestAuditEntry:
    def test_fields(self):
        entry = make_entry()
        assert entry.id == "e1"
        assert entry.level == "info"
        assert entry.category == "file"
        assert entry.actor == "opus"


class TestAuditLogAppend:
    def test_append_creates_file(self, audit_log, audit_dir):
        entry = make_entry()
        audit_log.append(entry)
        files = list(Path(audit_dir).glob("*.jsonl"))
        assert len(files) == 1

    def test_append_writes_jsonl_line(self, audit_log, audit_dir):
        entry = make_entry()
        audit_log.append(entry)
        files = list(Path(audit_dir).glob("*.jsonl"))
        data = json.loads(files[0].read_text().strip())
        assert data["id"] == "e1"
        assert data["action"] == "read"

    def test_append_multiple_events(self, audit_log, audit_dir):
        audit_log.append(make_entry(id="e1"))
        audit_log.append(make_entry(id="e2"))
        audit_log.append(make_entry(id="e3"))
        files = list(Path(audit_dir).glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 3


class TestAuditLogQuery:
    def test_query_by_category(self, audit_log):
        audit_log.append(make_entry(category="file"))
        audit_log.append(make_entry(category="command"))
        results = audit_log.query(category="file")
        assert len(results) == 1
        assert results[0]["category"] == "file"

    def test_query_by_level(self, audit_log):
        audit_log.append(make_entry(level="info"))
        audit_log.append(make_entry(level="error"))
        audit_log.append(make_entry(level="info"))
        results = audit_log.query(level="info")
        assert len(results) == 2

    def test_query_combined_filters(self, audit_log):
        audit_log.append(make_entry(category="file", level="info"))
        audit_log.append(make_entry(category="file", level="error"))
        audit_log.append(make_entry(category="command", level="info"))
        results = audit_log.query(category="file", level="info")
        assert len(results) == 1

    def test_query_no_filters_returns_all(self, audit_log):
        audit_log.append(make_entry(id="e1"))
        audit_log.append(make_entry(id="e2"))
        results = audit_log.query()
        assert len(results) == 2

    def test_query_respects_limit(self, audit_log):
        for i in range(5):
            audit_log.append(make_entry(id=f"e{i}"))
        results = audit_log.query(limit=2)
        assert len(results) == 2
