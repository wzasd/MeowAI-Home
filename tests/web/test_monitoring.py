"""Monitoring API tests"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.routes.monitoring import router as monitoring_router
from src.monitoring.health import get_health_checker, HealthStatus
from src.monitoring.metrics import get_metrics_collector


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(monitoring_router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestHealthEndpoint:
    def test_get_health(self, client):
        response = client.get("/api/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "components" in data


class TestLivenessEndpoint:
    def test_liveness_probe(self, client):
        response = client.get("/api/monitoring/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True


class TestReadinessEndpoint:
    def test_readiness_probe_healthy(self, client):
        # Mock health check to return healthy
        checker = get_health_checker()
        original_check_all = checker.check_all

        async def mock_check_all():
            from src.monitoring.health import SystemHealth, ComponentHealth
            return SystemHealth(
                status=HealthStatus.HEALTHY,
                version="1.0.0",
                uptime_seconds=100,
                components=[ComponentHealth("test", HealthStatus.HEALTHY, 1.0)],
            )

        checker.check_all = mock_check_all
        try:
            response = client.get("/api/monitoring/health/ready")
            assert response.status_code == 200
            data = response.json()
            assert data["ready"] is True
        finally:
            checker.check_all = original_check_all


class TestStatusEndpoint:
    def test_get_status(self, client):
        response = client.get("/api/monitoring/status")
        assert response.status_code == 200
        data = response.json()
        assert "health" in data
        assert "version" in data
        assert "uptime" in data


class TestMetricsEndpoint:
    def test_get_metrics(self, client):
        # Initialize metrics
        collector = get_metrics_collector()
        collector.record_http_request("GET", "/test", 200, 0.1)

        response = client.get("/api/monitoring/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "http_requests_total" in response.text
