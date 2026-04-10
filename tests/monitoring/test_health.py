"""Health check tests"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.monitoring.health import (
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    StatusReporter,
    get_health_checker,
)


class TestComponentHealth:
    def test_creation(self):
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            latency_ms=10.5,
            message="OK",
        )
        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 10.5

    def test_to_dict(self):
        health = ComponentHealth(
            name="test",
            status=HealthStatus.DEGRADED,
            latency_ms=10.5,
            message="Slow",
            details={"cpu": 90},
        )
        data = health.to_dict()
        assert data["name"] == "test"
        assert data["status"] == "degraded"
        assert data["latency_ms"] == 10.5
        assert data["details"]["cpu"] == 90


class TestSystemHealth:
    def test_creation(self):
        components = [
            ComponentHealth("db", HealthStatus.HEALTHY, 5.0),
            ComponentHealth("cache", HealthStatus.HEALTHY, 2.0),
        ]
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            uptime_seconds=3600,
            components=components,
        )
        assert health.status == HealthStatus.HEALTHY
        assert health.version == "1.0.0"
        assert len(health.components) == 2

    def test_to_dict(self):
        components = [ComponentHealth("db", HealthStatus.HEALTHY, 5.0)]
        health = SystemHealth(
            status=HealthStatus.HEALTHY,
            version="1.0.0",
            uptime_seconds=3600,
            components=components,
        )
        data = health.to_dict()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert len(data["components"]) == 1


class TestHealthChecker:
    @pytest.fixture
    def checker(self):
        return HealthChecker(version="0.2.0")

    @pytest.mark.asyncio
    async def test_check_database_not_configured(self, checker):
        result = await checker.check_database()
        assert result.status == HealthStatus.UNHEALTHY
        assert "not configured" in result.message

    @pytest.mark.asyncio
    async def test_check_database_success(self, checker):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            checker.register_database(db_path)
            result = await checker.check_database()
            assert result.status == HealthStatus.HEALTHY
            assert "OK" in result.message
            assert result.latency_ms > 0
        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_check_database_failure(self, checker):
        checker.register_database("/nonexistent/path/db.sqlite")
        result = await checker.check_database()
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_check_memory_no_psutil(self, checker):
        with patch.dict("sys.modules", {"psutil": None}):
            result = await checker.check_memory()
            assert result.status == HealthStatus.HEALTHY
            assert "skipped" in result.message

    @pytest.mark.asyncio
    async def test_check_disk_no_psutil(self, checker):
        with patch.dict("sys.modules", {"psutil": None}):
            result = await checker.check_disk()
            assert result.status == HealthStatus.HEALTHY
            assert "skipped" in result.message

    @pytest.mark.asyncio
    async def test_check_custom_success(self, checker):
        def check():
            return True

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.HEALTHY
        assert result.name == "custom"

    @pytest.mark.asyncio
    async def test_check_custom_failure(self, checker):
        def check():
            return False

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_custom_exception(self, checker):
        def check():
            raise ValueError("test error")

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.UNHEALTHY
        assert "test error" in result.message

    @pytest.mark.asyncio
    async def test_check_custom_async(self, checker):
        async def check():
            return True

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_custom_component_health(self, checker):
        def check():
            return ComponentHealth(
                name="custom",
                status=HealthStatus.DEGRADED,
                latency_ms=100,
                message="Slow",
            )

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.DEGRADED
        assert result.message == "Slow"

    @pytest.mark.asyncio
    async def test_check_custom_tuple_result(self, checker):
        def check():
            return (HealthStatus.DEGRADED, "Something wrong")

        result = await checker.check_custom("custom", check)
        assert result.status == HealthStatus.DEGRADED
        assert result.message == "Something wrong"

    @pytest.mark.asyncio
    async def test_check_all_healthy(self, checker):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            checker.register_database(db_path)
            result = await checker.check_all()
            assert result.status == HealthStatus.HEALTHY
            assert result.version == "0.2.0"
            assert len(result.components) >= 3  # db, memory, disk
        finally:
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_check_all_unhealthy(self, checker):
        checker.register_database("/nonexistent/path")

        def bad_check():
            return False

        checker.register_check("bad", bad_check)
        result = await checker.check_all()
        assert result.status == HealthStatus.UNHEALTHY

    def test_get_readiness(self, checker):
        result = checker.get_readiness()
        assert result["ready"] is True
        assert "timestamp" in result

    def test_get_liveness(self, checker):
        result = checker.get_liveness()
        assert result["alive"] is True
        assert "timestamp" in result


class TestStatusReporter:
    @pytest.mark.asyncio
    async def test_get_status(self):
        checker = HealthChecker(version="1.0.0")
        reporter = StatusReporter(checker)

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            checker.register_database(db_path)
            status = await reporter.get_status()
            assert "health" in status
            assert status["version"] == "1.0.0"
            assert "uptime" in status
        finally:
            os.unlink(db_path)

    def test_format_duration(self):
        checker = HealthChecker()
        reporter = StatusReporter(checker)

        assert reporter._format_duration(30) == "30s"
        assert reporter._format_duration(90) == "1m 30s"
        assert reporter._format_duration(3661) == "1h 1m"
        assert reporter._format_duration(90061) == "1d 1h"


class TestGetHealthChecker:
    def test_singleton(self):
        # Reset singleton for test
        import src.monitoring.health as health_module
        original = health_module._health_checker
        health_module._health_checker = None

        try:
            checker1 = get_health_checker()
            checker2 = get_health_checker()
            assert checker1 is checker2
        finally:
            health_module._health_checker = original

    def test_version_passed(self):
        import src.monitoring.health as health_module
        original = health_module._health_checker
        health_module._health_checker = None

        try:
            checker = get_health_checker(version="2.0.0")
            assert checker.version == "2.0.0"
        finally:
            health_module._health_checker = original
