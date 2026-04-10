"""Audit logging tests"""
import pytest
import json
import logging
from unittest.mock import patch, MagicMock

from src.monitoring.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    get_audit_logger,
)


class TestAuditEvent:
    def test_event_creation(self):
        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN,
            severity=AuditSeverity.INFO,
            user_id="user123",
            action="login",
            resource_type="auth",
            resource_id="user123",
            timestamp=1234567890.0,
            success=True,
            details={"ip": "127.0.0.1"},
        )
        assert event.event_type == AuditEventType.AUTH_LOGIN
        assert event.user_id == "user123"

    def test_to_dict(self):
        event = AuditEvent(
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.WARNING,
            user_id="user456",
            action="read",
            resource_type="thread",
            resource_id="thread789",
            timestamp=1234567890.0,
            success=True,
            details={"field": "content"},
            ip_address="192.168.1.1",
            session_id="sess_abc",
        )
        data = event.to_dict()
        assert data["audit"] is True
        assert data["event_type"] == "data.access"
        assert data["severity"] == "warning"
        assert data["user_id"] == "user456"
        assert data["ip_address"] == "192.168.1.1"


class TestAuditLoggerAuth:
    @patch("src.monitoring.audit.get_logger")
    def test_auth_login_success(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.auth_login(
            user_id="user123",
            success=True,
            ip_address="127.0.0.1",
            session_id="sess_abc",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "AUDIT"
        assert call_args[1]["event_type"] == "auth.login"
        assert call_args[1]["success"] is True
        assert call_args[1]["ip_address"] == "127.0.0.1"

    @patch("src.monitoring.audit.get_logger")
    def test_auth_login_failure(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.auth_login(
            user_id="user123",
            success=False,
            ip_address="127.0.0.1",
            details={"reason": "invalid_password"},
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["event_type"] == "auth.failed"
        assert call_args[1]["success"] is False
        assert call_args[1]["details"]["reason"] == "invalid_password"

    @patch("src.monitoring.audit.get_logger")
    def test_auth_logout(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.auth_logout(user_id="user123", session_id="sess_abc")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "auth.logout"
        assert call_args[1]["action"] == "logout"


class TestAuditLoggerPermission:
    @patch("src.monitoring.audit.get_logger")
    def test_permission_granted(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.permission_check(
            user_id="user123",
            permission="thread:read",
            resource_type="thread",
            resource_id="thread456",
            granted=True,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "permission.check"
        assert call_args[1]["success"] is True

    @patch("src.monitoring.audit.get_logger")
    def test_permission_denied(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.permission_check(
            user_id="user123",
            permission="admin:write",
            resource_type="config",
            resource_id="system",
            granted=False,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["event_type"] == "permission.denied"
        assert call_args[1]["success"] is False


class TestAuditLoggerData:
    @patch("src.monitoring.audit.get_logger")
    def test_data_access(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.data_access(
            user_id="user123",
            action="read",
            resource_type="memory",
            resource_id="mem_abc",
            details={"query": "test"},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "data.access"
        assert call_args[1]["action"] == "read"

    @patch("src.monitoring.audit.get_logger")
    def test_data_create(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.data_access(
            user_id="user123",
            action="create",
            resource_type="thread",
            resource_id="thread_new",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "data.create"

    @patch("src.monitoring.audit.get_logger")
    def test_data_delete(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.data_access(
            user_id="user123",
            action="delete",
            resource_type="agent",
            resource_id="agent_old",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "data.delete"


class TestAuditLoggerConfig:
    @patch("src.monitoring.audit.get_logger")
    def test_config_change(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.config_change(
            user_id="admin123",
            config_key="max_agents",
            old_value=10,
            new_value=20,
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[1]["event_type"] == "config.change"
        assert call_args[1]["details"]["old_value"] == "10"
        assert call_args[1]["details"]["new_value"] == "20"


class TestAuditLoggerAgent:
    @patch("src.monitoring.audit.get_logger")
    def test_agent_register(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.agent_management(
            user_id="admin123",
            action="register",
            agent_id="agent_new",
            details={"breed": "ragdoll"},
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "agent.register"

    @patch("src.monitoring.audit.get_logger")
    def test_agent_deregister(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.agent_management(
            user_id="admin123",
            action="deregister",
            agent_id="agent_old",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "agent.deregister"


class TestAuditLoggerSkill:
    @patch("src.monitoring.audit.get_logger")
    def test_skill_install(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.skill_management(
            user_id="user123",
            action="install",
            skill_name="tdd",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "skill.install"

    @patch("src.monitoring.audit.get_logger")
    def test_skill_execute(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.skill_management(
            user_id="user123",
            action="execute",
            skill_name="debugging",
            success=True,
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "skill.execute"


class TestAuditLoggerPack:
    @patch("src.monitoring.audit.get_logger")
    def test_pack_activate(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.pack_management(
            user_id="user123",
            action="activate",
            pack_name="tdd-pack",
            thread_id="thread_abc",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "pack.activate"
        assert call_args[1]["details"]["thread_id"] == "thread_abc"


class TestAuditLoggerWorkflow:
    @patch("src.monitoring.audit.get_logger")
    def test_workflow_start(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.workflow_event(
            user_id="user123",
            action="start",
            workflow_id="wf_abc",
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "workflow.start"

    @patch("src.monitoring.audit.get_logger")
    def test_workflow_complete(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.workflow_event(
            user_id="user123",
            action="complete",
            workflow_id="wf_abc",
            details={"nodes_executed": 5},
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "workflow.complete"


class TestAuditLoggerMCP:
    @patch("src.monitoring.audit.get_logger")
    def test_mcp_tool_success(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.mcp_tool_call(
            user_id="user123",
            tool_name="read_file",
            success=True,
            details={"path": "/test.txt"},
        )

        call_args = mock_logger.info.call_args
        assert call_args[1]["event_type"] == "mcp.tool_call"
        assert "error" not in call_args[1]["details"]

    @patch("src.monitoring.audit.get_logger")
    def test_mcp_tool_error(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        audit = AuditLogger()
        audit.mcp_tool_call(
            user_id="user123",
            tool_name="write_file",
            success=False,
            error="Permission denied",
        )

        call_args = mock_logger.warning.call_args
        assert call_args[1]["event_type"] == "mcp.tool_error"
        assert call_args[1]["details"]["error"] == "Permission denied"


class TestGetAuditLogger:
    def test_singleton(self):
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_returns_audit_logger(self):
        logger = get_audit_logger()
        assert isinstance(logger, AuditLogger)
