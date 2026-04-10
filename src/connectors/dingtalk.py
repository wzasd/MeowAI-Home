"""DingTalk platform connector for MeowAI Home multi-agent gateway."""
import hashlib
import hmac
from typing import Any, Dict, Optional

from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class DingTalkConnector(BaseConnector):
    """Connector for DingTalk robot outgoing webhooks.

    DingTalk robot sends messages via outgoing webhook. The connector
    validates HMAC-SHA256 signatures, parses text messages, and returns
    response text directly in the HTTP response body.
    """

    platform = "dingtalk"

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret

    async def validate_request(
        self, headers: Dict[str, str], body: bytes
    ) -> bool:
        """Validate DingTalk webhook signature using HMAC-SHA256.

        DingTalk signs requests with: sign = HmacSHA256(timestamp + "\\n" + app_secret, app_secret)
        The sign and timestamp are sent in the HTTP headers.
        """
        timestamp = headers.get("timestamp")
        sign = headers.get("sign")

        if not timestamp or not sign:
            return False

        string_to_sign = f"{timestamp}\n{self.app_secret}"
        expected_sign = hmac.new(
            self.app_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(sign, expected_sign)

    def parse_message(self, payload: Dict[str, Any]) -> Optional[PlatformMessage]:
        """Parse a DingTalk robot message into a normalized PlatformMessage.

        Only handles text messages (msgtype == "text").
        Returns None for non-text messages or payloads with missing required fields.
        """
        if not payload:
            return None

        if payload.get("msgtype") != "text":
            return None

        text_obj = payload.get("text")
        if not text_obj or not isinstance(text_obj, dict):
            return None

        content = text_obj.get("content")
        if content is None:
            return None

        chat_id = payload.get("conversationId")
        if not chat_id:
            return None

        user_id = payload.get("senderStaffId") or payload.get("senderId", "")
        if not user_id:
            return None

        user_name = payload.get("senderNick", "")

        return PlatformMessage(
            platform=self.platform,
            chat_id=chat_id,
            user_id=user_id,
            user_name=user_name,
            content=content,
            raw=payload,
        )

    async def send_response(
        self, chat_id: str, response: PlatformResponse
    ) -> bool:
        """Send response back via DingTalk.

        For DingTalk outgoing webhooks, the robot response is returned
        directly in the HTTP response body. No separate HTTP call is needed.
        The gateway layer handles embedding this into the HTTP response.

        Returns True to indicate the response was prepared successfully.
        """
        return True
