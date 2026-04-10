"""Health check and status API for monitoring"""
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import time
import asyncio
import sqlite3


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus
    version: str
    uptime_seconds: float
    components: List[ComponentHealth]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "components": [c.to_dict() for c in self.components],
            "timestamp": self.timestamp,
        }


class HealthChecker:
    """Performs health checks on system components."""

    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self.start_time = time.time()
        self._checks: Dict[str, callable] = {}
        self._db_path: Optional[str] = None

    def register_database(self, db_path: str):
        """Register database for health checking."""
        self._db_path = db_path

    def register_check(self, name: str, check_func: callable):
        """Register a custom health check function."""
        self._checks[name] = check_func

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity."""
        if not self._db_path:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message="Database not configured",
            )

        start = time.time()
        try:
            conn = sqlite3.connect(self._db_path, timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            latency = (time.time() - start) * 1000

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Database connection OK",
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Database check failed: {str(e)}",
            )

    async def check_memory(self) -> ComponentHealth:
        """Check memory usage."""
        start = time.time()
        try:
            import psutil
            memory = psutil.virtual_memory()
            latency = (time.time() - start) * 1000

            # Consider degraded if > 90% memory usage
            if memory.percent > 90:
                status = HealthStatus.DEGRADED
                message = f"High memory usage: {memory.percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage: {memory.percent}%"

            return ComponentHealth(
                name="memory",
                status=status,
                latency_ms=latency,
                message=message,
                details={
                    "percent": memory.percent,
                    "used_mb": memory.used // (1024 * 1024),
                    "available_mb": memory.available // (1024 * 1024),
                },
            )
        except ImportError:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="memory",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Memory check skipped (psutil not installed)",
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Memory check failed: {str(e)}",
            )

    async def check_disk(self) -> ComponentHealth:
        """Check disk space."""
        start = time.time()
        try:
            import psutil
            disk = psutil.disk_usage("/")
            latency = (time.time() - start) * 1000

            percent_used = (disk.used / disk.total) * 100

            # Consider degraded if > 90% disk usage
            if percent_used > 90:
                status = HealthStatus.DEGRADED
                message = f"High disk usage: {percent_used:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage: {percent_used:.1f}%"

            return ComponentHealth(
                name="disk",
                status=status,
                latency_ms=latency,
                message=message,
                details={
                    "percent": round(percent_used, 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                },
            )
        except ImportError:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="disk",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Disk check skipped (psutil not installed)",
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Disk check failed: {str(e)}",
            )

    async def check_custom(self, name: str, check_func: callable) -> ComponentHealth:
        """Run a custom health check."""
        start = time.time()
        try:
            result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            latency = (time.time() - start) * 1000

            if isinstance(result, ComponentHealth):
                result.latency_ms = latency
                return result
            elif isinstance(result, tuple):
                status, message = result
                return ComponentHealth(
                    name=name,
                    status=status,
                    latency_ms=latency,
                    message=message,
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    latency_ms=latency,
                    message="OK" if result else "Check failed",
                )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Check failed: {str(e)}",
            )

    async def check_all(self) -> SystemHealth:
        """Run all health checks."""
        components = []

        # Run built-in checks
        components.append(await self.check_database())
        components.append(await self.check_memory())
        components.append(await self.check_disk())

        # Run custom checks
        for name, check_func in self._checks.items():
            components.append(await self.check_custom(name, check_func))

        # Determine overall status
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            overall_status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        uptime = time.time() - self.start_time

        return SystemHealth(
            status=overall_status,
            version=self.version,
            uptime_seconds=uptime,
            components=components,
        )

    def get_readiness(self) -> Dict[str, Any]:
        """Get readiness probe status."""
        return {
            "ready": True,
            "timestamp": time.time(),
        }

    def get_liveness(self) -> Dict[str, Any]:
        """Get liveness probe status."""
        return {
            "alive": True,
            "timestamp": time.time(),
        }


class StatusReporter:
    """Reports detailed system status information."""

    def __init__(self, health_checker: HealthChecker):
        self.health = health_checker

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        health = await self.health.check_all()

        return {
            "health": health.to_dict(),
            "version": self.health.version,
            "uptime": {
                "seconds": round(health.uptime_seconds, 2),
                "formatted": self._format_duration(health.uptime_seconds),
            },
        }

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of key metrics."""
        # This would integrate with the metrics collector
        return {
            "timestamp": time.time(),
            "note": "Use /metrics for full Prometheus metrics",
        }

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m"
        else:
            return f"{int(seconds // 86400)}d {int((seconds % 86400) // 3600)}h"


# Singleton instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker(version: str = "0.1.0") -> HealthChecker:
    """Get the singleton health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker(version=version)
    return _health_checker
