"""Tests for metrics API routes."""
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with a temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        # Initialize registries
        from src.models.cat_registry import CatRegistry
        from src.models.agent_registry import AgentRegistry
        cat_reg = CatRegistry()
        agent_reg = AgentRegistry()

        # Load cat config if exists
        try:
            from src.models.registry_init import initialize_registries
            cat_reg, agent_reg = initialize_registries("cat-config.json")
        except Exception:
            pass  # Use empty registries

        app.state.cat_registry = cat_reg
        app.state.agent_registry = agent_reg

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        # Point metrics store to temp database so tests are isolated
        from src.metrics.sqlite_store import MetricsSQLiteStore
        import src.web.routes.metrics as metrics_module
        original_store = metrics_module.store
        metrics_module.store = MetricsSQLiteStore(db_path=db_path)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client

        metrics_module.store = original_store
        ThreadManager.reset()


@pytest.mark.asyncio
async def test_get_global_token_usage(app_client):
    """Test getting global token usage."""
    response = await app_client.get("/api/metrics/token-usage")
    assert response.status_code == 200
    data = response.json()
    assert "promptTokens" in data
    assert "completionTokens" in data
    assert "cacheHitRate" in data
    assert "totalCost" in data
    assert isinstance(data["promptTokens"], int)
    assert isinstance(data["completionTokens"], int)
    assert isinstance(data["cacheHitRate"], float)
    assert isinstance(data["totalCost"], float)


@pytest.mark.asyncio
async def test_get_thread_token_usage(app_client):
    """Test getting token usage for a specific thread."""
    thread_id = "test-thread-123"
    response = await app_client.get(f"/api/metrics/token-usage?threadId={thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert "promptTokens" in data
    assert "completionTokens" in data
    assert "cacheHitRate" in data
    assert "totalCost" in data
    # New thread should start with zero usage
    assert data["promptTokens"] == 0
    assert data["completionTokens"] == 0
    assert data["cacheHitRate"] == 0.0
    assert data["totalCost"] == 0.0


@pytest.mark.asyncio
async def test_track_token_usage(app_client):
    """Test tracking token usage for a thread."""
    thread_id = "test-thread-456"

    # Track some usage
    response = await app_client.post(
        "/api/metrics/token-usage/track",
        params={
            "threadId": thread_id,
            "promptTokens": 1000,
            "completionTokens": 500,
            "cost": 0.05,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify the usage was recorded
    response = await app_client.get(f"/api/metrics/token-usage?threadId={thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["promptTokens"] == 1000
    assert data["completionTokens"] == 500
    assert data["totalCost"] == 0.05


@pytest.mark.asyncio
async def test_track_token_usage_accumulates(app_client):
    """Test that tracking usage accumulates correctly."""
    thread_id = "test-thread-789"

    # Track usage twice
    await app_client.post(
        "/api/metrics/token-usage/track",
        params={
            "threadId": thread_id,
            "promptTokens": 1000,
            "completionTokens": 500,
            "cost": 0.05,
        },
    )
    await app_client.post(
        "/api/metrics/token-usage/track",
        params={
            "threadId": thread_id,
            "promptTokens": 2000,
            "completionTokens": 1000,
            "cost": 0.10,
        },
    )

    # Verify accumulated usage
    response = await app_client.get(f"/api/metrics/token-usage?threadId={thread_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["promptTokens"] == 3000
    assert data["completionTokens"] == 1500
    assert abs(data["totalCost"] - 0.15) < 0.001


@pytest.mark.asyncio
async def test_cache_hit_rate_calculation(app_client):
    """Test that cache hit rate is calculated correctly."""
    thread_id = "test-thread-cache"

    await app_client.post(
        "/api/metrics/token-usage/track",
        params={
            "threadId": thread_id,
            "promptTokens": 800,
            "completionTokens": 200,
            "cost": 0.05,
        },
    )

    response = await app_client.get(f"/api/metrics/token-usage?threadId={thread_id}")
    assert response.status_code == 200
    data = response.json()
    # Cache hit rate = min(0.95, promptTokens / total * 0.8)
    # = min(0.95, 800 / 1000 * 0.8) = min(0.95, 0.64) = 0.64
    assert abs(data["cacheHitRate"] - 0.64) < 0.001
