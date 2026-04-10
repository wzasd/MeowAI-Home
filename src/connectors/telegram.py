"""Telegram Bot platform connector."""
from typing import Any, Dict, Optional

import httpx

from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class TelegramConnector(BaseConnector):
    """Connector for Telegram Bot API."""

    platform = "telegram"

    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    # -- webhook validation -------------------------------------------------

    async def validate_request(
        self, headers: Dict[str, str], body: bytes
    ) -> bool:
        """Telegram does not sign webhooks by default; always accept."""
        return True

    # -- message parsing ----------------------------------------------------

    def parse_message(self, payload: Dict[str, Any]) -> Optional[PlatformMessage]:
        """Parse a Telegram ``message`` update.

        Returns ``None`` for non-text messages or payloads missing the
        ``message`` key.
        """
        message = payload.get("message")
        if not message:
            return None

        text = message.get("text")
        if text is None:
            return None

        chat = message.get("chat", {})
        sender = message.get("from", {})

        return PlatformMessage(
            platform=self.platform,
            chat_id=str(chat.get("id", "")),
            user_id=str(sender.get("id", "")),
            user_name=sender.get("first_name", ""),
            content=text,
            raw=payload,
        )

    # -- sending replies ----------------------------------------------------

    async def send_response(
        self, chat_id: str, response: PlatformResponse
    ) -> bool:
        """Send a text message via Telegram Bot API."""
        url = (
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        )
        payload = {
            "chat_id": chat_id,
            "text": response.text,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            return data.get("ok") is True
