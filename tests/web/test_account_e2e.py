"""End-to-end test for Provider Account Configuration system."""
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient
from src.web.app import create_app
from src.auth.store import AuthStore


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            auth_store = AuthStore(db_path=db_path)
            await auth_store.initialize()
            app.state.auth_store = auth_store

            await client.post(
                "/api/auth/register",
                json={"username": "testuser", "password": "testpass", "role": "admin"},
            )
            resp = await client.post(
                "/api/auth/login",
                json={"username": "testuser", "password": "testpass"},
            )
            token = resp.json()["access_token"]
            client.headers["Authorization"] = f"Bearer {token}"
            yield client


@pytest.mark.anyio
async def test_account_crud_e2e(async_client):
    # List accounts — should have builtins
    resp = await async_client.get("/api/config/accounts")
    assert resp.status_code == 200
    accounts = resp.json()["accounts"]
    ids = [a["id"] for a in accounts]
    assert "builtin-anthropic" in ids
    assert "builtin-openai" in ids

    # Create API key account
    resp = await async_client.post("/api/config/accounts", json={
        "id": "test-anthropic",
        "displayName": "Test Anthropic Key",
        "protocol": "anthropic",
        "authType": "api_key",
        "apiKey": "sk-test-key-123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["hasApiKey"] is True
    assert data["isBuiltin"] is False

    # Get single account
    resp = await async_client.get("/api/config/accounts/test-anthropic")
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Test Anthropic Key"

    # Update account
    resp = await async_client.patch("/api/config/accounts/test-anthropic", json={
        "displayName": "Updated Key",
    })
    assert resp.status_code == 200
    assert resp.json()["displayName"] == "Updated Key"

    # Delete account
    resp = await async_client.delete("/api/config/accounts/test-anthropic")
    assert resp.status_code == 200

    # Verify deleted
    resp = await async_client.get("/api/config/accounts")
    ids = [a["id"] for a in resp.json()["accounts"]]
    assert "test-anthropic" not in ids


@pytest.mark.anyio
async def test_cannot_delete_builtin_account(async_client):
    resp = await async_client.delete("/api/config/accounts/builtin-anthropic")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_bind_cat_to_account(async_client):
    """Bind-cat endpoint validates cat exists and returns proper error."""
    acc_id = "bind-test-e2e"
    resp = await async_client.post("/api/config/accounts", json={
        "id": acc_id,
        "displayName": "Bind Test",
        "protocol": "anthropic",
        "authType": "api_key",
        "apiKey": "sk-bind-test",
    })
    assert resp.status_code == 200

    # Bind with nonexistent cat → 404
    resp = await async_client.patch("/api/config/accounts/bind-cat", json={
        "catId": "nonexistent-cat-xyz",
        "accountRef": acc_id,
    })
    assert resp.status_code == 404

    # Cleanup
    await async_client.delete(f"/api/config/accounts/{acc_id}")


def test_cat_response_includes_account_ref(app):
    """Verify cats API returns accountRef field when lifespan initializes registry."""
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"username": "testuser", "password": "testpass", "role": "admin"})
        resp = client.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
        token = resp.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        resp = client.get("/api/cats")
        assert resp.status_code == 200
        cats = resp.json().get("cats", [])
        if cats:
            for cat in cats:
                assert "accountRef" in cat
