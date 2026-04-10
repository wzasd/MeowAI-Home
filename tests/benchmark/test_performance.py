"""Performance benchmark tests"""
import pytest
import time
import asyncio
import statistics
from typing import List, Callable
from concurrent.futures import ThreadPoolExecutor

from src.monitoring.metrics import get_metrics_collector


class BenchmarkResult:
    """Benchmark result container."""

    def __init__(self, name: str, latencies: List[float]):
        self.name = name
        self.latencies = latencies
        self.count = len(latencies)
        self.min = min(latencies)
        self.max = max(latencies)
        self.mean = statistics.mean(latencies)
        self.p50 = statistics.median(latencies)
        self.p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        self.p99 = sorted(latencies)[int(len(latencies) * 0.99)]

    def to_dict(self):
        return {
            "name": self.name,
            "count": self.count,
            "min_ms": round(self.min * 1000, 2),
            "max_ms": round(self.max * 1000, 2),
            "mean_ms": round(self.mean * 1000, 2),
            "p50_ms": round(self.p50 * 1000, 2),
            "p95_ms": round(self.p95 * 1000, 2),
            "p99_ms": round(self.p99 * 1000, 2),
        }


def benchmark(func: Callable, iterations: int = 100) -> BenchmarkResult:
    """Run benchmark on a function."""
    latencies = []

    for _ in range(iterations):
        start = time.time()
        func()
        latencies.append(time.time() - start)

    return BenchmarkResult(func.__name__, latencies)


@pytest.mark.benchmark
class TestHealthCheckPerformance:
    """Benchmark health check endpoints."""

    def test_liveness_latency(self, client):
        """Liveness probe should respond in < 10ms."""
        latencies = []

        for _ in range(100):
            start = time.time()
            response = client.get("/api/monitoring/health/live")
            latencies.append(time.time() - start)
            assert response.status_code == 200

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 0.01, f"P95 latency {p95*1000:.2f}ms exceeds 10ms"

    def test_readiness_latency(self, client):
        """Readiness probe should respond in < 50ms."""
        latencies = []

        for _ in range(100):
            start = time.time()
            response = client.get("/api/monitoring/health/ready")
            latencies.append(time.time() - start)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 0.05, f"P95 latency {p95*1000:.2f}ms exceeds 50ms"


@pytest.mark.benchmark
class TestThreadAPIPerformance:
    """Benchmark Thread API endpoints."""

    def test_list_threads_latency(self, client):
        """List threads should respond in < 100ms."""
        latencies = []

        for _ in range(100):
            start = time.time()
            response = client.get("/api/threads")
            latencies.append(time.time() - start)
            assert response.status_code == 200

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 0.1, f"P95 latency {p95*1000:.2f}ms exceeds 100ms"

    def test_create_thread_latency(self, client):
        """Create thread should respond in < 200ms."""
        latencies = []

        for i in range(50):
            start = time.time()
            response = client.post("/api/threads", json={"name": f"Bench {i}"})
            latencies.append(time.time() - start)
            assert response.status_code == 200

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 0.2, f"P95 latency {p95*1000:.2f}ms exceeds 200ms"


@pytest.mark.benchmark
class TestMemoryPerformance:
    """Benchmark memory operations."""

    def test_episodic_search_latency(self):
        """Episodic memory search should be < 50ms."""
        from src.memory import EpisodicMemory

        memory = EpisodicMemory(":memory:")
        # Insert test data
        asyncio.run(memory.store("test thread", "user", "test content"))

        latencies = []
        for _ in range(100):
            start = time.time()
            asyncio.run(memory.search("test", limit=10))
            latencies.append(time.time() - start)

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < 0.05, f"P95 latency {p95*1000:.2f}ms exceeds 50ms"


@pytest.mark.benchmark
class TestConcurrentPerformance:
    """Benchmark concurrent request handling."""

    def test_concurrent_health_checks(self, client):
        """Should handle 100 concurrent health checks."""
        import concurrent.futures

        def check_health():
            return client.get("/api/monitoring/health/live").status_code

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_health) for _ in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start
        assert all(r == 200 for r in results)
        assert duration < 5.0, f"100 concurrent requests took {duration:.2f}s"


def generate_benchmark_report():
    """Generate performance benchmark report."""
    report = {
        "timestamp": time.time(),
        "targets": {
            "p50_latency_ms": 200,
            "p95_latency_ms": 500,
            "p99_latency_ms": 1000,
        },
        "benchmarks": []
    }

    # Add benchmark results here
    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
