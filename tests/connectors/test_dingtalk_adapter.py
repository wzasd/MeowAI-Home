"""Tests for DingTalk connector adapter (E3)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.connectors.base import (
    MessageType,
    InboundMessage,
    OutboundMessage,
    MediaUploadResult,
)


class TestDingTalkAdapterBasics:
    @pytest.fixture
    def adapter(self):
        from src.connectors.dingtalk_adapter import DingTalkAdapter
        return DingTalkAdapter()

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        with patch.dict("os.environ", {"DINGTALK_APP_KEY": "test_key", "DINGTALK_APP_SECRET": "test_secret"}):
            with patch.object(adapter, "_get_access_token", new_callable=AsyncMock, return_value="token_xxx"):
                success = await adapter.initialize({})
                assert success is True
                assert adapter.app_key == "test_key"

    @pytest.mark.asyncio
    async def test_initialize_missing_config(self, adapter):
        with patch.dict("os.environ", {}, clear=True):
            success = await adapter.initialize({})
            assert success is False


class TestDingTalkMessageParsing:
    @pytest.fixture
    def adapter(self):
        from src.connectors.dingtalk_adapter import DingTalkAdapter
        adapter = DingTalkAdapter()
        adapter.app_key = "test"
        return adapter

    def test_parse_text_message(self, adapter):
        payload = {
            "msgtype": "text",
            "text": {"content": "Hello @机器人"},
            "conversationId": "cid_abc123",
            "senderStaffId": "user_456",
            "senderNick": "张三",
            "msgId": "msg_789",
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.content == "Hello @机器人"
        assert msg.thread_id == "dingtalk:cid_abc123"
        assert msg.user_id == "user_456"
        assert msg.user_name == "张三"
        assert msg.message_type == MessageType.TEXT

    def test_parse_image_message(self, adapter):
        payload = {
            "msgtype": "picture",
            "content": {"downloadCode": "code_xxx", "pictureDownloadCode": "code_xxx"},
            "conversationId": "cid_abc",
            "senderStaffId": "user_456",
            "senderNick": "张三",
            "msgId": "msg_789",
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.message_type == MessageType.IMAGE
        assert msg.file_url == "code_xxx"


class TestDingTalkSendMessage:
    @pytest.fixture
    def adapter(self):
        from src.connectors.dingtalk_adapter import DingTalkAdapter
        adapter = DingTalkAdapter()
        adapter.app_key = "test"
        adapter.app_secret = "secret"
        adapter.access_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_send_text_message(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"success": True, "result": {"openConversationId": "cid_123"}}, True

        adapter._api_call = mock_api_call

        message = OutboundMessage(content="Hello from MeowAI")
        success, result = await adapter.send_message("dingtalk:cid_abc", message)

        assert success is True

    @pytest.mark.asyncio
    async def test_send_rich_message(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"success": True, "result": {}}, True

        adapter._api_call = mock_api_call

        card_data = {
            "cardData": {"title": "Test Card", "content": "Card content"},
        }
        success, _ = await adapter.send_rich_message("dingtalk:cid_abc", "template", card_data)

        assert success is True


class TestDingTalkStreaming:
    @pytest.fixture
    def adapter(self):
        from src.connectors.dingtalk_adapter import DingTalkAdapter
        adapter = DingTalkAdapter()
        adapter.app_key = "test"
        adapter.app_secret = "secret"
        adapter.access_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_send_placeholder(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"success": True, "result": {"processQueryKey": "key_123"}}, True

        adapter._api_call = mock_api_call

        success, key = await adapter.send_placeholder("dingtalk:cid_abc", "⏳ 处理中...")

        assert success is True
        assert key == "key_123"

    @pytest.mark.asyncio
    async def test_edit_message(self, adapter):
        async def mock_api_call(method, url, **kwargs):
            return {"success": True}, True

        adapter._api_call = mock_api_call

        success, _ = await adapter.edit_message(
            "dingtalk:cid_abc",
            "key_123",
            "Updated content",
        )

        assert success is True


class TestDingTalkMedia:
    @pytest.fixture
    def adapter(self):
        from src.connectors.dingtalk_adapter import DingTalkAdapter
        adapter = DingTalkAdapter()
        adapter.app_key = "test"
        adapter.app_secret = "secret"
        adapter.access_token = "token_xxx"
        return adapter

    @pytest.mark.asyncio
    async def test_upload_media(self, adapter, tmp_path):
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image data")

        # Ensure token won't expire
        adapter.token_expires_at = float('inf')

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "result": {"mediaId": "@media_abc123"},
            }
            mock_post.return_value = mock_response

            result = await adapter.upload_media(str(test_file), MessageType.IMAGE)

            assert result.success is True
            assert result.media_id == "@media_abc123"
