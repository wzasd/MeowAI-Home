"""BaseConnector abstract class for multi-platform gateway"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlatformMessage:
    """Normalized message from any platform."""
    platform: str          # "feishu" | "dingtalk" | "wecom" | "telegram"
    chat_id: str           # Platform-specific conversation ID
    user_id: str           # Platform-specific user ID
    user_name: str
    content: str           # Message text
    raw: Dict[str, Any] = field(default_factory=dict)  # Original payload


@dataclass
class PlatformResponse:
    """Response to send back to platform."""
    text: str
    markdown: Optional[str] = None


class BaseConnector(ABC):
    """Abstract base class for platform connectors."""
    platform: str = "base"

    @abstractmethod
    async def validate_request(self, headers: Dict[str, str], body: bytes) -> bool:
        """Verify webhook signature."""
        ...

    @abstractmethod
    def parse_message(self, payload: Dict[str, Any]) -> Optional[PlatformMessage]:
        """Extract normalized message from platform payload."""
        ...

    @abstractmethod
    async def send_response(self, chat_id: str, response: PlatformResponse) -> bool:
        """Send reply back to platform."""
        ...

    def map_chat_to_thread(self, chat_id: str) -> str:
        """Map platform chat_id to internal thread_id."""
        return f"{self.platform}:{chat_id}"

    def map_thread_to_chat(self, thread_id: str) -> str:
        """Reverse mapping from thread_id to platform chat_id."""
        prefix = f"{self.platform}:"
        return thread_id[len(prefix):] if thread_id.startswith(prefix) else thread_id
