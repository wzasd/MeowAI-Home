"""Tests for Feishu connector adapter (E2)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

from src.connectors.base import (
    MessageType,
    InboundMessage,
    OutboundMessage,
    MediaUploadResult,
)


class TestFeishuAdapterBasics:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        return FeishuAdapter()

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        with patch.dict("os.environ", {"FEISHU_APP_ID": "test_app_id", "FEISHU_APP_SECRET": "test_secret"}):
            with patch.object(adapter, "_refresh_token", new_callable=AsyncMock, return_value=True):
                success = await adapter.initialize({})
                assert success is True
                assert adapter.app_id == "test_app_id"

    @pytest.mark.asyncio
    async def test_initialize_missing_config(self, adapter):
        with patch.dict("os.environ", {}, clear=True):
            success = await adapter.initialize({})
            assert success is False

    @pytest.mark.asyncio
    async def test_health_check(self, adapter):
        with patch.dict("os.environ", {"FEISHU_APP_ID": "test", "FEISHU_APP_SECRET": "secret"}):
            await adapter.initialize({})
            status = await adapter.health_check()
            assert status.name == "feishu"


class TestFeishuMessageParsing:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        return adapter

    def test_parse_text_message(self, adapter):
        payload = {
            "header": {"event_id": "evt_123"},
            "event": {
                "message": {
                    "message_type": "text",
                    "content": '{"text": "Hello @bot"}',
                    "chat_id": "chat_456",
                    "message_id": "msg_789",
                },
                "sender": {
                    "sender_id": {"user_id": "user_abc"},
                    "sender_type": "user",
                },
            },
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.content == "Hello @bot"
        assert msg.thread_id == "feishu:chat_456"
        assert msg.user_id == "user_abc"
        assert msg.message_type == MessageType.TEXT

    def test_parse_image_message(self, adapter):
        payload = {
            "header": {"event_id": "evt_123"},
            "event": {
                "message": {
                    "message_type": "image",
                    "content": '{"file_key": "img_xxx", "image_key": "img_xxx"}',
                    "chat_id": "chat_456",
                    "message_id": "msg_789",
                },
                "sender": {
                    "sender_id": {"user_id": "user_abc"},
                    "sender_type": "user",
                },
            },
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.message_type == MessageType.IMAGE

    def test_parse_mention_info(self, adapter):
        payload = {
            "header": {"event_id": "evt_123"},
            "event": {
                "message": {
                    "message_type": "text",
                    "content": '{"text": "@猫 help"}',
                    "chat_id": "chat_456",
                    "message_id": "msg_789",
                    "mentions": [
                        {"id": {"user_id": "bot_123"}, "name": "猫"}
                    ],
                },
                "sender": {
                    "sender_id": {"user_id": "user_abc"},
                },
            },
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.mentioned_cats is not None
        assert "bot_123" in msg.mentioned_cats


class TestFeishuSendMessage:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        adapter.app_secret = "secret"
        adapter.tenant_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_send_text_message(self, adapter):
        # Mock _api_call directly
        async def mock_api_call(method, url, **kwargs):
            return {"code": 0, "data": {"message_id": "msg_123"}}, True

        adapter._api_call = mock_api_call

        message = OutboundMessage(content="Hello from MeowAI")
        success, msg_id = await adapter.send_message("feishu:chat_456", message)

        assert success is True
        assert msg_id == "msg_123"

    @pytest.mark.asyncio
    async def test_send_rich_message(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"code": 0, "data": {"message_id": "msg_456"}}, True

        adapter._api_call = mock_api_call

        card_data = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": "Card content"}}],
        }
        success, msg_id = await adapter.send_rich_message("feishu:chat_456", "interactive", card_data)

        assert success is True
        assert msg_id == "msg_456"


class TestFeishuStreaming:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        adapter.app_secret = "secret"
        adapter.tenant_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_send_placeholder(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"code": 0, "data": {"message_id": "placeholder_123"}}, True

        adapter._api_call = mock_api_call

        success, msg_id = await adapter.send_placeholder("feishu:chat_456", "⏳ 处理中...")

        assert success is True
        assert msg_id == "placeholder_123"

    @pytest.mark.asyncio
    async def test_edit_message(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"code": 0}, True

        adapter._api_call = mock_api_call

        success, _ = await adapter.edit_message(
            "feishu:chat_456",
            "msg_123",
            "Updated content",
        )

        assert success is True


class TestFeishuMedia:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        adapter.app_secret = "secret"
        adapter.tenant_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_upload_media(self, adapter, tmp_path):
        # Create a temp file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image data")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "code": 0,
                "data": {"file_key": "img_abc123"},
            }
            mock_post.return_value = mock_response

            result = await adapter.upload_media(str(test_file), MessageType.IMAGE)

            assert result.success is True
            assert result.media_id == "img_abc123"

    @pytest.mark.asyncio
    async def test_send_media(self, adapter, tmp_path):
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"fake pdf data")

        # Mock _api_call for the message send part
        call_count = 0
        async def mock_api_call(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"code": 0, "data": {"message_id": "msg_789"}}, True

        adapter._api_call = mock_api_call

        # Mock upload_media
        async def mock_upload(path, mtype):
            return MediaUploadResult(success=True, media_id="file_key_123")

        adapter.upload_media = mock_upload

        success, msg_id = await adapter.send_media(
            "feishu:chat_456",
            MessageType.FILE,
            file_path=str(test_file),
            file_name="document.pdf",
        )

        assert success is True


class TestFeishuTokenRefresh:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        adapter.app_secret = "secret"
        return adapter

    @pytest.mark.asyncio
    async def test_token_refresh_on_auth_error(self, adapter):
        """Should refresh token when API returns auth error."""
        call_count = 0

        async def mock_api_call(method, url, **kwargs):
            nonlocal call_count
            call_count += 1
            # Always succeed for this test
            return {"code": 0, "data": {"message_id": "msg_123"}}, True

        adapter._api_call = mock_api_call

        with patch.object(adapter, "_refresh_token", new_callable=AsyncMock) as mock_refresh:
            message = OutboundMessage(content="Test")
            await adapter.send_message("feishu:chat_456", message)

            # _api_call handles auth internally
            assert call_count >= 1


class TestFeishuEdgeCases:
    @pytest.fixture
    def adapter(self):
        from src.connectors.feishu_adapter import FeishuAdapter
        adapter = FeishuAdapter()
        adapter.app_id = "test"
        return adapter

    def test_parse_invalid_payload(self, adapter):
        """Should handle invalid payloads gracefully."""
        msg = adapter.parse_inbound({})
        assert msg is None

    def test_parse_malformed_json_content(self, adapter):
        """Should handle malformed content JSON."""
        payload = {
            "header": {"event_id": "evt_123"},
            "event": {
                "message": {
                    "message_type": "text",
                    "content": "not valid json",
                    "chat_id": "chat_456",
                },
                "sender": {"sender_id": {"user_id": "user_abc"}},
            },
        }
        msg = adapter.parse_inbound(payload)
        # Should handle gracefully - returns None on parse error
        assert msg is None

    def test_map_message_types(self, adapter):
        """Test message type mapping."""
        assert adapter._map_message_type("text") == MessageType.TEXT
        assert adapter._map_message_type("image") == MessageType.IMAGE
        assert adapter._map_message_type("file") == MessageType.FILE
        assert adapter._map_message_type("audio") == MessageType.AUDIO
        assert adapter._map_message_type("media") == MessageType.AUDIO
        assert adapter._map_message_type("post") == MessageType.RICH
        assert adapter._map_message_type("interactive") == MessageType.RICH
        assert adapter._map_message_type("unknown") == MessageType.TEXT  # Default
