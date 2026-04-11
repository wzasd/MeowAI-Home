"""Feishu (Lark) connector adapter.

Supports text, image, file messages and interactive cards.
Implements streaming updates via card patches.
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


class FeishuAdapter(IStreamableOutboundAdapter):
    """Feishu/Lark platform adapter."""

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self):
        self.app_id: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.tenant_token: Optional[str] = None
        self.token_expires_at: float = 0
        self._handler: Optional[callable] = None

    @property
    def name(self) -> str:
        return "feishu"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with credentials."""
        self.app_id = config.get("app_id") or os.environ.get("FEISHU_APP_ID")
        self.app_secret = config.get("app_secret") or os.environ.get("FEISHU_APP_SECRET")

        if not self.app_id or not self.app_secret:
            return False

        # Get initial token
        await self._refresh_token()
        return True

    async def _refresh_token(self) -> bool:
        """Refresh tenant access token."""
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()

            if data.get("code") == 0:
                self.tenant_token = data.get("tenant_access_token")
                # Token expires in ~2 hours, refresh 5 min early
                expires_in = data.get("expire", 7200)
                self.token_expires_at = time.time() + expires_in - 300
                return True
            return False

    async def _ensure_token(self) -> bool:
        """Ensure valid token, refresh if needed."""
        if not self.tenant_token or time.time() > self.token_expires_at:
            return await self._refresh_token()
        return True

    def _headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {
            "Authorization": f"Bearer {self.tenant_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def health_check(self) -> ConnectorStatus:
        """Check connector health."""
        healthy = await self._ensure_token()
        return ConnectorStatus(
            name=self.name,
            health=ConnectorHealth.HEALTHY if healthy else ConnectorHealth.UNHEALTHY,
            connected=healthy and self.tenant_token is not None,
        )

    def set_message_handler(self, handler: callable) -> None:
        """Set handler for incoming messages."""
        self._handler = handler

    def parse_inbound(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        """Parse Feishu webhook payload to standardized message."""
        try:
            event = payload.get("event", {})
            message = event.get("message", {})
            sender = event.get("sender", {})

            # Check required fields
            if not message.get("message_id") or not message.get("chat_id"):
                return None

            message_type = message.get("message_type", "text")
            content_str = message.get("content", "{}")
            content = json.loads(content_str) if isinstance(content_str, str) else content_str

            # Map message type
            msg_type = self._map_message_type(message_type)

            # Extract text content
            text = content.get("text", "")
            if not text and "content" in content:
                text = content["content"]

            # Handle mentions
            mentioned_cats = None
            mentions = message.get("mentions", [])
            if mentions:
                mentioned_cats = [m.get("id", {}).get("user_id", "") for m in mentions]

            # Build file URL for media
            file_url = None
            if msg_type in (MessageType.IMAGE, MessageType.FILE, MessageType.AUDIO):
                file_key = content.get("file_key") or content.get("image_key")
                if file_key:
                    file_url = f"{self.BASE_URL}/im/v1/files/{file_key}"

            return InboundMessage(
                message_id=message.get("message_id", ""),
                thread_id=f"feishu:{message.get('chat_id', '')}",
                user_id=sender.get("sender_id", {}).get("user_id", ""),
                user_name=sender.get("sender_type", "unknown"),
                content=text,
                message_type=msg_type,
                raw_data=payload,
                file_url=file_url,
                file_name=content.get("file_name"),
                mentioned_cats=mentioned_cats,
            )
        except Exception:
            return None

    def _map_message_type(self, feishu_type: str) -> MessageType:
        """Map Feishu message type to standard type."""
        mapping = {
            "text": MessageType.TEXT,
            "image": MessageType.IMAGE,
            "file": MessageType.FILE,
            "audio": MessageType.AUDIO,
            "media": MessageType.AUDIO,
            "post": MessageType.RICH,
            "interactive": MessageType.RICH,
        }
        return mapping.get(feishu_type, MessageType.TEXT)

    async def _api_call(self, method: str, url: str, **kwargs) -> Tuple[Dict[str, Any], bool]:
        """Make API call with token refresh on auth error."""
        if not await self._ensure_token():
            return {}, False

        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self._headers(), timeout=60.0, **kwargs)
            data = response.json()

            # Check for auth error
            if data.get("code") == 99991663:  # Invalid tenant token
                if await self._refresh_token():
                    # Retry with new token
                    response = await client.request(method, url, headers=self._headers(), timeout=60.0, **kwargs)
                    data = response.json()

            success = data.get("code") == 0
            return data, success

    async def send_message(self, thread_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send message to thread."""
        chat_id = thread_id.replace("feishu:", "")
        url = f"{self.BASE_URL}/im/v1/messages?receive_id_type=chat_id"

        if message.message_type == MessageType.RICH and message.rich_content:
            msg_type = "interactive"
            content = json.dumps(message.rich_content)
        else:
            msg_type = "text"
            content = json.dumps({"text": message.content})

        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": content,
        }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("data", {}).get("message_id")
        return False, data.get("msg")

    async def send_reply(self, thread_id: str, reply_to_message_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send reply (Feishu uses thread for replies)."""
        return await self.send_message(thread_id, message)

    async def send_placeholder(self, thread_id: str, content: str = "⏳ 处理中...") -> Tuple[bool, Optional[str]]:
        """Send placeholder card for streaming."""
        card_data = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": content}}],
        }
        return await self.send_rich_message(thread_id, "interactive", card_data)

    async def edit_message(self, thread_id: str, message_id: str, new_content: str, rich_content: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """Edit existing message (used for streaming updates)."""
        url = f"{self.BASE_URL}/im/v1/messages/{message_id}"

        if rich_content:
            content = json.dumps(rich_content)
            msg_type = "interactive"
        else:
            content = json.dumps({"text": new_content})
            msg_type = "text"

        payload = {
            "content": content,
            "msg_type": msg_type,
        }

        data, success = await self._api_call("PATCH", url, json=payload)
        return success, data.get("msg") if not success else message_id

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Delete a message."""
        url = f"{self.BASE_URL}/im/v1/messages/{message_id}"
        data, success = await self._api_call("DELETE", url)
        return success

    async def send_rich_message(self, thread_id: str, card_type: str, card_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Send rich card message."""
        chat_id = thread_id.replace("feishu:", "")
        url = f"{self.BASE_URL}/im/v1/messages?receive_id_type=chat_id"

        content = json.dumps(card_data)
        msg_type = "interactive" if card_type == "interactive" else "post"

        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": content,
        }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("data", {}).get("message_id")
        return False, data.get("msg")

    async def send_media(self, thread_id: str, media_type: MessageType, file_path: Optional[str] = None, file_data: Optional[bytes] = None, file_name: Optional[str] = None, caption: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Send media message."""
        if file_path:
            # Upload first
            result = await self.upload_media(file_path, media_type)
            if not result.success:
                return False, result.error
            file_key = result.media_id
        elif file_data:
            # TODO: Implement direct upload from bytes
            return False, "Direct bytes upload not implemented"
        else:
            return False, "No file provided"

        chat_id = thread_id.replace("feishu:", "")
        url = f"{self.BASE_URL}/im/v1/messages?receive_id_type=chat_id"

        # Map to Feishu message type
        if media_type == MessageType.IMAGE:
            msg_type = "image"
            content = json.dumps({"image_key": file_key})
        elif media_type == MessageType.FILE:
            msg_type = "file"
            content = json.dumps({"file_key": file_key})
        elif media_type == MessageType.AUDIO:
            msg_type = "audio"
            content = json.dumps({"file_key": file_key})
        else:
            return False, f"Unsupported media type: {media_type}"

        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": content,
        }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("data", {}).get("message_id")
        return False, data.get("msg")

    async def download_media(self, media_url: str, local_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Download media from Feishu."""
        if not await self._ensure_token():
            return False, "Failed to get valid token"

        if local_path is None:
            local_path = f"/tmp/feishu_{int(time.time())}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {self.tenant_token}"},
                    timeout=120.0,
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(response.content)
                    return True, local_path
                return False, f"Download failed: {response.status_code}"
        except Exception as e:
            return False, str(e)

    async def upload_media(self, file_path: str, media_type: MessageType) -> MediaUploadResult:
        """Upload media to Feishu."""
        if not await self._ensure_token():
            return MediaUploadResult(success=False, error="Failed to get valid token")

        # Map to Feishu resource type
        resource_type = {
            MessageType.IMAGE: "image",
            MessageType.FILE: "file",
            MessageType.AUDIO: "file",
        }.get(media_type, "file")

        url = f"{self.BASE_URL}/im/v1/files"

        try:
            path = Path(file_path)
            if not path.exists():
                return MediaUploadResult(success=False, error=f"File not found: {file_path}")

            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"file": (path.name, f, "application/octet-stream")}
                    data = {"file_type": resource_type, "file_name": path.name}

                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.tenant_token}"},
                        files=files,
                        data=data,
                        timeout=120.0,
                    )

                    result = response.json()
                    if result.get("code") == 0:
                        file_key = result.get("data", {}).get("file_key")
                        return MediaUploadResult(success=True, media_id=file_key)
                    return MediaUploadResult(success=False, error=result.get("msg"))
        except Exception as e:
            return MediaUploadResult(success=False, error=str(e))

    async def start(self) -> None:
        """Start webhook server or stream connection."""
        # Feishu uses webhooks - handled by HTTP server
        pass

    async def stop(self) -> None:
        """Stop connections."""
        pass
