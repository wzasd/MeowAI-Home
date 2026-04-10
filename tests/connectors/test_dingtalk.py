"""DingTalk connector tests"""
import hashlib
import hmac
import time

import pytest

from src.connectors.base import PlatformMessage
from src.connectors.dingtalk import DingTalkConnector


@pytest.fixture
def connector():
    return DingTalkConnector(app_key="ding123", app_secret="secret_key")


@pytest.fixture
def valid_text_payload():
    return {
        "msgtype": "text",
        "text": {"content": "Hello bot"},
        "conversationId": "cid_sample_conv_001",
        "senderStaffId": "staff_zhangsan",
        "senderId": "user_zhangsan_id",
        "senderNick": "Zhang San",
        "chatbotUserId": "bot_001",
    }


class TestDingTalkParseMessage:
    """Test parse_message for DingTalk payloads."""

    def test_parse_valid_text_message(self, connector, valid_text_payload):
        msg = connector.parse_message(valid_text_payload)
        assert isinstance(msg, PlatformMessage)
        assert msg.platform == "dingtalk"
        assert msg.chat_id == "cid_sample_conv_001"
        assert msg.user_id == "staff_zhangsan"
        assert msg.user_name == "Zhang San"
        assert msg.content == "Hello bot"
        assert msg.raw == valid_text_payload

    def test_parse_fallback_to_sender_id(self, connector):
        """When senderStaffId is absent, fall back to senderId."""
        payload = {
            "msgtype": "text",
            "text": {"content": "fallback"},
            "conversationId": "cid_002",
            "senderId": "user_only_id",
            "senderNick": "Li Si",
        }
        msg = connector.parse_message(payload)
        assert msg is not None
        assert msg.user_id == "user_only_id"

    def test_parse_non_text_message_returns_none(self, connector):
        payload = {
            "msgtype": "picture",
            "picture": {"downloadCode": "abc"},
            "conversationId": "cid_003",
            "senderStaffId": "staff_001",
            "senderNick": "Test",
        }
        assert connector.parse_message(payload) is None

    def test_parse_message_with_missing_fields_returns_none(self, connector):
        # Missing text content
        payload = {"msgtype": "text", "conversationId": "cid_004"}
        assert connector.parse_message(payload) is None

    def test_parse_empty_payload_returns_none(self, connector):
        assert connector.parse_message({}) is None


class TestDingTalkValidateRequest:
    """Test HMAC-SHA256 signature validation."""

    @pytest.mark.asyncio
    async def test_validate_correct_signature(self, connector):
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{connector.app_secret}"
        sign = hmac.new(
            connector.app_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {"timestamp": timestamp, "sign": sign}
        body = b'{"msgtype":"text"}'
        assert await connector.validate_request(headers, body) is True

    @pytest.mark.asyncio
    async def test_validate_wrong_signature_returns_false(self, connector):
        headers = {"timestamp": "1234567890", "sign": "badsignature123"}
        body = b'{"msgtype":"text"}'
        assert await connector.validate_request(headers, body) is False

    @pytest.mark.asyncio
    async def test_validate_missing_headers_returns_false(self, connector):
        assert await connector.validate_request({}, b"body") is False


class TestDingTalkThreadMapping:
    """Test thread ID mapping inherited from BaseConnector."""

    def test_map_chat_to_thread(self, connector):
        thread_id = connector.map_chat_to_thread("cid_xxx")
        assert thread_id == "dingtalk:cid_xxx"

    def test_map_thread_to_chat_reverses(self, connector):
        thread_id = connector.map_chat_to_thread("cid_xxx")
        assert connector.map_thread_to_chat(thread_id) == "cid_xxx"


class TestDingTalkSendResponse:
    """Test send_response using mocked httpx.AsyncClient."""

    @pytest.mark.asyncio
    async def test_send_response_returns_true(self, connector, monkeypatch):
        """For DingTalk outgoing webhooks, reply is returned in HTTP body."""
        # DingTalk outgoing webhooks: response is returned directly in
        # the HTTP response body, so send_response always returns True.
        from src.connectors.base import PlatformResponse

        response = PlatformResponse(text="Got it!")
        result = await connector.send_response("cid_001", response)
        assert result is True
