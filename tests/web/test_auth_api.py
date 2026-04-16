"""Tests for the authentication API."""

import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app


@pytest.fixture
async def app_client():
    """Create a test client with temp databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_register_success(app_client):
    """Test successful user registration."""
    response = await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123", "role": "admin"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_register_duplicate_username(app_client):
    """Test registration with duplicate username returns 409."""
    await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    response = await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "otherpass"},
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_role(app_client):
    """Test registration with invalid role returns 400."""
    response = await app_client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "secret123", "role": "superuser"},
    )
    assert response.status_code == 400
    assert "Invalid role" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(app_client):
    """Test successful login returns JWT token."""
    await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    response = await app_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["username"] == "alice"
    assert data["role"] == "member"
    assert "access_token" in data
    assert isinstance(data["access_token"], str)


@pytest.mark.asyncio
async def test_login_invalid_credentials(app_client):
    """Test login with wrong password returns 401."""
    await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123"},
    )
    response = await app_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpass"},
    )
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_authenticated(app_client):
    """Test /auth/me with valid token."""
    await app_client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "secret123", "role": "admin"},
    )
    login_resp = await app_client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    token = login_resp.json()["access_token"]

    response = await app_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_unauthenticated(app_client):
    """Test /auth/me without token returns 401 via middleware."""
    response = await app_client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Missing or invalid authorization header" in response.json()["error"]


@pytest.mark.asyncio
async def test_me_invalid_token(app_client):
    """Test /auth/me with invalid token returns 401."""
    response = await app_client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert "Invalid token" in response.json()["error"]


@pytest.mark.asyncio
async def test_protected_route_requires_auth(app_client):
    """Test that a protected route rejects unauthenticated requests."""
    response = await app_client.get("/api/threads")
    assert response.status_code == 401
    assert "Missing or invalid authorization header" in response.json()["error"]
