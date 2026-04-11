"""Tests for MCP Callback framework (C1)."""
import json
import time
import pytest
from unittest.mock import Mock, patch

from src.mcp.callback import (
    CallbackConfig,
    CallbackOutbox,
    CallbackDelivery,
    DeliveryResult,
)


class TestCallbackConfig:
    def test_config_creation(self):
        config = CallbackConfig(
            invocation_id="inv-123",
            token="secret-token",
            api_url="https://api.example.com/callback",
        )
        assert config.invocation_id == "inv-123"
        assert config.token == "secret-token"
        assert config.api_url == "https://api.example.com/callback"

    def test_config_headers(self):
        config = CallbackConfig(
            invocation_id="inv-123",
            token="secret-token",
            api_url="https://api.example.com/callback",
        )
        headers = config.headers
        assert headers["Authorization"] == "Bearer secret-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Invocation-Id"] == "inv-123"


class TestCallbackOutbox:
    def test_queue_message(self):
        outbox = CallbackOutbox()
        outbox.queue(
            invocation_id="inv-123",
            payload={"status": "completed", "result": "done"},
        )
        assert outbox.size("inv-123") == 1

    def test_queue_multiple(self):
        outbox = CallbackOutbox()
        outbox.queue("inv-123", {"seq": 1})
        outbox.queue("inv-123", {"seq": 2})
        outbox.queue("inv-123", {"seq": 3})
        assert outbox.size("inv-123") == 3

    def test_dequeue(self):
        outbox = CallbackOutbox()
        outbox.queue("inv-123", {"data": "test"})
        msg = outbox.dequeue("inv-123")
        assert msg["payload"]["data"] == "test"
        # dequeue doesn't remove, confirm_delivery does
        assert outbox.size("inv-123") == 1
        outbox.confirm_delivery(msg["id"])
        assert outbox.size("inv-123") == 0

    def test_dequeue_empty_returns_none(self):
        outbox = CallbackOutbox()
        assert outbox.dequeue("inv-999") is None

    def test_peek(self):
        outbox = CallbackOutbox()
        outbox.queue("inv-123", {"data": "test"})
        msg = outbox.peek("inv-123")
        assert msg["payload"]["data"] == "test"
        assert outbox.size("inv-123") == 1  # Not removed

    def test_confirm_delivery(self):
        outbox = CallbackOutbox()
        outbox.queue("inv-123", {"data": "test"})
        msg = outbox.dequeue("inv-123")
        outbox.confirm_delivery(msg["id"])
        assert outbox.size("inv-123") == 0

    def test_retry_increment(self):
        outbox = CallbackOutbox()
        outbox.queue("inv-123", {"data": "test"})
        msg = outbox.dequeue("inv-123")
        assert msg["retry_count"] == 0

        outbox.increment_retry(msg["id"])
        msg = outbox.peek("inv-123")
        assert msg["retry_count"] == 1


class TestCallbackDelivery:
    @patch("httpx.post")
    def test_successful_delivery(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"ok": True})

        delivery = CallbackDelivery()
        config = CallbackConfig(
            invocation_id="inv-123",
            token="token",
            api_url="https://api.example.com/callback",
        )

        result = delivery.send(config, {"result": "success"})

        assert result.status == "delivered"
        assert result.attempts == 1
        mock_post.assert_called_once()

    @patch("httpx.post")
    def test_retry_on_failure(self, mock_post):
        mock_post.side_effect = [
            Exception("Connection error"),
            Mock(status_code=200, json=lambda: {"ok": True}),
        ]

        delivery = CallbackDelivery(max_retries=2, base_delay=0.01)
        config = CallbackConfig(
            invocation_id="inv-123",
            token="token",
            api_url="https://api.example.com/callback",
        )

        result = delivery.send(config, {"result": "success"})

        assert result.status == "delivered"
        assert result.attempts == 2
        assert mock_post.call_count == 2

    @patch("httpx.post")
    def test_max_retries_exhausted(self, mock_post):
        mock_post.side_effect = Exception("Always fails")

        delivery = CallbackDelivery(max_retries=3, base_delay=0.01)
        config = CallbackConfig(
            invocation_id="inv-123",
            token="token",
            api_url="https://api.example.com/callback",
        )

        result = delivery.send(config, {"result": "success"})

        assert result.status == "failed"
        assert result.attempts == 3
        assert "Always fails" in result.error

    @patch("httpx.post")
    def test_non_retryable_status_code(self, mock_post):
        mock_post.return_value = Mock(status_code=400, text="Bad request")

        delivery = CallbackDelivery()
        config = CallbackConfig(
            invocation_id="inv-123",
            token="token",
            api_url="https://api.example.com/callback",
        )

        result = delivery.send(config, {"result": "success"})

        assert result.status == "failed"
        assert result.attempts == 1  # No retry for 4xx

    @patch("httpx.post")
    def test_exponential_backoff(self, mock_post):
        mock_post.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Mock(status_code=200),
        ]

        delivery = CallbackDelivery(max_retries=3, base_delay=0.1)
        config = CallbackConfig(
            invocation_id="inv-123",
            token="token",
            api_url="https://api.example.com/callback",
        )

        start = time.time()
        result = delivery.send(config, {"result": "success"})
        elapsed = time.time() - start

        # Should have delays: 0.1s, 0.2s
        assert elapsed >= 0.25
        assert result.status == "delivered"


class TestOutboxPersistence:
    def test_persist_and_restore(self, tmp_path):
        outbox = CallbackOutbox(persist_dir=str(tmp_path))
        outbox.queue("inv-123", {"data": "test"})

        # Create new instance
        outbox2 = CallbackOutbox(persist_dir=str(tmp_path))
        assert outbox2.size("inv-123") == 1
        msg = outbox2.dequeue("inv-123")
        assert msg["payload"]["data"] == "test"
