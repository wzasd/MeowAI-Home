"""BaseConnector abstract class tests"""
import pytest
from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class TestPlatformMessage:
    def test_creation_with_all_fields(self):
        msg = PlatformMessage(
            platform="feishu",
            chat_id="oc_abc123",
            user_id="ou_xyz",
            user_name="Alice",
            content="Hello",
            raw={"event": {"type": "message"}},
        )
        assert msg.platform == "feishu"
        assert msg.chat_id == "oc_abc123"
        assert msg.user_id == "ou_xyz"
        assert msg.user_name == "Alice"
        assert msg.content == "Hello"
        assert msg.raw == {"event": {"type": "message"}}

    def test_default_raw_is_empty_dict(self):
        msg = PlatformMessage(
            platform="test", chat_id="c1", user_id="u1",
            user_name="Bob", content="Hi",
        )
        assert msg.raw == {}


class TestPlatformResponse:
    def test_text_only(self):
        resp = PlatformResponse(text="Hello!")
        assert resp.text == "Hello!"
        assert resp.markdown is None

    def test_with_markdown(self):
        resp = PlatformResponse(text="plain", markdown="**bold**")
        assert resp.markdown == "**bold**"


class TestBaseConnectorAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseConnector()

    def test_concrete_subclass_works(self):
        class DummyConnector(BaseConnector):
            platform = "dummy"

            async def validate_request(self, headers, body):
                return True

            def parse_message(self, payload):
                return PlatformMessage(
                    platform="dummy", chat_id="c1", user_id="u1",
                    user_name="Test", content=payload.get("text", ""),
                )

            async def send_response(self, chat_id, response):
                return True

        conn = DummyConnector()
        assert conn.platform == "dummy"
        assert conn.map_chat_to_thread("abc") == "dummy:abc"
        assert conn.map_thread_to_chat("dummy:abc") == "abc"

    def test_map_chat_to_thread_format(self):
        class MinimalConnector(BaseConnector):
            platform = "test"

            async def validate_request(self, headers, body):
                return True

            def parse_message(self, payload):
                return None

            async def send_response(self, chat_id, response):
                return True

        conn = MinimalConnector()
        assert conn.map_chat_to_thread("xyz") == "test:xyz"

    def test_map_thread_to_chat_reverse(self):
        class MinimalConnector(BaseConnector):
            platform = "wecom"

            async def validate_request(self, headers, body):
                return True

            def parse_message(self, payload):
                return None

            async def send_response(self, chat_id, response):
                return True

        conn = MinimalConnector()
        thread_id = conn.map_chat_to_thread("group_123")
        assert conn.map_thread_to_chat(thread_id) == "group_123"
