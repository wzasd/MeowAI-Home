"""WeCom (WeChat Work) Bot connector adapter.

Supports Webhook API and Template Cards.
"""
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


class WeComBotAdapter(IStreamableOutboundAdapter):
    """WeCom Bot adapter using webhook API.

    Supports text, markdown, image, file, news, and template cards.
    """

    UPLOAD_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media"

    def __init__(self):
        self.bot_key: Optional[str] = None
        self.webhook_url: Optional[str] = None
        self._handler: Optional[callable] = None

    @property
    def name(self) -> str:
        return "wecom_bot"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with bot credentials."""
        self.bot_key = config.get("bot_key") or os.environ.get("WECOM_BOT_KEY")
        self.webhook_url = config.get("webhook_url") or os.environ.get("WECOM_BOT_WEBHOOK")

        if not self.bot_key:
            return False

        if not self.webhook_url:
            # Default webhook URL
            self.webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self.bot_key}"

        return True

    async def health_check(self) -> ConnectorStatus:
        """Check connector health."""
        if not self.bot_key:
            return ConnectorStatus(
                name=self.name,
                health=ConnectorHealth.UNHEALTHY,
                connected=False,
                last_error="No bot key configured",
            )

        # Try a simple request
        try:
            async with httpx.AsyncClient() as client:
                # Send a test message (will fail but we can check connection)
                response = await client.post(
                    self.webhook_url,
                    json={"msgtype": "text", "text": {"content": ""}},
                    timeout=10.0,
                )
                # Empty content returns error, but connection works
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
        """Parse WeCom webhook payload to standardized message."""
        try:
            # Check required fields
            msg_id = payload.get("id")
            if not msg_id:
                return None

            chat_id = payload.get("chatid", "")
            msg_type = payload.get("msgtype", "text")

            # Extract content based on type
            if msg_type == "text":
                content = payload.get("text", {}).get("content", "")
            elif msg_type == "markdown":
                content = payload.get("markdown", {}).get("content", "")
            else:
                content = ""

            return InboundMessage(
                message_id=str(msg_id),
                thread_id=f"wecom_bot:{chat_id}",
                user_id=payload.get("sender", ""),
                user_name=payload.get("sender_name", "unknown"),
                content=content,
                message_type=MessageType.TEXT if msg_type in ("text", "markdown") else MessageType.RICH,
                raw_data=payload,
            )
        except Exception:
            return None

    async def _send_webhook(self, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Send webhook request."""
        if not self.webhook_url:
            return False, "Webhook URL not configured"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    timeout=30.0,
                )
                data = response.json()

                if data.get("errcode") == 0:
                    return True, None
                return False, data.get("errmsg", "Unknown error")
        except Exception as e:
            return False, str(e)

    async def send_message(self, thread_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send message via webhook."""
        payload = {
            "msgtype": "text",
            "text": {"content": message.content},
        }

        return await self._send_webhook(payload)

    async def send_reply(self, thread_id: str, reply_to_message_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send reply (WeCom bot uses same webhook)."""
        return await self.send_message(thread_id, message)

    async def send_placeholder(self, thread_id: str, content: str = "⏳ 处理中...") -> Tuple[bool, Optional[str]]:
        """Send placeholder text."""
        message = OutboundMessage(content=content)
        return await self.send_message(thread_id, message)

    async def edit_message(self, thread_id: str, message_id: str, new_content: str, rich_content: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """Edit message (not supported by WeCom bot)."""
        return False, "WeCom bot does not support editing messages"

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Delete message (not supported by WeCom bot)."""
        return False

    async def send_rich_message(self, thread_id: str, card_type: str, card_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Send template card."""
        if card_type == "template":
            payload = {
                "msgtype": "template_card",
                "template_card": card_data,
            }
        elif card_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": card_data.get("content", "")},
            }
        elif card_type == "news":
            payload = {
                "msgtype": "news",
                "news": card_data,
            }
        else:
            # Fallback to text
            payload = {
                "msgtype": "text",
                "text": {"content": json.dumps(card_data, ensure_ascii=False)},
            }

        return await self._send_webhook(payload)

    async def send_media(self, thread_id: str, media_type: MessageType, file_path: Optional[str] = None, file_data: Optional[bytes] = None, file_name: Optional[str] = None, caption: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Send media message."""
        if file_path:
            result = await self.upload_media(file_path, media_type)
            if not result.success:
                return False, result.error
            media_id = result.media_id
        elif file_data:
            # Save to temp and upload
            temp_path = f"/tmp/wecom_{int(time.time())}"
            Path(temp_path).write_bytes(file_data)
            result = await self.upload_media(temp_path, media_type)
            if not result.success:
                return False, result.error
            media_id = result.media_id
        else:
            return False, "No file provided"

        # Send using media_id
        if media_type == MessageType.IMAGE:
            payload = {
                "msgtype": "image",
                "image": {"media_id": media_id},
            }
        elif media_type == MessageType.FILE:
            payload = {
                "msgtype": "file",
                "file": {"media_id": media_id},
            }
        else:
            return False, f"Unsupported media type: {media_type}"

        return await self._send_webhook(payload)

    async def download_media(self, media_url: str, local_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Download media (not typically used with bot API)."""
        return False, "WeCom bot does not support media download"

    async def upload_media(self, file_path: str, media_type: MessageType) -> MediaUploadResult:
        """Upload media to WeCom."""
        if not self.bot_key:
            return MediaUploadResult(success=False, error="Bot key not configured")

        path = Path(file_path)
        if not path.exists():
            return MediaUploadResult(success=False, error=f"File not found: {file_path}")

        # Map to WeCom media type
        type_map = {
            MessageType.IMAGE: "image",
            MessageType.FILE: "file",
            MessageType.VIDEO: "video",
            MessageType.AUDIO: "voice",
        }
        wecom_type = type_map.get(media_type, "file")

        url = f"{self.UPLOAD_URL}?key={self.bot_key}&type={wecom_type}"

        try:
            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"media": (path.name, f, "application/octet-stream")}
                    response = await client.post(url, files=files, timeout=120.0)
                    result = response.json()

                    if result.get("errcode") == 0:
                        return MediaUploadResult(
                            success=True,
                            media_id=result.get("media_id"),
                        )
                    return MediaUploadResult(
                        success=False,
                        error=result.get("errmsg"),
                    )
        except Exception as e:
            return MediaUploadResult(success=False, error=str(e))

    async def start(self) -> None:
        """Start (no-op for webhook-based bot)."""
        pass

    async def stop(self) -> None:
        """Stop (no-op for webhook-based bot)."""
        pass
