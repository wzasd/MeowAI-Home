"""Tests for OutboundDeliveryHook (E7)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from src.connectors.base import OutboundMessage, MessageType


class TestOutboundDeliveryPriority:
    """Test delivery priority: formattedReply > richMessage > reply+media > plainReply"""

    @pytest.fixture
    def delivery(self):
        from src.connectors.outbound_delivery import OutboundDeliveryHook
        return OutboundDeliveryHook()

    @pytest.mark.asyncio
    async def test_formatted_reply_priority(self, delivery):
        """formattedReply should be used when available."""
        mock_adapter = AsyncMock()

        result = {
            "formattedReply": "**Formatted** text",
            "plainReply": "Plain text",
            "richMessage": {"card": "data"},
        }

        await delivery.deliver(mock_adapter, "thread:123", result)

        # Should prefer formattedReply
        call_args = mock_adapter.send_message.call_args
        assert call_args is not None
        message = call_args[0][1]
        assert "Formatted" in message.content

    @pytest.mark.asyncio
    async def test_rich_message_fallback(self, delivery):
        """richMessage should be used when formattedReply not available."""
        mock_adapter = AsyncMock()

        result = {
            "plainReply": "Plain text",
            "richMessage": {"title": "Card Title"},
        }

        await delivery.deliver(mock_adapter, "thread:123", result)

        # Should call send_rich_message
        assert mock_adapter.send_rich_message.called

    @pytest.mark.asyncio
    async def test_reply_with_media(self, delivery):
        """reply + media should be used when richMessage not available."""
        mock_adapter = AsyncMock()
        mock_adapter.send_message = AsyncMock(return_value=(True, None))
        mock_adapter.send_media = AsyncMock(return_value=(True, None))

        result = {
            "plainReply": "See attached file",
            "attachments": [{"path": "/tmp/file.pdf", "type": "file"}],
        }

        await delivery.deliver(mock_adapter, "thread:123", result)

        # Should send text + media
        assert mock_adapter.send_message.called
        assert mock_adapter.send_media.called

    @pytest.mark.asyncio
    async def test_plain_reply_fallback(self, delivery):
        """plainReply should be used when nothing else available."""
        mock_adapter = AsyncMock()

        result = {
            "plainReply": "Simple text response",
        }

        await delivery.deliver(mock_adapter, "thread:123", result)

        call_args = mock_adapter.send_message.call_args
        message = call_args[0][1]
        assert message.content == "Simple text response"


class TestOutboundDeliveryMedia:
    @pytest.fixture
    def delivery(self):
        from src.connectors.outbound_delivery import OutboundDeliveryHook
        return OutboundDeliveryHook()

    @pytest.mark.asyncio
    async def test_media_path_resolution(self, delivery):
        """Test media path is resolved correctly."""
        mock_adapter = AsyncMock()
        mock_adapter.send_message = AsyncMock(return_value=(True, None))
        mock_adapter.send_media = AsyncMock(return_value=(True, None))

        result = {
            "plainReply": "Image attached",
            "attachments": [{"path": "/tmp/test.png", "type": "image"}],
        }

        await delivery.deliver(mock_adapter, "thread:123", result)

        # Check media was sent
        assert mock_adapter.send_media.called
        call_args = mock_adapter.send_media.call_args
        assert call_args[1]["file_path"] == "/tmp/test.png"

    @pytest.mark.asyncio
    async def test_path_traversal_protection(self, delivery):
        """Test path traversal is blocked."""
        mock_adapter = AsyncMock()

        result = {
            "plainReply": "Malicious file",
            "attachments": [{"path": "../../../etc/passwd", "type": "file"}],
        }

        success, error = await delivery.deliver(mock_adapter, "thread:123", result)

        assert success is False
        assert "traversal" in error.lower() or "invalid" in error.lower()


class TestOutboundDeliveryStreaming:
    @pytest.fixture
    def delivery(self):
        from src.connectors.outbound_delivery import OutboundDeliveryHook
        return OutboundDeliveryHook()

    @pytest.mark.asyncio
    async def test_streaming_placeholder(self, delivery):
        """Test streaming with placeholder + updates."""
        mock_adapter = AsyncMock()
        mock_adapter.send_placeholder = AsyncMock(return_value=(True, "placeholder_123"))
        mock_adapter.edit_message = AsyncMock(return_value=(True, None))

        # Simulate streaming chunks
        chunks = ["Hello", "Hello world", "Hello world!"]
        placeholder_id = "placeholder_123"

        for chunk in chunks:
            await delivery.update_stream(mock_adapter, "thread:123", placeholder_id, chunk)

        # Should have called edit_message for each update
        assert mock_adapter.edit_message.call_count == len(chunks)

    @pytest.mark.asyncio
    async def test_streaming_final(self, delivery):
        """Test finalizing stream."""
        mock_adapter = AsyncMock()

        await delivery.finalize_stream(
            mock_adapter,
            "thread:123",
            "placeholder_123",
            {"formattedReply": "Final content"},
        )

        # Should edit with final content or delete placeholder and send new
        assert mock_adapter.edit_message.called or mock_adapter.delete_message.called
