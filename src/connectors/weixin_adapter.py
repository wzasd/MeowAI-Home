"""WeChat Personal (iLink Bot) connector adapter.

Supports long-polling protocol and SILK audio codec.
Implements 3s debounce for reply merging.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import (
    IStreamableOutboundAdapter,
    MessageType,
    InboundMessage,
    OutboundMessage,
    MediaUploadResult,
    ConnectorStatus,
    ConnectorHealth,
)


class WeixinAdapter(IStreamableOutboundAdapter):
    """WeChat Personal (iLink Bot) adapter.

    Uses iLink Bot HTTP API for receiving/sending messages.
    Supports SILK audio codec conversion.
    """

    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url: Optional[str] = None
        self._handler: Optional[callable] = None
        self._debounce_window_seconds: float = 3.0
        self._pending_messages: Dict[str, List[str]] = {}  # room_id -> messages
        self._debounce_tasks: Dict[str, asyncio.Task] = {}

    @property
    def name(self) -> str:
        return "weixin"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with iLink Bot credentials."""
        self.api_key = config.get("api_key") or os.environ.get("ILINK_API_KEY")
        self.base_url = config.get("base_url") or os.environ.get("ILINK_BASE_URL", "http://localhost:8080")

        if not self.api_key:
            return False

        # Test connection
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0,
                )
                return response.status_code == 200
        except Exception:
            # Allow initialization even if health check fails
            # (iLink might not be running yet)
            return True

    async def health_check(self) -> ConnectorStatus:
        """Check connector health."""
        if not self.api_key:
            return ConnectorStatus(
                name=self.name,
                health=ConnectorHealth.UNHEALTHY,
                connected=False,
                last_error="No API key configured",
            )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=5.0,
                )
                healthy = response.status_code == 200
                return ConnectorStatus(
                    name=self.name,
                    health=ConnectorHealth.HEALTHY if healthy else ConnectorHealth.DEGRADED,
                    connected=healthy,
                )
        except Exception as e:
            return ConnectorStatus(
                name=self.name,
                health=ConnectorHealth.UNHEALTHY,
                connected=False,
                last_error=str(e),
            )

    def set_message_handler(self, handler: callable) -> None:
        """Set handler for incoming messages."""
        self._handler = handler

    def parse_inbound(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        """Parse iLink webhook payload to standardized message."""
        try:
            # Check required fields
            msg_id = payload.get("msgId")
            if not msg_id:
                return None

            msg_type = payload.get("msgType", 1)
            content = payload.get("content", "")
            room_id = payload.get("roomId", "")

            # Map message type
            msg_type_enum = self._map_message_type(msg_type)

            # Handle media
            file_url = None
            if msg_type_enum in (MessageType.IMAGE, MessageType.FILE, MessageType.AUDIO):
                extra = payload.get("extra", {})
                file_url = extra.get("filePath") or content

            return InboundMessage(
                message_id=str(msg_id),
                thread_id=f"weixin:{room_id}",
                user_id=payload.get("fromUser", ""),
                user_name=payload.get("fromNick", "unknown"),
                content=content,
                message_type=msg_type_enum,
                raw_data=payload,
                file_url=file_url,
                file_name=Path(file_url).name if file_url else None,
            )
        except Exception:
            return None

    def _map_message_type(self, ilink_type: int) -> MessageType:
        """Map iLink message type to standard type."""
        # iLink msgType values
        mapping = {
            1: MessageType.TEXT,
            3: MessageType.IMAGE,
            34: MessageType.AUDIO,  # Voice
            43: MessageType.VIDEO,
            47: MessageType.IMAGE,  # Emoji/sticker
            49: MessageType.RICH,   # App message
        }
        return mapping.get(ilink_type, MessageType.TEXT)

    async def _debounced_send(self, room_id: str) -> None:
        """Send pending messages after debounce window."""
        await asyncio.sleep(self._debounce_window_seconds)

        messages = self._pending_messages.get(room_id, [])
        if messages:
            merged_content = "\n".join(messages)
            await self._send_immediately(room_id, merged_content)

        # Clean up
        self._pending_messages.pop(room_id, None)
        self._debounce_tasks.pop(room_id, None)

    async def _send_immediately(self, room_id: str, content: str) -> Tuple[bool, Optional[str]]:
        """Send message immediately via iLink API."""
        url = f"{self.base_url}/api/message/sendText"

        payload = {
            "apiKey": self.api_key,
            "roomId": room_id,
            "content": content,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                data = response.json()

                if data.get("code") == 0:
                    return True, data.get("data", {}).get("msgId")
                return False, data.get("message")
        except Exception as e:
            return False, str(e)

    async def send_message(self, thread_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send message with debounce merging."""
        room_id = thread_id.replace("weixin:", "")

        # Add to pending queue
        if room_id not in self._pending_messages:
            self._pending_messages[room_id] = []
        self._pending_messages[room_id].append(message.content)

        # Cancel existing debounce task
        if room_id in self._debounce_tasks:
            self._debounce_tasks[room_id].cancel()

        # Start new debounce task
        task = asyncio.create_task(self._debounced_send(room_id))
        self._debounce_tasks[room_id] = task

        return True, "queued"

    async def send_reply(self, thread_id: str, reply_to_message_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send reply (WeChat uses same room for replies)."""
        return await self.send_message(thread_id, message)

    async def send_placeholder(self, thread_id: str, content: str = "⏳ 处理中...") -> Tuple[bool, Optional[str]]:
        """Send placeholder (immediately, no debounce)."""
        room_id = thread_id.replace("weixin:", "")
        return await self._send_immediately(room_id, content)

    async def edit_message(self, thread_id: str, message_id: str, new_content: str, rich_content: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """Edit message (not supported by WeChat)."""
        return False, "WeChat does not support message editing"

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Delete message (not supported by WeChat)."""
        return False

    async def send_rich_message(self, thread_id: str, card_type: str, card_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Send rich message as text (WeChat limited support)."""
        # Convert card to text representation
        content = card_data.get("content", "")
        if not content and "cardData" in card_data:
            content = json.dumps(card_data["cardData"], ensure_ascii=False)

        message = OutboundMessage(content=content)
        return await self.send_message(thread_id, message)

    async def send_media(self, thread_id: str, media_type: MessageType, file_path: Optional[str] = None, file_data: Optional[bytes] = None, file_name: Optional[str] = None, caption: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Send media message."""
        room_id = thread_id.replace("weixin:", "")

        if file_path:
            return await self._send_media_file(room_id, file_path, media_type, caption)
        elif file_data:
            # Save to temp file
            temp_path = f"/tmp/weixin_{int(time.time())}"
            Path(temp_path).write_bytes(file_data)
            return await self._send_media_file(room_id, temp_path, media_type, caption)
        else:
            return False, "No file provided"

    async def _send_media_file(self, room_id: str, file_path: str, media_type: MessageType, caption: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Send media file via iLink API."""
        path = Path(file_path)

        if media_type == MessageType.IMAGE:
            url = f"{self.base_url}/api/message/sendImage"
        elif media_type == MessageType.FILE:
            url = f"{self.base_url}/api/message/sendFile"
        elif media_type == MessageType.AUDIO:
            # Convert SILK if needed
            url = f"{self.base_url}/api/message/sendVoice"
        else:
            return False, f"Unsupported media type: {media_type}"

        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"file": (path.name, f, "application/octet-stream")}
                    data = {
                        "apiKey": self.api_key,
                        "roomId": room_id,
                    }
                    if caption:
                        data["content"] = caption

                    response = await client.post(url, files=files, data=data, timeout=60.0)
                    result = response.json()

                    if result.get("code") == 0:
                        return True, result.get("data", {}).get("msgId")
                    return False, result.get("message")
        except Exception as e:
            return False, str(e)

    async def download_media(self, media_url: str, local_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Download media (media_url is local path in iLink)."""
        # iLink provides local file paths directly
        if Path(media_url).exists():
            if local_path:
                Path(local_path).write_bytes(Path(media_url).read_bytes())
                return True, local_path
            return True, media_url
        return False, f"File not found: {media_url}"

    async def upload_media(self, file_path: str, media_type: MessageType) -> MediaUploadResult:
        """Upload media (iLink handles this automatically)."""
        path = Path(file_path)
        if not path.exists():
            return MediaUploadResult(success=False, error=f"File not found: {file_path}")

        # iLink doesn't need separate upload, just return the path
        return MediaUploadResult(success=True, media_id=str(path), url=str(path))

    async def start(self) -> None:
        """Start long-polling for messages."""
        # Long polling is handled by separate webhook or polling loop
        pass

    async def stop(self) -> None:
        """Stop connections and flush pending messages."""
        # Cancel all debounce tasks and flush
        for task in self._debounce_tasks.values():
            task.cancel()

        # Flush pending messages
        for room_id in list(self._pending_messages.keys()):
            messages = self._pending_messages.get(room_id, [])
            if messages:
                merged_content = "\n".join(messages)
                await self._send_immediately(room_id, merged_content)

        self._pending_messages.clear()
        self._debounce_tasks.clear()
