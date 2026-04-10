"""Feishu/Lark platform connector for MeowAI Home multi-agent gateway."""
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional

import httpx

from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class FeishuConnector(BaseConnector):
    """Connector for Feishu (Lark) platform webhooks and API."""

    platform = "feishu"

    def __init__(self, app_id: str, app_secret: str, verification_token: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # -- Signature validation ------------------------------------------------

    async def validate_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """Validate X-Lark-Signature using HMAC-SHA256.

        The signature is computed over: timestamp + verification_token + body
        with verification_token as the HMAC key.
        """
        timestamp = headers.get("X-Lark-Request-Timestamp", "")
        signature = headers.get("X-Lark-Signature", "")

        sign_content = f"{timestamp}{self.verification_token}".encode("utf-8") + body
        expected = hmac.new(
            self.verification_token.encode("utf-8"),
            sign_content,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    # -- Message parsing -----------------------------------------------------

    def parse_message(self, payload: Dict[str, Any]) -> Optional[PlatformMessage]:
        """Extract a normalized PlatformMessage from a Feishu event payload.

        Returns None if the payload is missing required fields.
        """
        event = payload.get("event")
        if not event or not isinstance(event, dict):
            return None

        message = event.get("message")
        if not message or not isinstance(message, dict):
            return None

        chat_id = message.get("chat_id")
        if not chat_id:
            return None

        # Extract sender info
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}) if isinstance(sender, dict) else {}
        user_id = sender_id.get("user_id", "")

        # Extract text content
        content_raw = message.get("content", "{}")
        try:
            content_obj = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
            text = content_obj.get("text", "")
        except (json.JSONDecodeError, AttributeError):
            text = content_raw if isinstance(content_raw, str) else ""

        return PlatformMessage(
            platform=self.platform,
            chat_id=chat_id,
            user_id=user_id,
            user_name="",
            content=text,
            raw=payload,
        )

    # -- Send response -------------------------------------------------------

    async def send_response(self, chat_id: str, response: PlatformResponse) -> bool:
        """Send a text reply to a Feishu chat via the im/v1/messages API."""
        token = await self._get_access_token()
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"

        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": response.text}),
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers)
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # -- Access token management ---------------------------------------------

    async def _get_access_token(self) -> str:
        """Obtain or return cached tenant_access_token."""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        self._access_token = data["tenant_access_token"]
        # Cache with a small safety margin (expire - 60s)
        self._token_expires_at = time.time() + data.get("expire", 7200) - 60
        return self._access_token
