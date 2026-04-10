"""Monitoring package for observability

Provides:
- Structured logging (JSON output)
- Audit logging (security events)
- Prometheus metrics
- Health checks
"""

from src.monitoring.logging import (
    JSONFormatter,
    StructuredLogger,
    get_logger,
    setup_logging,
)

from src.monitoring.audit import (
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    AuditLogger,
    get_audit_logger,
)

from src.monitoring.metrics import (
    MetricsCollector,
    Timer,
    timed,
    get_metrics_collector,
    get_metrics_content_type,
    REGISTRY,
)

from src.monitoring.health import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    StatusReporter,
    get_health_checker,
)

__all__ = [
    # Logging
    "JSONFormatter",
    "StructuredLogger",
    "get_logger",
    "setup_logging",
    # Audit
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "AuditLogger",
    "get_audit_logger",
    # Metrics
    "MetricsCollector",
    "Timer",
    "timed",
    "get_metrics_collector",
    "get_metrics_content_type",
    "REGISTRY",
    # Health
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "StatusReporter",
    "get_health_checker",
]
