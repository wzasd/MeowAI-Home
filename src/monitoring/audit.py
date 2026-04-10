"""Audit logging for security-relevant events"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import time

from src.monitoring.logging import get_logger


class AuditEventType(Enum):
    """Types of audit events."""
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_REFRESH = "auth.refresh"

    PERMISSION_CHECK = "permission.check"
    PERMISSION_DENIED = "permission.denied"

    DATA_ACCESS = "data.access"
    DATA_CREATE = "data.create"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"

    CONFIG_CHANGE = "config.change"

    AGENT_REGISTER = "agent.register"
    AGENT_DEREGISTER = "agent.deregister"
    AGENT_UPDATE = "agent.update"

    SKILL_INSTALL = "skill.install"
    SKILL_UNINSTALL = "skill.uninstall"
    SKILL_EXECUTE = "skill.execute"

    PACK_ACTIVATE = "pack.activate"
    PACK_DEACTIVATE = "pack.deactivate"

    WORKFLOW_START = "workflow.start"
    WORKFLOW_COMPLETE = "workflow.complete"
    WORKFLOW_CANCEL = "workflow.cancel"

    MCP_TOOL_CALL = "mcp.tool_call"
    MCP_TOOL_ERROR = "mcp.tool_error"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents an audit event."""
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    timestamp: float
    success: bool
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "audit": True,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "timestamp": self.timestamp,
            "success": self.success,
            "details": self.details,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
            "request_id": self.request_id,
        }


class AuditLogger:
    """Audit logger for security-relevant events."""

    def __init__(self):
        self._logger = get_logger("audit")

    def _log(self, event: AuditEvent):
        """Log an audit event."""
        data = event.to_dict()
        severity = event.severity

        if severity == AuditSeverity.CRITICAL:
            self._logger.critical("AUDIT", **data)
        elif severity == AuditSeverity.ERROR:
            self._logger.error("AUDIT", **data)
        elif severity == AuditSeverity.WARNING:
            self._logger.warning("AUDIT", **data)
        else:
            self._logger.info("AUDIT", **data)

    def auth_login(
        self,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log authentication attempt."""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGIN if success else AuditEventType.AUTH_FAILED,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            action="login",
            resource_type="auth",
            resource_id=user_id,
            timestamp=time.time(),
            success=success,
            details=details or {},
            ip_address=ip_address,
            session_id=session_id,
        )
        self._log(event)

    def auth_logout(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log user logout."""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_LOGOUT,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action="logout",
            resource_type="auth",
            resource_id=user_id,
            timestamp=time.time(),
            success=True,
            details=details or {},
            session_id=session_id,
        )
        self._log(event)

    def permission_check(
        self,
        user_id: str,
        permission: str,
        resource_type: str,
        resource_id: str,
        granted: bool,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log permission check."""
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_CHECK if granted else AuditEventType.PERMISSION_DENIED,
            severity=AuditSeverity.INFO if granted else AuditSeverity.WARNING,
            user_id=user_id,
            action="check_permission",
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=time.time(),
            success=granted,
            details={"permission": permission, **(details or {})},
        )
        self._log(event)

    def data_access(
        self,
        user_id: Optional[str],
        action: str,
        resource_type: str,
        resource_id: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log data access event."""
        event_type_map = {
            "create": AuditEventType.DATA_CREATE,
            "read": AuditEventType.DATA_ACCESS,
            "update": AuditEventType.DATA_UPDATE,
            "delete": AuditEventType.DATA_DELETE,
        }

        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.DATA_ACCESS),
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=time.time(),
            success=success,
            details=details or {},
        )
        self._log(event)

    def config_change(
        self,
        user_id: str,
        config_key: str,
        old_value: Any,
        new_value: Any,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log configuration change."""
        event = AuditEvent(
            event_type=AuditEventType.CONFIG_CHANGE,
            severity=AuditSeverity.WARNING,
            user_id=user_id,
            action="change_config",
            resource_type="config",
            resource_id=config_key,
            timestamp=time.time(),
            success=True,
            details={
                "old_value": str(old_value) if old_value is not None else None,
                "new_value": str(new_value) if new_value is not None else None,
                **(details or {}),
            },
        )
        self._log(event)

    def agent_management(
        self,
        user_id: str,
        action: str,  # register, deregister, update
        agent_id: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log agent management event."""
        action_map = {
            "register": AuditEventType.AGENT_REGISTER,
            "deregister": AuditEventType.AGENT_DEREGISTER,
            "update": AuditEventType.AGENT_UPDATE,
        }

        event = AuditEvent(
            event_type=action_map.get(action, AuditEventType.AGENT_UPDATE),
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type="agent",
            resource_id=agent_id,
            timestamp=time.time(),
            success=success,
            details=details or {},
        )
        self._log(event)

    def skill_management(
        self,
        user_id: str,
        action: str,  # install, uninstall, execute
        skill_name: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log skill management event."""
        action_map = {
            "install": AuditEventType.SKILL_INSTALL,
            "uninstall": AuditEventType.SKILL_UNINSTALL,
            "execute": AuditEventType.SKILL_EXECUTE,
        }

        event = AuditEvent(
            event_type=action_map.get(action, AuditEventType.SKILL_EXECUTE),
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type="skill",
            resource_id=skill_name,
            timestamp=time.time(),
            success=success,
            details=details or {},
        )
        self._log(event)

    def pack_management(
        self,
        user_id: str,
        action: str,  # activate, deactivate
        pack_name: str,
        thread_id: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log pack management event."""
        event = AuditEvent(
            event_type=AuditEventType.PACK_ACTIVATE if action == "activate" else AuditEventType.PACK_DEACTIVATE,
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type="pack",
            resource_id=pack_name,
            timestamp=time.time(),
            success=success,
            details={"thread_id": thread_id, **(details or {})},
        )
        self._log(event)

    def workflow_event(
        self,
        user_id: Optional[str],
        action: str,  # start, complete, cancel
        workflow_id: str,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log workflow lifecycle event."""
        action_map = {
            "start": AuditEventType.WORKFLOW_START,
            "complete": AuditEventType.WORKFLOW_COMPLETE,
            "cancel": AuditEventType.WORKFLOW_CANCEL,
        }

        event = AuditEvent(
            event_type=action_map.get(action, AuditEventType.WORKFLOW_START),
            severity=AuditSeverity.INFO,
            user_id=user_id,
            action=action,
            resource_type="workflow",
            resource_id=workflow_id,
            timestamp=time.time(),
            success=success,
            details=details or {},
        )
        self._log(event)

    def mcp_tool_call(
        self,
        user_id: Optional[str],
        tool_name: str,
        success: bool,
        error: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log MCP tool invocation."""
        event = AuditEvent(
            event_type=AuditEventType.MCP_TOOL_CALL if success else AuditEventType.MCP_TOOL_ERROR,
            severity=AuditSeverity.INFO if success else AuditSeverity.WARNING,
            user_id=user_id,
            action="invoke",
            resource_type="mcp_tool",
            resource_id=tool_name,
            timestamp=time.time(),
            success=success,
            details={"error": error, **(details or {})} if error else (details or {}),
        )
        self._log(event)


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
