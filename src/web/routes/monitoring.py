"""Monitoring API routes for health checks and metrics"""
from fastapi import APIRouter, Response, Depends
from fastapi.responses import PlainTextResponse

from src.monitoring.health import get_health_checker, HealthStatus
from src.monitoring.metrics import get_metrics_collector, get_metrics_content_type


router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health():
    """Get comprehensive health status."""
    checker = get_health_checker()
    health = await checker.check_all()
    return health.to_dict()


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe endpoint."""
    checker = get_health_checker()
    return checker.get_liveness()


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe endpoint."""
    checker = get_health_checker()
    # Check if critical components are healthy
    health = await checker.check_all()

    if health.status == HealthStatus.UNHEALTHY:
        return Response(
            content='{"ready": false, "reason": "unhealthy"}',
            status_code=503,
            media_type="application/json",
        )

    return checker.get_readiness()


@router.get("/status")
async def get_status():
    """Get detailed system status."""
    from src.monitoring.health import StatusReporter
    checker = get_health_checker()
    reporter = StatusReporter(checker)
    return await reporter.get_status()


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    """Get Prometheus metrics."""
    collector = get_metrics_collector()
    content = collector.get_metrics()
    return Response(
        content=content,
        media_type=get_metrics_content_type(),
    )
