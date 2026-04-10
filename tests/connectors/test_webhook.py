"""Webhook route tests"""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.connectors.webhook import router, register_connector, unregister_connector, list_connectors
from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class DummyConnector(BaseConnector):
    platform = "dummy"

    def __init__(self, valid: bool = True):
        self._valid = valid
        self.last_msg = None

    async def validate_request(self, headers, body) -> bool:
        return self._valid

    def parse_message(self, payload):
        text = payload.get("text", "")
        if not text:
            return None
        return PlatformMessage(
            platform="dummy",
            chat_id=payload.get("chat_id", "c1"),
            user_id=payload.get("user_id", "u1"),
            user_name=payload.get("user_name", "Test"),
            content=text,
        )

    async def send_response(self, chat_id, response) -> bool:
        return True


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    # Clear connectors before each test
    for platform in list_connectors():
        unregister_connector(platform)
    return TestClient(app)


class TestWebhookRouting:
    def test_post_unknown_platform_returns_404(self, client):
        response = client.post("/webhook/unknown", json={"text": "hi"})
        assert response.status_code == 404
        assert "Unknown platform" in response.json()["detail"]

    def test_post_invalid_signature_returns_401(self, client):
        invalid_conn = DummyConnector(valid=False)
        register_connector(invalid_conn)
        response = client.post("/webhook/dummy", json={"text": "hi"})
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid signature"

    def test_post_valid_message_returns_200(self, client):
        valid_conn = DummyConnector(valid=True)
        register_connector(valid_conn)
        response = client.post(
            "/webhook/dummy",
            json={"text": "Hello", "chat_id": "g1", "user_id": "u1", "user_name": "Alice"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["platform"] == "dummy"
        assert "thread_id" in data

    def test_thread_id_mapping(self, client):
        valid_conn = DummyConnector(valid=True)
        register_connector(valid_conn)
        response = client.post(
            "/webhook/dummy",
            json={"text": "Hi", "chat_id": "group123"}
        )
        assert response.status_code == 200
        assert response.json()["thread_id"] == "dummy:group123"

    def test_unparsable_message_returns_ignored(self, client):
        valid_conn = DummyConnector(valid=True)
        register_connector(valid_conn)
        response = client.post("/webhook/dummy", json={"text": ""})  # Empty text returns None
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_multiple_connectors_registered(self, client):
        conn1 = DummyConnector(valid=True)
        conn2 = DummyConnector(valid=True)
        conn2.platform = "dummy2"
        register_connector(conn1)
        register_connector(conn2)
        assert sorted(list_connectors()) == ["dummy", "dummy2"]

    def test_unregister_connector(self, client):
        conn = DummyConnector()
        register_connector(conn)
        assert "dummy" in list_connectors()
        unregister_connector("dummy")
        assert "dummy" not in list_connectors()
