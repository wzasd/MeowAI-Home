"""Prometheus metrics for observability"""
from typing import Optional, Dict, Any
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)


# Default registry
REGISTRY = CollectorRegistry()


class MetricsCollector:
    """Collects and exposes Prometheus metrics for the application."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or REGISTRY

        # Request metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )
        self.http_request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # A2A messaging metrics
        self.a2a_messages_total = Counter(
            "a2a_messages_total",
            "Total A2A messages processed",
            ["message_type", "status"],
            registry=self.registry,
        )
        self.a2a_message_duration = Histogram(
            "a2a_message_duration_seconds",
            "A2A message processing duration",
            ["message_type"],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )
        self.a2a_active_invocations = Gauge(
            "a2a_active_invocations",
            "Number of active A2A invocations",
            registry=self.registry,
        )

        # Agent metrics
        self.agent_invocations_total = Counter(
            "agent_invocations_total",
            "Total agent invocations",
            ["agent_id", "provider", "status"],
            registry=self.registry,
        )
        self.agent_invocation_duration = Histogram(
            "agent_invocation_duration_seconds",
            "Agent invocation duration",
            ["agent_id", "provider"],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )
        self.agent_tokens_total = Counter(
            "agent_tokens_total",
            "Total tokens consumed by agents",
            ["agent_id", "model"],
            registry=self.registry,
        )

        # Thread metrics
        self.threads_active = Gauge(
            "threads_active",
            "Number of active threads",
            registry=self.registry,
        )
        self.thread_messages_total = Counter(
            "thread_messages_total",
            "Total messages in threads",
            ["thread_id"],
            registry=self.registry,
        )

        # Skill metrics
        self.skill_executions_total = Counter(
            "skill_executions_total",
            "Total skill executions",
            ["skill_name", "status"],
            registry=self.registry,
        )
        self.skill_execution_duration = Histogram(
            "skill_execution_duration_seconds",
            "Skill execution duration",
            ["skill_name"],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
        )

        # Workflow metrics
        self.workflows_active = Gauge(
            "workflows_active",
            "Number of active workflows",
            registry=self.registry,
        )
        self.workflow_executions_total = Counter(
            "workflow_executions_total",
            "Total workflow executions",
            ["template", "status"],
            registry=self.registry,
        )
        self.workflow_execution_duration = Histogram(
            "workflow_execution_duration_seconds",
            "Workflow execution duration",
            ["template"],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
        )
        self.workflow_nodes_executed = Histogram(
            "workflow_nodes_executed",
            "Number of nodes executed per workflow",
            ["template"],
            registry=self.registry,
            buckets=[1, 2, 3, 5, 10, 20, 50],
        )

        # Memory metrics
        self.memory_operations_total = Counter(
            "memory_operations_total",
            "Total memory operations",
            ["operation", "layer"],
            registry=self.registry,
        )
        self.memory_operation_duration = Histogram(
            "memory_operation_duration_seconds",
            "Memory operation duration",
            ["operation", "layer"],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
        )
        self.memory_entries = Gauge(
            "memory_entries",
            "Number of entries in memory layers",
            ["layer"],
            registry=self.registry,
        )

        # MCP tool metrics
        self.mcp_tool_calls_total = Counter(
            "mcp_tool_calls_total",
            "Total MCP tool calls",
            ["tool_name", "status"],
            registry=self.registry,
        )
        self.mcp_tool_duration = Histogram(
            "mcp_tool_duration_seconds",
            "MCP tool execution duration",
            ["tool_name"],
            registry=self.registry,
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # Auth metrics
        self.auth_attempts_total = Counter(
            "auth_attempts_total",
            "Total authentication attempts",
            ["type", "status"],
            registry=self.registry,
        )

        # Application info
        self.app_info = Info(
            "app",
            "Application information",
            registry=self.registry,
        )

    def set_app_info(self, version: str, build: str = ""):
        """Set application info metrics."""
        self.app_info.info({"version": version, "build": build})

    # HTTP metrics
    def record_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record an HTTP request."""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        self.http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)

    # A2A metrics
    def record_a2a_message(self, message_type: str, duration: float, success: bool = True):
        """Record an A2A message processing."""
        status = "success" if success else "failure"
        self.a2a_messages_total.labels(message_type=message_type, status=status).inc()
        self.a2a_message_duration.labels(message_type=message_type).observe(duration)

    def inc_active_invocations(self):
        """Increment active invocations counter."""
        self.a2a_active_invocations.inc()

    def dec_active_invocations(self):
        """Decrement active invocations counter."""
        self.a2a_active_invocations.dec()

    # Agent metrics
    def record_agent_invocation(
        self,
        agent_id: str,
        provider: str,
        duration: float,
        tokens: int = 0,
        model: str = "unknown",
        success: bool = True,
    ):
        """Record an agent invocation."""
        status = "success" if success else "failure"
        self.agent_invocations_total.labels(agent_id=agent_id, provider=provider, status=status).inc()
        self.agent_invocation_duration.labels(agent_id=agent_id, provider=provider).observe(duration)
        if tokens > 0:
            self.agent_tokens_total.labels(agent_id=agent_id, model=model).inc(tokens)

    # Thread metrics
    def set_active_threads(self, count: int):
        """Set the number of active threads."""
        self.threads_active.set(count)

    def record_thread_message(self, thread_id: str):
        """Record a message in a thread."""
        self.thread_messages_total.labels(thread_id=thread_id).inc()

    # Skill metrics
    def record_skill_execution(self, skill_name: str, duration: float, success: bool = True):
        """Record a skill execution."""
        status = "success" if success else "failure"
        self.skill_executions_total.labels(skill_name=skill_name, status=status).inc()
        self.skill_execution_duration.labels(skill_name=skill_name).observe(duration)

    # Workflow metrics
    def set_active_workflows(self, count: int):
        """Set the number of active workflows."""
        self.workflows_active.set(count)

    def record_workflow_execution(
        self,
        template: str,
        duration: float,
        nodes_executed: int,
        success: bool = True,
    ):
        """Record a workflow execution."""
        status = "success" if success else "failure"
        self.workflow_executions_total.labels(template=template, status=status).inc()
        self.workflow_execution_duration.labels(template=template).observe(duration)
        self.workflow_nodes_executed.labels(template=template).observe(nodes_executed)

    # Memory metrics
    def record_memory_operation(self, operation: str, layer: str, duration: float):
        """Record a memory operation."""
        self.memory_operations_total.labels(operation=operation, layer=layer).inc()
        self.memory_operation_duration.labels(operation=operation, layer=layer).observe(duration)

    def set_memory_entries(self, layer: str, count: int):
        """Set the number of entries in a memory layer."""
        self.memory_entries.labels(layer=layer).set(count)

    # MCP metrics
    def record_mcp_tool_call(self, tool_name: str, duration: float, success: bool = True):
        """Record an MCP tool call."""
        status = "success" if success else "failure"
        self.mcp_tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        self.mcp_tool_duration.labels(tool_name=tool_name).observe(duration)

    # Auth metrics
    def record_auth_attempt(self, auth_type: str, success: bool = True):
        """Record an authentication attempt."""
        status = "success" if success else "failure"
        self.auth_attempts_total.labels(type=auth_type, status=status).inc()

    def get_metrics(self) -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest(self.registry)


# Singleton instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the singleton metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_metrics_content_type() -> str:
    """Get the content type for Prometheus metrics."""
    return CONTENT_TYPE_LATEST


class Timer:
    """Context manager for timing operations."""

    def __init__(self, metric, *labels):
        self.metric = metric
        self.labels = labels
        self.start_time: Optional[float] = None
        self.duration: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        self.metric.labels(*self.labels).observe(self.duration)


def timed(metric_name: str, **label_kwargs):
    """Decorator for timing function execution.

    Usage:
        @timed("my_metric", endpoint="/api/test")
        async def my_function():
            pass
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            metric = getattr(collector, metric_name, None)
            if metric is None:
                return await func(*args, **kwargs)

            labels = [label_kwargs.get(k, "") for k in metric._labelnames]
            with Timer(metric, *labels):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            collector = get_metrics_collector()
            metric = getattr(collector, metric_name, None)
            if metric is None:
                return func(*args, **kwargs)

            labels = [label_kwargs.get(k, "") for k in metric._labelnames]
            with Timer(metric, *labels):
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
