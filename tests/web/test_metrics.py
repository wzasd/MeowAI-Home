"""Tests for metrics API routes."""
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.web.app import create_app
from src.metrics.sqlite_store import MetricsSQLiteStore
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with a temp database for metrics."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        app = create_app()

        # Monkey-patch the metrics store to use temp DB
        import src.web.routes.metrics as metrics_module
        original_store = metrics_module.store
        metrics_module.store = MetricsSQLiteStore(db_path=db_path)

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client

        metrics_module.store = original_store


@pytest.mark.anyio
async def test_get_cat_metrics_empty(app_client):
    """Get metrics for a cat with no records."""
    response = await app_client.get("/api/metrics/cats?cat_id=orange&days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["cat_id"] == "orange"
    assert data["days"] == 7
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_leaderboard_empty(app_client):
    """Get leaderboard with no records."""
    response = await app_client.get("/api/metrics/leaderboard?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["days"] == 7
    assert data["leaderboard"] == []


@pytest.mark.anyio
async def test_get_cat_metrics_with_data(app_client):
    """Get metrics after saving a record."""
    from src.metrics.collector import InvocationRecord

    record = InvocationRecord(
        cat_id="orange",
        thread_id="t1",
        project_path="/tmp",
        prompt_tokens=100,
        completion_tokens=200,
        success=True,
        duration_ms=50,
    )
    import src.web.routes.metrics as metrics_module
    await metrics_module.store.save(record)

    response = await app_client.get("/api/metrics/cats?cat_id=orange&days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["cat_id"] == "orange"
    assert len(data["data"]) == 1
    assert data["data"][0]["prompt_tokens"] == 100
    assert data["data"][0]["completion_tokens"] == 200


@pytest.mark.anyio
async def test_get_leaderboard_with_data(app_client):
    """Get leaderboard after saving records."""
    from src.metrics.collector import InvocationRecord

    import src.web.routes.metrics as metrics_module
    await metrics_module.store.save(
        InvocationRecord(
            cat_id="orange",
            thread_id="t1",
            project_path="/tmp",
            prompt_tokens=100,
            completion_tokens=200,
            success=True,
            duration_ms=50,
        )
    )
    await metrics_module.store.save(
        InvocationRecord(
            cat_id="inky",
            thread_id="t2",
            project_path="/tmp",
            prompt_tokens=50,
            completion_tokens=100,
            success=False,
            duration_ms=30,
        )
    )

    response = await app_client.get("/api/metrics/leaderboard?days=7")
    assert response.status_code == 200
    data = response.json()
    assert len(data["leaderboard"]) == 2

    orange = next(r for r in data["leaderboard"] if r["cat_id"] == "orange")
    assert orange["total_calls"] == 1
    assert orange["prompt_tokens"] == 100
    assert orange["success_rate"] == 1.0

    inky = next(r for r in data["leaderboard"] if r["cat_id"] == "inky")
    assert inky["total_calls"] == 1
    assert inky["success_rate"] == 0.0
