"""Tests for connector messages API routes."""

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client():
    """Create authenticated test client."""
    app = create_app()
    with TestClient(app) as c:
        c.post("/api/auth/register", json={"username": "testuser", "password": "testpass", "role": "admin"})
        resp = c.post("/api/auth/login", json={"username": "testuser", "password": "testpass"})
        token = resp.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class TestListMessages:
    """Tests for GET /api/connectors/messages endpoint."""

    def test_list_messages_empty(self, client):
        """Test listing messages when none exist."""
        response = client.get("/api/connectors/messages")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert isinstance(data["messages"], list)

    def test_list_messages_with_connector_filter(self, client):
        """Test listing messages with connector filter."""
        response = client.get("/api/connectors/messages?connector=feishu")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data


class TestCreateMessage:
    """Tests for POST /api/connectors/messages endpoint."""

    def test_create_message_minimal(self, client):
        """Test creating message with minimal data."""
        response = client.post(
            "/api/connectors/messages",
            json={
                "connector": "feishu",
                "sender": {"id": "u1", "name": "张三"},
                "content": "Hello from Feishu!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Hello from Feishu!"
        assert data["connector"] == "feishu"
        assert data["id"] is not None
        assert data["timestamp"] is not None
        assert data["icon"] == "📱"  # auto-detected from connector

    def test_create_message_full(self, client):
        """Test creating message with all fields."""
        response = client.post(
            "/api/connectors/messages",
            json={
                "connector": "github",
                "connector_type": "system",
                "sender": {"id": "bot", "name": "GitHub Bot", "avatar": "https://github.com/bot.png"},
                "content": "PR #123 merged",
                "content_blocks": [
                    {"type": "text", "text": "PR #123 merged"},
                    {"type": "image", "url": "https://example.com/img.png"},
                ],
                "source_url": "https://github.com/repo/pull/123",
                "icon": "🐙",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["connector"] == "github"
        assert data["connector_type"] == "system"
        assert data["source_url"] == "https://github.com/repo/pull/123"
        assert len(data["content_blocks"]) == 2

    def test_create_message_all_connectors(self, client):
        """Test creating messages for all connector types."""
        connectors = ["feishu", "dingtalk", "weixin", "wecom", "github", "scheduler", "system"]
        for connector in connectors:
            response = client.post(
                "/api/connectors/messages",
                json={
                    "connector": connector,
                    "sender": {"id": "u1", "name": "Test"},
                    "content": f"Message from {connector}",
                },
            )
            assert response.status_code == 200


class TestGetMessage:
    """Tests for GET /api/connectors/messages/{id} endpoint."""

    def test_get_message_not_found(self, client):
        """Test getting non-existent message."""
        response = client.get("/api/connectors/messages/nonexistent")
        assert response.status_code == 404

    def test_get_message_success(self, client):
        """Test getting existing message."""
        # Create a message first
        create_response = client.post(
            "/api/connectors/messages",
            json={
                "connector": "feishu",
                "sender": {"id": "u1", "name": "Test"},
                "content": "Get test message",
            },
        )
        msg = create_response.json()

        # Get it
        response = client.get(f"/api/connectors/messages/{msg['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == msg["id"]


class TestDeleteMessage:
    """Tests for DELETE /api/connectors/messages/{id} endpoint."""

    def test_delete_message_not_found(self, client):
        """Test deleting non-existent message."""
        response = client.delete("/api/connectors/messages/nonexistent")
        assert response.status_code == 404

    def test_delete_message_success(self, client):
        """Test deleting existing message."""
        # Create a message
        create_response = client.post(
            "/api/connectors/messages",
            json={
                "connector": "feishu",
                "sender": {"id": "u1", "name": "Test"},
                "content": "Delete test",
            },
        )
        msg = create_response.json()

        # Delete it
        response = client.delete(f"/api/connectors/messages/{msg['id']}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it's gone
        get_response = client.get(f"/api/connectors/messages/{msg['id']}")
        assert get_response.status_code == 404


class TestConnectorThemes:
    """Tests for GET /api/connectors/themes/{connector} endpoint."""

    def test_get_theme_feishu(self, client):
        """Test getting feishu theme."""
        response = client.get("/api/connectors/themes/feishu")
        assert response.status_code == 200
        data = response.json()
        assert "avatar" in data
        assert "label" in data
        assert "bubble" in data
        assert "blue" in data["avatar"]

    def test_get_theme_all_connectors(self, client):
        """Test getting themes for all connectors."""
        connectors = ["feishu", "dingtalk", "weixin", "wecom", "github", "scheduler", "system"]
        for connector in connectors:
            response = client.get(f"/api/connectors/themes/{connector}")
            assert response.status_code == 200


class TestConnectorIcons:
    """Tests for GET /api/connectors/icons/{connector} endpoint."""

    def test_get_icon_feishu(self, client):
        """Test getting feishu icon."""
        response = client.get("/api/connectors/icons/feishu")
        assert response.status_code == 200
        data = response.json()
        assert "icon" in data
