"""Tests for cat management API routes."""
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

        # Initialize cat_registry
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

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_list_cats(app_client):
    response = await app_client.get("/api/cats")
    assert response.status_code == 200
    data = response.json()
    assert "cats" in data
    assert isinstance(data["cats"], list)


@pytest.mark.asyncio
async def test_get_cat_detail(app_client):
    # First list cats to get a valid ID
    list_resp = await app_client.get("/api/cats")
    cats = list_resp.json()["cats"]

    if not cats:
        pytest.skip("No cats configured")

    cat_id = cats[0]["id"]
    response = await app_client.get(f"/api/cats/{cat_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == cat_id


@pytest.mark.asyncio
async def test_get_cat_not_found(app_client):
    response = await app_client.get("/api/cats/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_cat_budget(app_client):
    list_resp = await app_client.get("/api/cats")
    cats = list_resp.json()["cats"]

    if not cats:
        pytest.skip("No cats configured")

    cat_id = cats[0]["id"]
    response = await app_client.get(f"/api/cats/{cat_id}/budget")
    assert response.status_code == 200
    data = response.json()
    assert "budget" in data


@pytest.mark.asyncio
async def test_list_env_vars(app_client):
    response = await app_client.get("/api/config/env")
    assert response.status_code == 200
    data = response.json()
    assert "variables" in data
    assert "categories" in data


@pytest.mark.asyncio
async def test_get_env_var(app_client):
    response = await app_client.get("/api/config/env/MEOWAI_ENV")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "MEOWAI_ENV"


@pytest.mark.asyncio
async def test_list_connectors(app_client):
    response = await app_client.get("/api/connectors")
    assert response.status_code == 200
    data = response.json()
    assert "connectors" in data
    assert len(data["connectors"]) >= 4
