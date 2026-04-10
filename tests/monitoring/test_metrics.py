"""Prometheus metrics tests"""
import pytest
import time
from unittest.mock import patch

from prometheus_client import CollectorRegistry

from src.monitoring.metrics import (
    MetricsCollector,
    get_metrics_collector,
    get_metrics_content_type,
    Timer,
    REGISTRY,
)


class TestMetricsCollector:
    def test_creation(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)
        assert collector.registry is registry

    def test_set_app_info(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)
        collector.set_app_info(version="1.0.0", build="abc123")

        metrics = collector.get_metrics().decode()
        assert 'version="1.0.0"' in metrics
        assert 'build="abc123"' in metrics


class TestHTTPMetrics:
    def test_record_http_request(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_http_request("GET", "/api/test", 200, 0.1)
        collector.record_http_request("POST", "/api/test", 201, 0.2)

        metrics = collector.get_metrics().decode()
        assert 'http_requests_total{endpoint="/api/test",method="GET",status="200"} 1.0' in metrics
        assert 'http_requests_total{endpoint="/api/test",method="POST",status="201"} 1.0' in metrics


class TestA2AMetrics:
    def test_record_a2a_message(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_a2a_message("mention", 0.05, success=True)
        collector.record_a2a_message("mention", 0.1, success=False)

        metrics = collector.get_metrics().decode()
        assert 'a2a_messages_total{message_type="mention",status="success"} 1.0' in metrics
        assert 'a2a_messages_total{message_type="mention",status="failure"} 1.0' in metrics

    def test_active_invocations(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.inc_active_invocations()
        collector.inc_active_invocations()
        collector.dec_active_invocations()

        metrics = collector.get_metrics().decode()
        assert "a2a_active_invocations 1.0" in metrics


class TestAgentMetrics:
    def test_record_agent_invocation(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_agent_invocation(
            agent_id="cat-1",
            provider="claude",
            duration=1.5,
            tokens=100,
            model="claude-3-sonnet",
            success=True,
        )

        metrics = collector.get_metrics().decode()
        assert 'agent_invocations_total{agent_id="cat-1",provider="claude",status="success"} 1.0' in metrics
        assert 'agent_tokens_total{agent_id="cat-1",model="claude-3-sonnet"} 100.0' in metrics


class TestThreadMetrics:
    def test_set_active_threads(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.set_active_threads(5)

        metrics = collector.get_metrics().decode()
        assert "threads_active 5.0" in metrics

    def test_record_thread_message(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_thread_message("thread-1")
        collector.record_thread_message("thread-1")

        metrics = collector.get_metrics().decode()
        assert 'thread_messages_total{thread_id="thread-1"} 2.0' in metrics


class TestSkillMetrics:
    def test_record_skill_execution(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_skill_execution("tdd", 0.5, success=True)
        collector.record_skill_execution("debugging", 1.0, success=False)

        metrics = collector.get_metrics().decode()
        assert 'skill_executions_total{skill_name="tdd",status="success"} 1.0' in metrics
        assert 'skill_executions_total{skill_name="debugging",status="failure"} 1.0' in metrics


class TestWorkflowMetrics:
    def test_set_active_workflows(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.set_active_workflows(3)

        metrics = collector.get_metrics().decode()
        assert "workflows_active 3.0" in metrics

    def test_record_workflow_execution(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_workflow_execution("tdd", 10.0, nodes_executed=5, success=True)

        metrics = collector.get_metrics().decode()
        assert 'workflow_executions_total{status="success",template="tdd"} 1.0' in metrics


class TestMemoryMetrics:
    def test_record_memory_operation(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_memory_operation("search", "episodic", 0.05)
        collector.record_memory_operation("store", "semantic", 0.1)

        metrics = collector.get_metrics().decode()
        assert 'memory_operations_total{layer="episodic",operation="search"} 1.0' in metrics
        assert 'memory_operations_total{layer="semantic",operation="store"} 1.0' in metrics

    def test_set_memory_entries(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.set_memory_entries("episodic", 100)
        collector.set_memory_entries("semantic", 50)

        metrics = collector.get_metrics().decode()
        assert 'memory_entries{layer="episodic"} 100.0' in metrics
        assert 'memory_entries{layer="semantic"} 50.0' in metrics


class TestMCPMetrics:
    def test_record_mcp_tool_call(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_mcp_tool_call("read_file", 0.1, success=True)
        collector.record_mcp_tool_call("write_file", 0.2, success=False)

        metrics = collector.get_metrics().decode()
        assert 'mcp_tool_calls_total{status="success",tool_name="read_file"} 1.0' in metrics
        assert 'mcp_tool_calls_total{status="failure",tool_name="write_file"} 1.0' in metrics


class TestAuthMetrics:
    def test_record_auth_attempt(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        collector.record_auth_attempt("login", success=True)
        collector.record_auth_attempt("login", success=False)
        collector.record_auth_attempt("token_refresh", success=True)

        metrics = collector.get_metrics().decode()
        assert 'auth_attempts_total{status="success",type="login"} 1.0' in metrics
        assert 'auth_attempts_total{status="failure",type="login"} 1.0' in metrics


class TestGetMetricsCollector:
    def test_singleton(self):
        # Reset singleton for test
        import src.monitoring.metrics as metrics_module
        original = metrics_module._metrics_collector
        metrics_module._metrics_collector = None

        try:
            collector1 = get_metrics_collector()
            collector2 = get_metrics_collector()
            assert collector1 is collector2
        finally:
            metrics_module._metrics_collector = original


class TestGetMetricsContentType:
    def test_returns_string(self):
        content_type = get_metrics_content_type()
        assert isinstance(content_type, str)
        assert "text/plain" in content_type


class TestTimer:
    def test_timer_records_duration(self):
        registry = CollectorRegistry()
        collector = MetricsCollector(registry=registry)

        with Timer(collector.http_request_duration, "GET", "/test"):
            time.sleep(0.01)

        metrics = collector.get_metrics().decode()
        assert "http_request_duration_seconds" in metrics
