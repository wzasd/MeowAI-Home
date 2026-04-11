"""DingTalk connector adapter.

Supports Stream SDK mode and AI Card streaming.
Implements 300ms throttle for updates.
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


class DingTalkAdapter(IStreamableOutboundAdapter):
    """DingTalk platform adapter with AI Card streaming support."""

    BASE_URL = "https://api.dingtalk.com"

    def __init__(self):
        self.app_key: Optional[str] = None
        self.app_secret: Optional[str] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        self._handler: Optional[callable] = None
        self._last_update_time: float = 0
        self._update_throttle_ms: int = 300  # 300ms throttle

    @property
    def name(self) -> str:
        return "dingtalk"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with credentials."""
        self.app_key = config.get("app_key") or os.environ.get("DINGTALK_APP_KEY")
        self.app_secret = config.get("app_secret") or os.environ.get("DINGTALK_APP_SECRET")

        if not self.app_key or not self.app_secret:
            return False

        # Get initial token
        await self._get_access_token()
        return True

    async def _get_access_token(self) -> bool:
        """Get access token."""
        url = f"{self.BASE_URL}/v1.0/oauth2/accessToken"
        payload = {
            "appKey": self.app_key,
            "appSecret": self.app_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()

            if "accessToken" in data:
                self.access_token = data["accessToken"]
                # Token expires in 2 hours, refresh 5 min early
                expires_in = data.get("expireIn", 7200)
                self.token_expires_at = time.time() + expires_in - 300
                return True
            return False

    async def _ensure_token(self) -> bool:
        """Ensure valid token, refresh if needed."""
        if not self.access_token or time.time() > self.token_expires_at:
            return await self._get_access_token()
        return True

    def _headers(self) -> Dict[str, str]:
        """Get auth headers."""
        return {
            "x-acs-dingtalk-access-token": self.access_token or "",
            "Content-Type": "application/json",
        }

    async def _throttle(self) -> None:
        """Apply 300ms throttle between updates."""
        now = time.time()
        elapsed_ms = (now - self._last_update_time) * 1000
        if elapsed_ms < self._update_throttle_ms:
            await asyncio.sleep((self._update_throttle_ms - elapsed_ms) / 1000)
        self._last_update_time = time.time()

    async def health_check(self) -> ConnectorStatus:
        """Check connector health."""
        healthy = await self._ensure_token()
        return ConnectorStatus(
            name=self.name,
            health=ConnectorHealth.HEALTHY if healthy else ConnectorHealth.UNHEALTHY,
            connected=healthy and self.access_token is not None,
        )

    def set_message_handler(self, handler: callable) -> None:
        """Set handler for incoming messages."""
        self._handler = handler

    def parse_inbound(self, payload: Dict[str, Any]) -> Optional[InboundMessage]:
        """Parse DingTalk webhook payload to standardized message."""
        try:
            # Check required fields
            if not payload.get("conversationId") or not payload.get("msgId"):
                return None

            msg_type = payload.get("msgtype", "text")
            content = payload.get("text", {}).get("content", "")

            # Handle different message types
            if msg_type == "picture":
                content_data = payload.get("content", {})
                file_url = content_data.get("downloadCode") or content_data.get("pictureDownloadCode", "")
            elif msg_type == "richText":
                content = payload.get("content", {}).get("richText", [{}])[0].get("text", "")
                file_url = None
            else:
                file_url = None

            # Map message type
            msg_type_enum = self._map_message_type(msg_type)

            return InboundMessage(
                message_id=payload.get("msgId", ""),
                thread_id=f"dingtalk:{payload['conversationId']}",
                user_id=payload.get("senderStaffId", ""),
                user_name=payload.get("senderNick", "unknown"),
                content=content,
                message_type=msg_type_enum,
                raw_data=payload,
                file_url=file_url,
                mentioned_cats=None,  # TODO: Parse @mentions
            )
        except Exception:
            return None

    def _map_message_type(self, dingtalk_type: str) -> MessageType:
        """Map DingTalk message type to standard type."""
        mapping = {
            "text": MessageType.TEXT,
            "picture": MessageType.IMAGE,
            "file": MessageType.FILE,
            "voice": MessageType.AUDIO,
            "richText": MessageType.RICH,
        }
        return mapping.get(dingtalk_type, MessageType.TEXT)

    async def _api_call(self, method: str, url: str, **kwargs) -> Tuple[Dict[str, Any], bool]:
        """Make API call with token refresh on auth error."""
        if not await self._ensure_token():
            return {}, False

        async with httpx.AsyncClient() as client:
            headers = kwargs.pop("headers", self._headers())
            response = await client.request(method, url, headers=headers, timeout=60.0, **kwargs)
            data = response.json()

            success = data.get("success", False) or response.status_code == 200
            return data, success

    async def send_message(self, thread_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send message to conversation."""
        conversation_id = thread_id.replace("dingtalk:", "")
        url = f"{self.BASE_URL}/v1.0/im/interactiveCards/send"

        if message.message_type == MessageType.RICH and message.rich_content:
            # AI Card streaming
            payload = {
                "conversationType": 1,  # Group chat
                "openConversationId": conversation_id,
                "cardTemplateId": "StandardCard",
                "cardData": json.dumps(message.rich_content),
                "callbackType": "STREAM",
            }
        else:
            # Simple text via AI card
            payload = {
                "conversationType": 1,
                "openConversationId": conversation_id,
                "cardTemplateId": "StandardCard",
                "cardData": json.dumps({"content": message.content}),
                "callbackType": "STREAM",
            }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("result", {}).get("processQueryKey")
        return False, data.get("errmsg")

    async def send_reply(self, thread_id: str, reply_to_message_id: str, message: OutboundMessage) -> Tuple[bool, Optional[str]]:
        """Send reply (DingTalk uses conversation for replies)."""
        return await self.send_message(thread_id, message)

    async def send_placeholder(self, thread_id: str, content: str = "⏳ 处理中...") -> Tuple[bool, Optional[str]]:
        """Send placeholder card for streaming."""
        card_data = {
            "status": "PROCESSING",
            "content": content,
        }
        return await self.send_rich_message(thread_id, "ai_card", card_data)

    async def edit_message(self, thread_id: str, message_id: str, new_content: str, rich_content: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """Edit/update existing AI card (streaming update)."""
        await self._throttle()

        url = f"{self.BASE_URL}/v1.0/im/interactiveCards/update"

        if rich_content:
            card_data = rich_content
        else:
            card_data = {"content": new_content}

        payload = {
            "processQueryKey": message_id,
            "cardData": json.dumps(card_data),
            "callbackType": "STREAM",
        }

        data, success = await self._api_call("PUT", url, json=payload)
        return success, data.get("errmsg") if not success else message_id

    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """Delete a message."""
        # DingTalk doesn't support direct message deletion
        return False

    async def send_rich_message(self, thread_id: str, card_type: str, card_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Send rich card message."""
        conversation_id = thread_id.replace("dingtalk:", "")
        url = f"{self.BASE_URL}/v1.0/im/interactiveCards/send"

        # AI Card format
        payload = {
            "conversationType": 1,
            "openConversationId": conversation_id,
            "cardTemplateId": "StandardCard" if card_type == "template" else "AIStreamCard",
            "cardData": json.dumps(card_data),
            "callbackType": "STREAM",
        }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("result", {}).get("processQueryKey")
        return False, data.get("errmsg")

    async def send_media(self, thread_id: str, media_type: MessageType, file_path: Optional[str] = None, file_data: Optional[bytes] = None, file_name: Optional[str] = None, caption: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Send media message."""
        if file_path:
            result = await self.upload_media(file_path, media_type)
            if not result.success:
                return False, result.error
            media_id = result.media_id
        elif file_data:
            # TODO: Implement direct upload
            return False, "Direct bytes upload not implemented"
        else:
            return False, "No file provided"

        # Send as file message
        conversation_id = thread_id.replace("dingtalk:", "")
        url = f"{self.BASE_URL}/v1.0/robot/oToMessages/batchSend"

        # Note: DingTalk robot API differs from interactive cards
        # For now, send as text with file reference
        payload = {
            "robotCode": self.app_key,
            "openConversationIds": [conversation_id],
            "msgKey": "sampleText",
            "msgParam": json.dumps({"content": caption or f"[File: {file_name or 'attachment'}]"}),
        }

        data, success = await self._api_call("POST", url, json=payload)
        if success:
            return True, data.get("result")
        return False, data.get("errmsg")

    async def download_media(self, media_url: str, local_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Download media using download code."""
        if not await self._ensure_token():
            return False, "Failed to get valid token"

        if local_path is None:
            local_path = f"/tmp/dingtalk_{int(time.time())}"

        try:
            url = f"{self.BASE_URL}/v1.0/im/files/{media_url}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={"x-acs-dingtalk-access-token": self.access_token or ""},
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
        """Upload media to DingTalk."""
        if not await self._ensure_token():
            return MediaUploadResult(success=False, error="Failed to get valid token")

        url = f"{self.BASE_URL}/v1.0/im/files"

        try:
            path = Path(file_path)
            if not path.exists():
                return MediaUploadResult(success=False, error=f"File not found: {file_path}")

            async with httpx.AsyncClient() as client:
                with open(file_path, "rb") as f:
                    files = {"file": (path.name, f, "application/octet-stream")}
                    data = {"uploadCode": "AUTO"}

                    response = await client.post(
                        url,
                        headers={"x-acs-dingtalk-access-token": self.access_token or ""},
                        files=files,
                        data=data,
                        timeout=120.0,
                    )

                    result = response.json()
                    if result.get("success"):
                        media_id = result.get("result", {}).get("mediaId")
                        return MediaUploadResult(success=True, media_id=media_id)
                    return MediaUploadResult(success=False, error=result.get("errmsg"))
        except Exception as e:
            return MediaUploadResult(success=False, error=str(e))

    async def start(self) -> None:
        """Start webhook server or stream connection."""
        pass

    async def stop(self) -> None:
        """Stop connections."""
        pass
