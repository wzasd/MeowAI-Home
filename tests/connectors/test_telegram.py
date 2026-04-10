"""TelegramConnector tests"""
import pytest

from src.connectors.telegram import TelegramConnector
from src.connectors.base import PlatformMessage, PlatformResponse


@pytest.fixture
def connector():
    return TelegramConnector(bot_token="123456:ABC-DEF")


class TestTelegramParseMessage:
    def test_parse_valid_text_message(self, connector):
        payload = {
            "message": {
                "text": "Hello MeowAI",
                "chat": {"id": 987654},
                "from": {"id": 111222, "first_name": "WangZhao"},
            }
        }
        msg = connector.parse_message(payload)
        assert isinstance(msg, PlatformMessage)
        assert msg.platform == "telegram"
        assert msg.chat_id == "987654"
        assert msg.user_id == "111222"
        assert msg.user_name == "WangZhao"
        assert msg.content == "Hello MeowAI"
        assert msg.raw == payload

    def test_parse_non_text_message_returns_none(self, connector):
        payload = {
            "message": {
                "photo": [{"file_id": "abc"}],
                "chat": {"id": 987654},
                "from": {"id": 111222, "first_name": "WangZhao"},
            }
        }
        assert connector.parse_message(payload) is None

    def test_parse_missing_message_returns_none(self, connector):
        assert connector.parse_message({}) is None


class TestTelegramValidateRequest:
    @pytest.mark.asyncio
    async def test_validate_always_true(self, connector):
        assert await connector.validate_request({}, b"") is True


class TestTelegramThreadMapping:
    def test_map_chat_to_thread(self, connector):
        assert connector.map_chat_to_thread("123456") == "telegram:123456"

    def test_map_thread_to_chat_reverse(self, connector):
        thread_id = connector.map_chat_to_thread("123456")
        assert connector.map_thread_to_chat(thread_id) == "123456"
