"""Tests for audit API endpoints."""
import pytest
import json
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient

from src.invocation.audit import AuditLog, AuditEntry
from src.web.routes.audit import router, get_audit_log


@pytest.fixture
def temp_audit_dir(tmp_path):
    """Create a temporary audit directory."""
    return str(tmp_path / "audit")


@pytest.fixture
def audit_log(temp_audit_dir):
    """Create an AuditLog instance with temp directory."""
    return AuditLog(log_dir=temp_audit_dir)


class TestAuditLog:
    """Tests for the AuditLog class."""

    def test_append_and_query(self, temp_audit_dir):
        """Test appending entries and querying them."""
        log = AuditLog(log_dir=temp_audit_dir)

        entry = AuditEntry(
            id="test-1",
            timestamp="14:32:10",
            level="info",
            category="file",
            actor="orange",
            action="read_file",
            details="读取了 src/config.ts",
            threadId="thread-1"
        )
        log.append(entry)

        results = log.query(limit=10)
        assert len(results) == 1
        assert results[0]["id"] == "test-1"
        assert results[0]["level"] == "info"
        assert results[0]["category"] == "file"

    def test_query_with_category_filter(self, temp_audit_dir):
        """Test querying with category filter."""
        log = AuditLog(log_dir=temp_audit_dir)

        log.append(AuditEntry(
            id="1", timestamp="14:00", level="info", category="file",
            actor="cat1", action="read", details="details", threadId=""
        ))
        log.append(AuditEntry(
            id="2", timestamp="14:01", level="warning", category="command",
            actor="cat2", action="execute", details="details", threadId=""
        ))

        results = log.query(category="file")
        assert len(results) == 1
        assert results[0]["category"] == "file"

    def test_query_with_level_filter(self, temp_audit_dir):
        """Test querying with level filter."""
        log = AuditLog(log_dir=temp_audit_dir)

        log.append(AuditEntry(
            id="1", timestamp="14:00", level="info", category="file",
            actor="cat1", action="read", details="details", threadId=""
        ))
        log.append(AuditEntry(
            id="2", timestamp="14:01", level="error", category="file",
            actor="cat2", action="read", details="details", threadId=""
        ))

        results = log.query(level="error")
        assert len(results) == 1
        assert results[0]["level"] == "error"

    def test_query_limit(self, temp_audit_dir):
        """Test query limit."""
        log = AuditLog(log_dir=temp_audit_dir)

        for i in range(5):
            log.append(AuditEntry(
                id=str(i), timestamp=f"14:0{i}", level="info", category="file",
                actor="cat", action="read", details="details", threadId=""
            ))

        results = log.query(limit=3)
        assert len(results) == 3


class TestAuditAPI:
    """Tests for the audit API endpoints."""

    def test_list_entries_empty(self, temp_audit_dir):
        """Test listing entries when log is empty."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # Override the audit log to use temp directory
        audit = AuditLog(log_dir=temp_audit_dir)
        from src.web.routes import audit as audit_module
        original_get_audit_log = audit_module.get_audit_log
        audit_module.get_audit_log = lambda: audit

        try:
            response = client.get("/api/audit/entries")
            assert response.status_code == 200
            assert response.json() == []
        finally:
            audit_module.get_audit_log = original_get_audit_log

    def test_list_entries_with_data(self, temp_audit_dir):
        """Test listing entries with data."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        audit = AuditLog(log_dir=temp_audit_dir)
        audit.append(AuditEntry(
            id="test-1", timestamp="14:32:10", level="info", category="file",
            actor="orange", action="read_file", details="读取了文件", threadId="thread-1"
        ))

        from src.web.routes import audit as audit_module
        original_get_audit_log = audit_module.get_audit_log
        audit_module.get_audit_log = lambda: audit

        try:
            response = client.get("/api/audit/entries")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "test-1"
            assert data[0]["actor"] == "orange"
        finally:
            audit_module.get_audit_log = original_get_audit_log

    def test_list_entries_with_category_filter(self, temp_audit_dir):
        """Test listing entries with category filter."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        audit = AuditLog(log_dir=temp_audit_dir)
        audit.append(AuditEntry(
            id="1", timestamp="14:00", level="info", category="file",
            actor="cat1", action="read", details="details", threadId=""
        ))
        audit.append(AuditEntry(
            id="2", timestamp="14:01", level="warning", category="command",
            actor="cat2", action="execute", details="details", threadId=""
        ))

        from src.web.routes import audit as audit_module
        original_get_audit_log = audit_module.get_audit_log
        audit_module.get_audit_log = lambda: audit

        try:
            response = client.get("/api/audit/entries?category=file")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["category"] == "file"
        finally:
            audit_module.get_audit_log = original_get_audit_log

    def test_list_entries_with_level_filter(self, temp_audit_dir):
        """Test listing entries with level filter."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        audit = AuditLog(log_dir=temp_audit_dir)
        audit.append(AuditEntry(
            id="1", timestamp="14:00", level="info", category="file",
            actor="cat1", action="read", details="details", threadId=""
        ))
        audit.append(AuditEntry(
            id="2", timestamp="14:01", level="error", category="file",
            actor="cat2", action="read", details="details", threadId=""
        ))

        from src.web.routes import audit as audit_module
        original_get_audit_log = audit_module.get_audit_log
        audit_module.get_audit_log = lambda: audit

        try:
            response = client.get("/api/audit/entries?level=error")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["level"] == "error"
        finally:
            audit_module.get_audit_log = original_get_audit_log

    def test_list_entries_with_limit(self, temp_audit_dir):
        """Test listing entries with limit."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        audit = AuditLog(log_dir=temp_audit_dir)
        for i in range(5):
            audit.append(AuditEntry(
                id=str(i), timestamp=f"14:0{i}", level="info", category="file",
                actor="cat", action="read", details="details", threadId=""
            ))

        from src.web.routes import audit as audit_module
        original_get_audit_log = audit_module.get_audit_log
        audit_module.get_audit_log = lambda: audit

        try:
            response = client.get("/api/audit/entries?limit=3")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
        finally:
            audit_module.get_audit_log = original_get_audit_log
