"""End-to-end test for Provider Account Configuration system."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.web.app import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_account_crud_e2e(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List accounts — should have builtins
        resp = await client.get("/api/config/accounts")
        assert resp.status_code == 200
        accounts = resp.json()["accounts"]
        ids = [a["id"] for a in accounts]
        assert "builtin-anthropic" in ids
        assert "builtin-openai" in ids

        # Create API key account
        resp = await client.post("/api/config/accounts", json={
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
        resp = await client.get("/api/config/accounts/test-anthropic")
        assert resp.status_code == 200
        assert resp.json()["displayName"] == "Test Anthropic Key"

        # Update account
        resp = await client.patch("/api/config/accounts/test-anthropic", json={
            "displayName": "Updated Key",
        })
        assert resp.status_code == 200
        assert resp.json()["displayName"] == "Updated Key"

        # Delete account
        resp = await client.delete("/api/config/accounts/test-anthropic")
        assert resp.status_code == 200

        # Verify deleted
        resp = await client.get("/api/config/accounts")
        ids = [a["id"] for a in resp.json()["accounts"]]
        assert "test-anthropic" not in ids


@pytest.mark.anyio
async def test_cannot_delete_builtin_account(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/config/accounts/builtin-anthropic")
        assert resp.status_code == 400


@pytest.mark.anyio
async def test_bind_cat_to_account(app):
    """Bind-cat endpoint validates cat exists and returns proper error."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        acc_id = "bind-test-e2e"
        resp = await client.post("/api/config/accounts", json={
            "id": acc_id,
            "displayName": "Bind Test",
            "protocol": "anthropic",
            "authType": "api_key",
            "apiKey": "sk-bind-test",
        })
        assert resp.status_code == 200

        # Bind with nonexistent cat → 404
        resp = await client.patch("/api/config/accounts/bind-cat", json={
            "catId": "nonexistent-cat-xyz",
            "accountRef": acc_id,
        })
        assert resp.status_code == 404

        # Cleanup
        await client.delete(f"/api/config/accounts/{acc_id}")

        # Cleanup
        await client.delete("/api/config/runtime-cats/test-bind-cat")
        await client.delete(f"/api/config/accounts/{acc_id}")


@pytest.mark.anyio
async def test_cat_response_includes_account_ref(app):
    """Verify cats API returns accountRef field when lifespan initializes registry."""
    from starlette.testclient import TestClient
    # Use TestClient which triggers lifespan
    with TestClient(app) as client:
        resp = client.get("/api/cats")
        assert resp.status_code == 200
        cats = resp.json().get("cats", [])
        if cats:
            for cat in cats:
                assert "accountRef" in cat
