"""WeComConnector tests"""
import hashlib
import pytest

from src.connectors.wecom import WeComConnector
from src.connectors.base import PlatformMessage, PlatformResponse


@pytest.fixture
def connector():
    return WeComConnector(
        corp_id="corp123",
        agent_id="1000002",
        secret="mysecret",
        token="mytoken",
        encoding_aes_key="abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG",
    )


class TestWeComParseMessage:
    def test_parse_valid_text_message(self, connector):
        payload = {
            "Content": "Hello MeowAI",
            "FromUserName": "user_wangzhao",
            "ChatId": "chat_001",
        }
        msg = connector.parse_message(payload)
        assert isinstance(msg, PlatformMessage)
        assert msg.platform == "wecom"
        assert msg.chat_id == "chat_001"
        assert msg.user_id == "user_wangzhao"
        assert msg.content == "Hello MeowAI"
        assert msg.raw == payload

    def test_parse_invalid_payload_returns_none(self, connector):
        assert connector.parse_message({}) is None
        assert connector.parse_message({"FromUserName": "u1"}) is None


class TestWeComValidateRequest:
    def _make_signature(self, token, timestamp, nonce):
        """Reproduce the SHA1 sort-based signature."""
        items = sorted([token, timestamp, nonce])
        raw = "".join(items)
        return hashlib.sha1(raw.encode()).hexdigest()

    @pytest.mark.asyncio
    async def test_validate_correct_signature(self, connector):
        ts = "1609459200"
        nonce = "abc123"
        sig = self._make_signature("mytoken", ts, nonce)
        headers = {"timestamp": ts, "nonce": nonce, "msg_signature": sig}
        assert await connector.validate_request(headers, b"") is True

    @pytest.mark.asyncio
    async def test_validate_wrong_signature(self, connector):
        headers = {
            "timestamp": "1609459200",
            "nonce": "abc123",
            "msg_signature": "badsignature",
        }
        assert await connector.validate_request(headers, b"") is False


class TestWeComThreadMapping:
    def test_map_chat_to_thread(self, connector):
        assert connector.map_chat_to_thread("chat_001") == "wecom:chat_001"

    def test_map_thread_to_chat_reverse(self, connector):
        thread_id = connector.map_chat_to_thread("group_999")
        assert connector.map_thread_to_chat(thread_id) == "group_999"


class TestWeComSendResponse:
    @pytest.mark.asyncio
    async def test_send_response_success(self, connector, monkeypatch):
        import src.connectors.wecom as mod

        async def fake_post(self, url, json):
            class Resp:
                status_code = 200

                def json(self):
                    return {"errcode": 0}

            return Resp()

        monkeypatch.setattr(mod.httpx.AsyncClient, "post", fake_post)
        # Also patch _get_access_token to return a dummy token
        connector._access_token = "fake_token"
        result = await connector.send_response(
            "chat_001", PlatformResponse(text="Meow!")
        )
        assert result is True
