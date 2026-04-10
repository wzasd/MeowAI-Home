"""WeCom (企业微信) platform connector."""
import hashlib
from typing import Any, Dict, Optional

import httpx

from src.connectors.base import BaseConnector, PlatformMessage, PlatformResponse


class WeComConnector(BaseConnector):
    """Connector for WeCom (WeChat Work) platform."""

    platform = "wecom"

    def __init__(
        self,
        corp_id: str,
        agent_id: str,
        secret: str,
        token: str,
        encoding_aes_key: str,
    ):
        self.corp_id = corp_id
        self.agent_id = agent_id
        self.secret = secret
        self.token = token
        self.encoding_aes_key = encoding_aes_key
        self._access_token: Optional[str] = None

    # -- webhook validation -------------------------------------------------

    async def validate_request(
        self, headers: Dict[str, str], body: bytes
    ) -> bool:
        """Validate WeCom callback signature.

        WeCom computes: SHA1(sort(token, timestamp, nonce)).
        The result is passed as ``msg_signature`` in query params / headers.
        """
        timestamp = headers.get("timestamp", "")
        nonce = headers.get("nonce", "")
        msg_signature = headers.get("msg_signature", "")

        if not (timestamp and nonce and msg_signature):
            return False

        items = sorted([self.token, timestamp, nonce])
        raw = "".join(items)
        expected = hashlib.sha1(raw.encode()).hexdigest()
        return expected == msg_signature

    # -- message parsing ----------------------------------------------------

    def parse_message(self, payload: Dict[str, Any]) -> Optional[PlatformMessage]:
        """Parse WeCom JSON-format message payload.

        Expected keys: ``Content`` (text), ``FromUserName`` (user),
        ``ChatId`` (conversation).
        """
        content = payload.get("Content")
        user_id = payload.get("FromUserName")
        if not content or not user_id:
            return None

        chat_id = payload.get("ChatId", user_id)

        return PlatformMessage(
            platform=self.platform,
            chat_id=str(chat_id),
            user_id=str(user_id),
            user_name=str(user_id),
            content=str(content),
            raw=payload,
        )

    # -- sending replies ----------------------------------------------------

    async def send_response(
        self, chat_id: str, response: PlatformResponse
    ) -> bool:
        """Send a text message via WeCom message API."""
        token = await self._get_access_token()
        url = (
            f"https://qyapi.weixin.qq.com/cgi-bin/message/send"
            f"?access_token={token}"
        )
        payload = {
            "touser": chat_id,
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {"content": response.text},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            return data.get("errcode") == 0

    # -- helpers ------------------------------------------------------------

    async def _get_access_token(self) -> str:
        """Fetch or return cached access token."""
        if self._access_token:
            return self._access_token

        url = (
            f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
            f"?corpid={self.corp_id}&corpsecret={self.secret}"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()
            self._access_token = data.get("access_token", "")
            return self._access_token
