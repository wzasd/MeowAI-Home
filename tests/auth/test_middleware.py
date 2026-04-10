"""Auth middleware tests"""
import pytest
import time
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse

from src.auth.middleware import AuthMiddleware
from src.auth.models import User


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/public")
    def public():
        return {"message": "public"}

    @app.get("/protected")
    def protected(request: Request):
        user = getattr(request.state, "user", None)
        return {"user": user}

    return app


@pytest.fixture
def client(app):
    app.add_middleware(
        AuthMiddleware,
        secret="test-secret",
        public_paths=["/public", "/health"]
    )
    return TestClient(app)


class TestPublicPaths:
    def test_public_path_no_token(self, client):
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json()["message"] == "public"

    def test_health_path_no_token(self, client):
        response = client.get("/health")
        # 404 because route doesn't exist, not 401
        assert response.status_code == 404


class TestProtectedPaths:
    def test_protected_no_token_returns_401(self, client):
        response = client.get("/protected")
        assert response.status_code == 401
        assert "authorization" in response.json()["error"].lower()

    def test_protected_invalid_token_format(self, client):
        response = client.get("/protected", headers={"Authorization": "Basic xyz"})
        assert response.status_code == 401

    def test_protected_valid_token(self, client):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("test-secret")
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["user"]["sub"] == "alice"

    def test_protected_expired_token(self, client):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("test-secret", expires_in=-1)
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert "expired" in response.json()["error"].lower()

    def test_protected_wrong_secret(self, client):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("wrong-secret")
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert "invalid" in response.json()["error"].lower()


class TestMiddlewareConfiguration:
    def test_custom_public_paths(self, app):
        app.add_middleware(
            AuthMiddleware,
            secret="test-secret",
            public_paths=["/custom-public"]
        )
        client = TestClient(app)
        response = client.get("/public")  # Not in public paths anymore
        assert response.status_code == 401
