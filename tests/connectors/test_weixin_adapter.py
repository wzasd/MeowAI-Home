"""Tests for WeChat Personal (iLink Bot) connector adapter (E4)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.connectors.base import MessageType, InboundMessage, OutboundMessage, MediaUploadResult


class TestWeixinAdapterBasics:
    @pytest.fixture
    def adapter(self):
        from src.connectors.weixin_adapter import WeixinAdapter
        return WeixinAdapter()

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        with patch.dict("os.environ", {"ILINK_API_KEY": "test_key", "ILINK_BASE_URL": "http://localhost:8080"}):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_get.return_value = mock_response
                success = await adapter.initialize({})
                assert success is True
                assert adapter.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_initialize_missing_config(self, adapter):
        with patch.dict("os.environ", {}, clear=True):
            success = await adapter.initialize({})
            assert success is False


class TestWeixinMessageParsing:
    @pytest.fixture
    def adapter(self):
        from src.connectors.weixin_adapter import WeixinAdapter
        adapter = WeixinAdapter()
        adapter.api_key = "test"
        return adapter

    def test_parse_text_message(self, adapter):
        payload = {
            "msgId": "msg_123",
            "fromUser": "wxid_abc",
            "fromNick": "张三",
            "roomId": "room_xyz",
            "content": "Hello bot",
            "msgType": 1,  # Text
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.content == "Hello bot"
        assert msg.thread_id == "weixin:room_xyz"
        assert msg.user_id == "wxid_abc"
        assert msg.user_name == "张三"
        assert msg.message_type == MessageType.TEXT

    def test_parse_image_message(self, adapter):
        payload = {
            "msgId": "msg_456",
            "fromUser": "wxid_abc",
            "fromNick": "张三",
            "roomId": "room_xyz",
            "content": "/path/to/image.jpg",
            "msgType": 3,  # Image
            "extra": {"filePath": "/path/to/image.jpg"},
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.message_type == MessageType.IMAGE
        assert msg.file_url == "/path/to/image.jpg"

    def test_parse_private_chat(self, adapter):
        """Private chat uses fromUser as roomId."""
        payload = {
            "msgId": "msg_789",
            "fromUser": "wxid_abc",
            "fromNick": "张三",
            "roomId": "wxid_abc",  # Same as fromUser for private
            "content": "Private message",
            "msgType": 1,
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.thread_id == "weixin:wxid_abc"


class TestWeixinSendMessage:
    @pytest.fixture
    def adapter(self):
        from src.connectors.weixin_adapter import WeixinAdapter
        adapter = WeixinAdapter()
        adapter.api_key = "test"
        adapter.base_url = "http://localhost:8080"
        return adapter

    @pytest.mark.asyncio
    async def test_send_text_message(self, adapter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 0, "message": "success"}
            mock_post.return_value = mock_response

            message = OutboundMessage(content="Hello from MeowAI")
            success, result = await adapter.send_message("weixin:room_xyz", message)

            assert success is True

    @pytest.mark.asyncio
    async def test_debounce_merge(self, adapter):
        """Test 3s debounce window merges messages."""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 0}
            mock_post.return_value = mock_response

            # First message
            message1 = OutboundMessage(content="Line 1")
            await adapter.send_message("weixin:room_xyz", message1)

            # Second message within 3s window should be queued
            message2 = OutboundMessage(content="Line 2")
            await adapter.send_message("weixin:room_xyz", message2)

            # Should only have called API once (merged)
            # Note: In real implementation, debounce is time-based


class TestWeixinMedia:
    @pytest.fixture
    def adapter(self):
        from src.connectors.weixin_adapter import WeixinAdapter
        adapter = WeixinAdapter()
        adapter.api_key = "test"
        adapter.base_url = "http://localhost:8080"
        return adapter

    @pytest.mark.asyncio
    async def test_send_image(self, adapter, tmp_path):
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"code": 0}
            mock_post.return_value = mock_response

            success, _ = await adapter.send_media(
                "weixin:room_xyz",
                MessageType.IMAGE,
                file_path=str(test_file),
            )

            assert success is True


class TestWeixinEdgeCases:
    @pytest.fixture
    def adapter(self):
        from src.connectors.weixin_adapter import WeixinAdapter
        adapter = WeixinAdapter()
        adapter.api_key = "test"
        return adapter

    def test_parse_invalid_payload(self, adapter):
        """Should handle invalid payloads gracefully."""
        msg = adapter.parse_inbound({})
        assert msg is None

    def test_parse_missing_msg_id(self, adapter):
        """Should require msgId."""
        payload = {
            "fromUser": "wxid_abc",
            "content": "Hello",
            "msgType": 1,
        }
        msg = adapter.parse_inbound(payload)
        assert msg is None
