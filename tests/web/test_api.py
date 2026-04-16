"""Tests for the MeowAI Home Web API."""

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
        # Override the lifespan init to use temp db
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_health_check(app_client):
    """Test health endpoint."""
    response = await app_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.8.0"


@pytest.mark.asyncio
async def test_create_thread(app_client):
    """Test POST /api/threads."""
    response = await app_client.post("/api/threads", json={"name":"Test Thread", "project_path": "/tmp/test"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Thread"
    assert data["current_cat_id"] == "orange"
    assert data["is_archived"] is False
    assert "id" in data
    assert data["messages"] == []


@pytest.mark.asyncio
async def test_create_thread_custom_cat(app_client):
    """Test POST /api/threads with custom cat."""
    response = await app_client.post(
        "/api/threads", json={"name":"Patch Thread", "cat_id": "patch", "project_path": "/tmp/test"}
    )
    assert response.status_code == 200
    assert response.json()["current_cat_id"] == "patch"


@pytest.mark.asyncio
async def test_list_threads(app_client):
    """Test GET /api/threads."""
    await app_client.post("/api/threads", json={"name":"Thread 1", "project_path": "/tmp/test"})
    await app_client.post("/api/threads", json={"name":"Thread 2", "project_path": "/tmp/test"})

    response = await app_client.get("/api/threads")
    assert response.status_code == 200
    data = response.json()
    assert len(data["threads"]) == 2


@pytest.mark.asyncio
async def test_get_thread(app_client):
    """Test GET /api/threads/{id}."""
    create_resp = await app_client.post("/api/threads", json={"name":"My Thread", "project_path": "/tmp/test"})
    thread_id = create_resp.json()["id"]

    response = await app_client.get(f"/api/threads/{thread_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "My Thread"


@pytest.mark.asyncio
async def test_get_thread_not_found(app_client):
    """Test GET /api/threads/{id} with invalid id."""
    response = await app_client.get("/api/threads/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rename_thread(app_client):
    """Test PATCH /api/threads/{id}."""
    create_resp = await app_client.post("/api/threads", json={"name":"Old Name", "project_path": "/tmp/test"})
    thread_id = create_resp.json()["id"]

    response = await app_client.patch(
        f"/api/threads/{thread_id}", json={"name": "New Name"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_thread(app_client):
    """Test DELETE /api/threads/{id}."""
    create_resp = await app_client.post("/api/threads", json={"name":"To Delete", "project_path": "/tmp/test"})
    thread_id = create_resp.json()["id"]

    response = await app_client.delete(f"/api/threads/{thread_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_resp = await app_client.get(f"/api/threads/{thread_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_archive_thread(app_client):
    """Test POST /api/threads/{id}/archive."""
    create_resp = await app_client.post("/api/threads", json={"name":"To Archive", "project_path": "/tmp/test"})
    thread_id = create_resp.json()["id"]

    response = await app_client.post(f"/api/threads/{thread_id}/archive")
    assert response.status_code == 200
    assert response.json()["is_archived"] is True


@pytest.mark.asyncio
async def test_get_messages_empty(app_client):
    """Test GET /api/threads/{id}/messages with no messages."""
    create_resp = await app_client.post("/api/threads", json={"name":"Empty", "project_path": "/tmp/test"})
    thread_id = create_resp.json()["id"]

    response = await app_client.get(f"/api/threads/{thread_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_thread_validation_empty_name(app_client):
    """Test POST /api/threads rejects empty name."""
    response = await app_client.post("/api/threads", json={"name":""})
    assert response.status_code == 422
