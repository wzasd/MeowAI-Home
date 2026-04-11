"""Tests for WeCom Bot connector adapter (E5)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.connectors.base import MessageType, InboundMessage, OutboundMessage, MediaUploadResult


class TestWeComBotAdapterBasics:
    @pytest.fixture
    def adapter(self):
        from src.connectors.wecom_bot_adapter import WeComBotAdapter
        return WeComBotAdapter()

    @pytest.mark.asyncio
    async def test_initialize_success(self, adapter):
        with patch.dict("os.environ", {"WECOM_BOT_KEY": "test_key", "WECOM_BOT_WEBHOOK": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"}):
            success = await adapter.initialize({})
            assert success is True
            assert adapter.bot_key == "test_key"

    @pytest.mark.asyncio
    async def test_initialize_missing_config(self, adapter):
        with patch.dict("os.environ", {}, clear=True):
            success = await adapter.initialize({})
            assert success is False


class TestWeComBotMessageParsing:
    @pytest.fixture
    def adapter(self):
        from src.connectors.wecom_bot_adapter import WeComBotAdapter
        adapter = WeComBotAdapter()
        adapter.bot_key = "test"
        return adapter

    def test_parse_text_message(self, adapter):
        payload = {
            "id": "msg_123",
            "chatid": "chat_abc",
            "sender": "user_xyz",
            "sender_name": "张三",
            "msgtype": "text",
            "text": {"content": "Hello bot"},
        }

        msg = adapter.parse_inbound(payload)
        assert msg is not None
        assert msg.content == "Hello bot"
        assert msg.thread_id == "wecom_bot:chat_abc"
        assert msg.user_id == "user_xyz"
        assert msg.user_name == "张三"
        assert msg.message_type == MessageType.TEXT


class TestWeComBotSendMessage:
    @pytest.fixture
    def adapter(self):
        from src.connectors.wecom_bot_adapter import WeComBotAdapter
        adapter = WeComBotAdapter()
        adapter.bot_key = "test"
        adapter.webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        return adapter

    @pytest.mark.asyncio
    async def test_send_text_message(self, adapter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            message = OutboundMessage(content="Hello from MeowAI")
            success, result = await adapter.send_message("wecom_bot:chat_abc", message)

            assert success is True

    @pytest.mark.asyncio
    async def test_send_template_card(self, adapter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            card_data = {
                "card_type": "text_notice",
                "source": {"desc": "企业微信"},
                "main_title": {"title": "通知", "desc": "内容"},
            }
            success, _ = await adapter.send_rich_message("wecom_bot:chat_abc", "template", card_data)

            assert success is True


class TestWeComBotStreaming:
    @pytest.fixture
    def adapter(self):
        from src.connectors.wecom_bot_adapter import WeComBotAdapter
        adapter = WeComBotAdapter()
        adapter.bot_key = "test"
        adapter.webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        return adapter

    @pytest.mark.asyncio
    async def test_send_placeholder(self, adapter):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
            mock_post.return_value = mock_response

            success, _ = await adapter.send_placeholder("wecom_bot:chat_abc", "⏳ 处理中...")

            assert success is True

    @pytest.mark.asyncio
    async def test_edit_not_supported(self, adapter):
        """WeCom bot does not support editing messages."""
        success, error = await adapter.edit_message("wecom_bot:chat_abc", "msg_123", "Updated")
        assert success is False
        assert "not support" in error.lower()


class TestWeComBotMedia:
    @pytest.fixture
    def adapter(self):
        from src.connectors.wecom_bot_adapter import WeComBotAdapter
        adapter = WeComBotAdapter()
        adapter.bot_key = "test"
        adapter.webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send"
        return adapter

    @pytest.mark.asyncio
    async def test_upload_media(self, adapter, tmp_path):
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image data")

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "errcode": 0,
                "media_id": "media_abc123",
            }
            mock_post.return_value = mock_response

            result = await adapter.upload_media(str(test_file), MessageType.IMAGE)

            assert result.success is True
            assert result.media_id == "media_abc123"
