"""Tests for connector binding API routes."""

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListConnectors:
    """Tests for GET /api/connectors endpoint."""

    def test_list_connectors(self, client):
        """Test listing all connectors."""
        response = client.get("/api/connectors")
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert len(data["connectors"]) == 4
        names = [c["name"] for c in data["connectors"]]
        assert "feishu" in names
        assert "dingtalk" in names
        assert "weixin" in names
        assert "wecom_bot" in names

    def test_connector_fields(self, client):
        """Test connector has expected fields."""
        response = client.get("/api/connectors")
        data = response.json()
        feishu = next(c for c in data["connectors"] if c["name"] == "feishu")
        assert feishu["displayName"] == "飞书"
        assert feishu["enabled"] is True
        assert "features" in feishu
        assert "configFields" in feishu


class TestBindingStatus:
    """Tests for GET /api/connectors/{name}/binding-status endpoint."""

    def test_binding_status_default(self, client):
        """Test default binding status (not bound)."""
        response = client.get("/api/connectors/feishu/binding-status")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "feishu"
        assert data["bound"] is False
        assert data["bound_at"] is None
        assert data["bound_user"] is None


class TestGetQr:
    """Tests for GET /api/connectors/{name}/qr endpoint."""

    def test_get_qr(self, client):
        """Test generating QR code."""
        response = client.get("/api/connectors/feishu/qr")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "feishu"
        assert "qr_data_url" in data
        assert data["qr_data_url"].startswith("data:image/svg+xml;base64,")
        assert "bind_url" in data
        assert "token" in data
        assert data["expires_in"] == 300


class TestBindCallback:
    """Tests for POST /api/connectors/{name}/bind-callback endpoint."""

    def test_bind_success(self, client):
        """Test successful bind via callback."""
        # First get a QR token
        qr_response = client.get("/api/connectors/dingtalk/qr")
        token = qr_response.json()["token"]

        # Bind
        response = client.post(
            "/api/connectors/dingtalk/bind-callback",
            json={"token": token, "user_name": "测试用户"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["bound"] is True
        assert data["bound_user"] == "测试用户"

        # Verify binding status
        status_response = client.get("/api/connectors/dingtalk/binding-status")
        status = status_response.json()
        assert status["bound"] is True
        assert status["bound_user"] == "测试用户"
        assert status["bound_at"] is not None

    def test_bind_invalid_token(self, client):
        """Test bind with invalid token."""
        response = client.post(
            "/api/connectors/feishu/bind-callback",
            json={"token": "invalid-token", "user_name": "黑客"},
        )
        assert response.status_code == 400


class TestUnbind:
    """Tests for POST /api/connectors/{name}/unbind endpoint."""

    def test_unbind_not_bound(self, client):
        """Test unbinding a connector that isn't bound."""
        response = client.post("/api/connectors/weixin/unbind")
        assert response.status_code == 400

    def test_unbind_success(self, client):
        """Test successful unbind."""
        # First bind
        qr_response = client.get("/api/connectors/wecom_bot/qr")
        token = qr_response.json()["token"]
        client.post(
            "/api/connectors/wecom_bot/bind-callback",
            json={"token": token, "user_name": "测试"},
        )

        # Unbind
        response = client.post("/api/connectors/wecom_bot/unbind")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify unbound
        status_response = client.get("/api/connectors/wecom_bot/binding-status")
        assert status_response.json()["bound"] is False


class TestEnableDisable:
    """Tests for enable/disable endpoints."""

    def test_enable_connector(self, client):
        """Test enabling a connector."""
        response = client.post("/api/connectors/weixin/enable")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_disable_connector(self, client):
        """Test disabling a connector."""
        response = client.post("/api/connectors/feishu/disable")
        assert response.status_code == 200
        assert response.json()["success"] is True
