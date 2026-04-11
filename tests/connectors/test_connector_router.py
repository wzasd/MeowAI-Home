"""Tests for ConnectorRouter message processing pipeline (E6)."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path

from src.connectors.base import InboundMessage, MessageType


class TestConnectorRouterBasics:
    @pytest.fixture
    def router(self):
        from src.connectors.router import ConnectorRouter
        return ConnectorRouter()

    def test_router_creation(self, router):
        assert router is not None
        assert len(router._adapters) == 0

    def test_register_adapter(self, router):
        mock_adapter = MagicMock()
        mock_adapter.name = "test"
        router.register_adapter("test", mock_adapter)
        assert "test" in router._adapters

    def test_unregister_adapter(self, router):
        mock_adapter = MagicMock()
        mock_adapter.name = "test"
        router.register_adapter("test", mock_adapter)
        router.unregister_adapter("test")
        assert "test" not in router._adapters


class TestConnectorRouterProcessing:
    @pytest.fixture
    def router(self):
        from src.connectors.router import ConnectorRouter
        router = ConnectorRouter()
        # Mock thread manager
        router._thread_manager = MagicMock()
        return router

    @pytest.mark.asyncio
    async def test_dedup_message(self, router):
        """Test message deduplication."""
        message = InboundMessage(
            message_id="msg_123",
            thread_id="test:chat_456",
            user_id="user_abc",
            user_name="Test User",
            content="Hello",
            message_type=MessageType.TEXT,
        )

        # First process
        result1 = await router.process_inbound("test", message)
        assert result1 is True

        # Second process (duplicate)
        result2 = await router.process_inbound("test", message)
        assert result2 is False  # Deduped

    @pytest.mark.asyncio
    async def test_group_whitelist(self, router):
        """Test group whitelist filtering."""
        router._whitelisted_groups = {"test:allowed_group"}

        message_allowed = InboundMessage(
            message_id="msg_123",
            thread_id="test:allowed_group",
            user_id="user_abc",
            user_name="Test User",
            content="Hello",
            message_type=MessageType.TEXT,
        )

        message_denied = InboundMessage(
            message_id="msg_124",
            thread_id="test:other_group",
            user_id="user_abc",
            user_name="Test User",
            content="Hello",
            message_type=MessageType.TEXT,
        )

        result1 = await router.process_inbound("test", message_allowed)
        assert result1 is True

        result2 = await router.process_inbound("test", message_denied)
        assert result2 is False  # Blocked by whitelist

    @pytest.mark.asyncio
    async def test_command_intercept(self, router):
        """Test command interception."""
        # Register command handler
        mock_handler = AsyncMock(return_value=True)
        router.register_command("/status", mock_handler)

        message = InboundMessage(
            message_id="msg_123",
            thread_id="test:chat_456",
            user_id="user_abc",
            user_name="Test User",
            content="/status",
            message_type=MessageType.TEXT,
        )

        result = await router.process_inbound("test", message)
        assert result is True
        mock_handler.assert_called_once()


class TestConnectorRouterMentionParsing:
    @pytest.fixture
    def router(self):
        from src.connectors.router import ConnectorRouter
        return ConnectorRouter()

    def test_parse_mention_text(self, router):
        content = "@阿橘 请帮我检查代码"
        mentions = router.parse_mentions(content)
        assert "阿橘" in mentions

    def test_parse_multiple_mentions(self, router):
        content = "@阿橘 @墨点 一起看看"
        mentions = router.parse_mentions(content)
        assert "阿橘" in mentions
        assert "墨点" in mentions

    def test_parse_no_mention(self, router):
        content = "请帮我检查代码"
        mentions = router.parse_mentions(content)
        assert len(mentions) == 0


class TestConnectorRouterBindingLookup:
    @pytest.fixture
    def router(self):
        from src.connectors.router import ConnectorRouter
        router = ConnectorRouter()
        router._thread_manager = MagicMock()
        return router

    def test_get_or_create_thread(self, router):
        # Mock thread creation
        router._thread_manager.get_or_create.return_value = {"id": "thread_123"}

        thread_id = router.get_or_create_thread("feishu:chat_456")
        assert thread_id == "thread_123"


class TestConnectorRouterOutbound:
    @pytest.fixture
    def router(self):
        from src.connectors.router import ConnectorRouter
        router = ConnectorRouter()
        return router

    @pytest.mark.asyncio
    async def test_route_outbound(self, router):
        mock_adapter = AsyncMock()
        mock_adapter.send_message = AsyncMock(return_value=(True, "msg_123"))
        router.register_adapter("feishu", mock_adapter)

        from src.connectors.base import OutboundMessage
        message = OutboundMessage(content="Hello")

        success, result = await router.send_outbound("feishu:chat_456", message)
        assert success is True
