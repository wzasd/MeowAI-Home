"""User model tests"""
import pytest
import time
from src.auth.models import User


class TestUserPasswordHash:
    def test_hash_password_deterministic(self):
        h1 = User.hash_password("secret123")
        h2 = User.hash_password("secret123")
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_hash_password_different_for_different_passwords(self):
        h1 = User.hash_password("password1")
        h2 = User.hash_password("password2")
        assert h1 != h2

    def test_verify_password_correct(self):
        user = User(
            id=1,
            username="test",
            password_hash=User.hash_password("secret"),
            role="member",
            created_at=time.time(),
        )
        assert user.verify_password("secret") is True

    def test_verify_password_incorrect(self):
        user = User(
            id=1,
            username="test",
            password_hash=User.hash_password("secret"),
            role="member",
            created_at=time.time(),
        )
        assert user.verify_password("wrong") is False


class TestUserToken:
    def test_generate_token_creates_valid_jwt(self):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("secret-key")
        assert isinstance(token, str)
        assert "." in token  # JWT format

    def test_verify_token_valid(self):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("secret-key")
        payload = User.verify_token(token, "secret-key")
        assert payload is not None
        assert payload["sub"] == "alice"
        assert payload["role"] == "admin"

    def test_verify_token_wrong_secret(self):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        token = user.generate_token("secret-key")
        payload = User.verify_token(token, "wrong-secret")
        assert payload is None

    def test_verify_token_expired(self):
        user = User(
            id=1,
            username="alice",
            password_hash="hash",
            role="admin",
            created_at=time.time(),
        )
        # Create expired token (expires_in=-1)
        token = user.generate_token("secret-key", expires_in=-1)
        payload = User.verify_token(token, "secret-key")
        assert payload is None


class TestUserTokenExpiration:
    def test_token_expires_after_duration(self):
        user = User(
            id=1,
            username="test",
            password_hash="hash",
            role="member",
            created_at=time.time(),
        )
        # Short expiration
        token = user.generate_token("secret", expires_in=1)
        # Token should be valid now
        assert User.verify_token(token, "secret") is not None
        # Wait for expiration
        time.sleep(1.1)
        # Token should be expired
        assert User.verify_token(token, "secret") is None
