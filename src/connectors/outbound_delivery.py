"""OutboundDeliveryHook — outbound message delivery with priority routing.

Delivery priority:
1. formattedReply (Markdown/rich text)
2. richMessage (Structured cards)
3. reply + media (Text with attachments)
4. plainReply (Simple text)

Includes path traversal protection for media.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base import OutboundMessage, MessageType, MediaUploadResult


class PathTraversalError(Exception):
    """Raised when path traversal is detected."""
    pass


class OutboundDeliveryHook:
    """Handles outbound message delivery with format selection."""

    def __init__(self):
        self._allowed_base_paths: List[str] = ["/tmp", "/var/tmp", os.getcwd()]

    def add_allowed_path(self, path: str) -> None:
        """Add allowed base path for media resolution."""
        self._allowed_base_paths.append(os.path.abspath(path))

    def _validate_media_path(self, file_path: str) -> bool:
        """Validate media path for traversal attacks.

        Returns True if path is safe, False otherwise.
        """
        try:
            # Check for common traversal patterns
            if ".." in file_path:
                return False

            # Normalize the path
            abs_path = os.path.abspath(file_path)

            # Check if path is within allowed directories
            for allowed in self._allowed_base_paths:
                try:
                    # Check if file is under allowed path
                    Path(abs_path).relative_to(os.path.abspath(allowed))
                    return True
                except ValueError:
                    continue

            # Also allow if file exists in current working directory subtree
            try:
                Path(abs_path).relative_to(os.getcwd())
                return True
            except ValueError:
                pass

            # Allow common temp directories
            if abs_path.startswith(("/tmp", "/var/tmp", "/private/tmp")):
                return True

            return False
        except Exception:
            return False

    async def deliver(
        self,
        adapter: Any,
        thread_id: str,
        result: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Deliver message according to priority.

        Args:
            adapter: Connector adapter
            thread_id: Target thread ID
            result: Cat response with possible fields:
                - formattedReply: Markdown/rich text
                - richMessage: Structured card data
                - plainReply: Simple text
                - attachments: List of {path, type, name}

        Returns:
            (success, error_message)
        """
        try:
            # Priority 1: formattedReply
            if result.get("formattedReply"):
                return await self._send_formatted(adapter, thread_id, result["formattedReply"])

            # Priority 2: richMessage
            if result.get("richMessage"):
                return await self._send_rich(adapter, thread_id, result["richMessage"])

            # Priority 3: reply + media
            if result.get("attachments"):
                return await self._send_with_media(adapter, thread_id, result)

            # Priority 4: plainReply
            if result.get("plainReply"):
                return await self._send_plain(adapter, thread_id, result["plainReply"])

            # Nothing to send
            return False, "No content to deliver"

        except PathTraversalError as e:
            return False, f"Security violation: {e}"
        except Exception as e:
            return False, str(e)

    async def _send_formatted(
        self,
        adapter: Any,
        thread_id: str,
        content: str,
    ) -> Tuple[bool, Optional[str]]:
        """Send formatted reply (Markdown)."""
        message = OutboundMessage(
            content=content,
            message_type=MessageType.TEXT,
        )
        return await adapter.send_message(thread_id, message)

    async def _send_rich(
        self,
        adapter: Any,
        thread_id: str,
        rich_data: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Send rich/card message."""
        card_type = rich_data.get("type", "template")
        card_data = rich_data.get("data", rich_data)

        return await adapter.send_rich_message(thread_id, card_type, card_data)

    async def _send_plain(
        self,
        adapter: Any,
        thread_id: str,
        content: str,
    ) -> Tuple[bool, Optional[str]]:
        """Send plain text reply."""
        message = OutboundMessage(
            content=content,
            message_type=MessageType.TEXT,
        )
        return await adapter.send_message(thread_id, message)

    async def _send_with_media(
        self,
        adapter: Any,
        thread_id: str,
        result: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Send text with media attachments."""
        attachments = result.get("attachments", [])
        text = result.get("plainReply", "")

        # Validate all paths first
        for attachment in attachments:
            path = attachment.get("path", "")
            if not self._validate_media_path(path):
                raise PathTraversalError(f"Invalid path: {path}")

        # Send text first if present
        if text:
            message = OutboundMessage(content=text)
            success, error = await adapter.send_message(thread_id, message)
            if not success:
                return False, error

        # Send each attachment
        for attachment in attachments:
            path = attachment.get("path", "")
            media_type_str = attachment.get("type", "file")
            media_type = self._parse_media_type(media_type_str)

            success, error = await adapter.send_media(
                thread_id,
                media_type,
                file_path=path,
                file_name=attachment.get("name"),
            )
            if not success:
                return False, error

        return True, None

    def _parse_media_type(self, type_str: str) -> MessageType:
        """Parse media type string to MessageType."""
        mapping = {
            "image": MessageType.IMAGE,
            "img": MessageType.IMAGE,
            "picture": MessageType.IMAGE,
            "file": MessageType.FILE,
            "audio": MessageType.AUDIO,
            "voice": MessageType.AUDIO,
            "video": MessageType.VIDEO,
        }
        return mapping.get(type_str.lower(), MessageType.FILE)

    async def start_stream(
        self,
        adapter: Any,
        thread_id: str,
        initial_text: str = "⏳ 处理中...",
    ) -> Tuple[bool, Optional[str]]:
        """Start streaming response with placeholder.

        Returns:
            (success, placeholder_id)
        """
        if hasattr(adapter, "send_placeholder"):
            return await adapter.send_placeholder(thread_id, initial_text)
        else:
            # Fallback to regular message
            message = OutboundMessage(content=initial_text)
            return await adapter.send_message(thread_id, message)

    async def update_stream(
        self,
        adapter: Any,
        thread_id: str,
        placeholder_id: str,
        new_content: str,
    ) -> Tuple[bool, Optional[str]]:
        """Update streaming placeholder."""
        if hasattr(adapter, "edit_message"):
            return await adapter.edit_message(thread_id, placeholder_id, new_content)
        else:
            # Adapter doesn't support editing, can't stream
            return False, "Adapter does not support streaming"

    async def finalize_stream(
        self,
        adapter: Any,
        thread_id: str,
        placeholder_id: str,
        result: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Finalize streaming response with final content."""
        # Try to edit with final content
        if result.get("formattedReply"):
            if hasattr(adapter, "edit_message"):
                return await adapter.edit_message(
                    thread_id,
                    placeholder_id,
                    result["formattedReply"],
                )

        # If edit fails or not supported, delete placeholder and send new
        if hasattr(adapter, "delete_message"):
            await adapter.delete_message(thread_id, placeholder_id)

        return await self.deliver(adapter, thread_id, result)
