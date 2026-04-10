"""Tests for FeishuConnector platform adapter."""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connectors.base import PlatformMessage, PlatformResponse
from src.connectors.feishu import FeishuConnector


@pytest.fixture
def connector():
    return FeishuConnector(
        app_id="cli_test_app_id",
        app_secret="test_app_secret",
        verification_token="test_verification_token",
    )


# ---- Test 1: Parse valid text message event ----

def test_parse_valid_text_message(connector):
    """Parse a valid Feishu text message event into PlatformMessage."""
    payload = {
        "event": {
            "message": {
                "chat_id": "oc_abc123",
                "message_id": "om_xyz789",
                "content": json.dumps({"text": "Hello from Feishu!"}),
                "msg_type": "text",
            },
            "sender": {
                "sender_id": {"user_id": "ou_user001"},
                "sender_type": "user",
            },
        }
    }

    result = connector.parse_message(payload)

    assert isinstance(result, PlatformMessage)
    assert result.platform == "feishu"
    assert result.chat_id == "oc_abc123"
    assert result.user_id == "ou_user001"
    assert result.content == "Hello from Feishu!"
    assert result.raw == payload


# ---- Test 2: Parse message with missing event data returns None ----

def test_parse_missing_event_data_returns_none(connector):
    """Return None when payload lacks event or message data."""
    # No event key at all
    assert connector.parse_message({}) is None

    # Event exists but no message key
    assert connector.parse_message({"event": {}}) is None

    # Event.message exists but missing chat_id
    assert connector.parse_message({"event": {"message": {"content": "{}"}}}) is None


# ---- Test 3: Validate correct signature returns True ----

@pytest.mark.asyncio
async def test_validate_correct_signature(connector):
    """Return True when X-Lark-Signature matches computed HMAC."""
    timestamp = "1712736000"
    body = b'{"event":{"message":{"content":"hi"}}}'

    # Compute expected signature the same way the connector does
    sign_content = f"{timestamp}{connector.verification_token}".encode("utf-8") + body
    expected_sig = hmac.new(
        connector.verification_token.encode("utf-8"),
        sign_content,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "X-Lark-Signature": expected_sig,
        "X-Lark-Request-Timestamp": timestamp,
    }

    assert await connector.validate_request(headers, body) is True


# ---- Test 4: Validate wrong signature returns False ----

@pytest.mark.asyncio
async def test_validate_wrong_signature(connector):
    """Return False when X-Lark-Signature does not match."""
    headers = {
        "X-Lark-Signature": "deadbeef_invalid_sig",
        "X-Lark-Request-Timestamp": "1712736000",
    }
    body = b'{"event":{}}'

    assert await connector.validate_request(headers, body) is False


# ---- Test 5: map_chat_to_thread returns "feishu:oc_xxx" ----

def test_map_chat_to_thread(connector):
    """Map Feishu chat_id to internal thread_id with platform prefix."""
    assert connector.map_chat_to_thread("oc_xxx") == "feishu:oc_xxx"


# ---- Test 6: map_thread_to_chat reverses correctly ----

def test_map_thread_to_chat(connector):
    """Reverse map internal thread_id back to Feishu chat_id."""
    assert connector.map_thread_to_chat("feishu:oc_xxx") == "oc_xxx"


# ---- Test 7: Send response calls correct API endpoint ----

@pytest.mark.asyncio
async def test_send_response_calls_correct_endpoint(connector):
    """POST reply to Feishu im/v1/messages with correct payload."""
    mock_post = AsyncMock()
    mock_post.return_value = MagicMock(status_code=200)
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    mock_acm.__aexit__ = AsyncMock(return_value=False)

    # Stub _get_access_token so we don't hit the real API
    connector._get_access_token = AsyncMock(return_value="tenant_token_123")

    with patch("src.connectors.feishu.httpx.AsyncClient", return_value=mock_acm):
        response = PlatformResponse(text="Meow reply")
        result = await connector.send_response("oc_chat001", response)

    assert result is True
    mock_post.assert_awaited_once()
    call_args = mock_post.call_args
    url = call_args.args[0]
    assert "im/v1/messages" in url
    assert "receive_id_type=chat_id" in url


# ---- Test 8: Get access token caches result ----

@pytest.mark.asyncio
async def test_get_access_token_caches_result(connector):
    """_get_access_token should cache and return same token on second call."""
    mock_post = AsyncMock()
    mock_post.return_value = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"tenant_access_token": "cached_token_abc", "expire": 7200}),
    )
    mock_acm = MagicMock()
    mock_acm.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
    mock_acm.__aexit__ = AsyncMock(return_value=False)

    with patch("src.connectors.feishu.httpx.AsyncClient", return_value=mock_acm):
        token1 = await connector._get_access_token()
        token2 = await connector._get_access_token()

    # Should only have made one HTTP call (cached on second)
    assert token1 == "cached_token_abc"
    assert token2 == "cached_token_abc"
    assert mock_post.await_count == 1
