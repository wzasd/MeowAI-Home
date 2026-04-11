"""Base connector interfaces for MeowAI.

Defines the core contracts for inbound and outbound adapters.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, BinaryIO
from enum import Enum


class MessageType(Enum):
    """Supported message types."""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    RICH = "rich"  # Rich text / card message


@dataclass
class InboundMessage:
    """Standardized inbound message from any connector."""
    message_id: str
    thread_id: str
    user_id: str
    user_name: str
    content: str
    message_type: MessageType = MessageType.TEXT
    raw_data: Optional[Dict[str, Any]] = None
    # Media attachments
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    # @mention info
    mentioned_cats: Optional[List[str]] = None  # List of cat IDs mentioned
    is_at_all: bool = False


@dataclass
class OutboundMessage:
    """Standardized outbound message to send."""
    content: str
    message_type: MessageType = MessageType.TEXT
    # For rich messages
    rich_content: Optional[Dict[str, Any]] = None
    # For media
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    # For streaming/typing indicators
    placeholder_id: Optional[str] = None


@dataclass
class MediaUploadResult:
    """Result of media upload operation."""
    success: bool
    media_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


class IInboundAdapter(ABC):
    """Interface for receiving messages from external platforms."""

    @abstractmethod
    async def start(self) -> None:
        """Start listening for incoming messages."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening."""
        pass

    @abstractmethod
    def set_message_handler(self, handler: callable) -> None:
        """Set callback for received messages.

        Handler signature: async handler(InboundMessage) -> None
        """
        pass


class IOutboundAdapter(ABC):
    """Interface for sending messages to external platforms."""

    @abstractmethod
    async def send_message(
        self,
        thread_id: str,
        message: OutboundMessage,
    ) -> Tuple[bool, Optional[str]]:
        """Send a message.

        Returns: (success, message_id_or_error)
        """
        pass

    @abstractmethod
    async def send_reply(
        self,
        thread_id: str,
        reply_to_message_id: str,
        message: OutboundMessage,
    ) -> Tuple[bool, Optional[str]]:
        """Send a reply to a specific message."""
        pass


class IStreamableOutboundAdapter(IOutboundAdapter, ABC):
    """Extended outbound adapter with streaming and rich message support."""

    @abstractmethod
    async def send_placeholder(
        self,
        thread_id: str,
        content: str = "⏳ 处理中...",
    ) -> Tuple[bool, Optional[str]]:
        """Send a placeholder message, returns placeholder_id."""
        pass

    @abstractmethod
    async def edit_message(
        self,
        thread_id: str,
        message_id: str,
        new_content: str,
        rich_content: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Edit an existing message (for streaming updates)."""
        pass

    @abstractmethod
    async def delete_message(
        self,
        thread_id: str,
        message_id: str,
    ) -> bool:
        """Delete a message."""
        pass

    @abstractmethod
    async def send_rich_message(
        self,
        thread_id: str,
        card_type: str,  # e.g., "interactive", "template"
        card_data: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Send a rich card message."""
        pass

    @abstractmethod
    async def send_media(
        self,
        thread_id: str,
        media_type: MessageType,
        file_path: Optional[str] = None,
        file_data: Optional[bytes] = None,
        file_name: Optional[str] = None,
        caption: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Send media (image, file, audio, video)."""
        pass

    @abstractmethod
    async def download_media(
        self,
        media_url: str,
        local_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Download media from URL to local path.

        Returns: (success, local_path_or_error)
        """
        pass

    @abstractmethod
    async def upload_media(
        self,
        file_path: str,
        media_type: MessageType,
    ) -> MediaUploadResult:
        """Upload media to platform CDN."""
        pass


class ConnectorHealth(Enum):
    """Health status of a connector."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ConnectorStatus:
    """Status report for a connector."""
    name: str
    health: ConnectorHealth
    connected: bool
    last_error: Optional[str] = None
    message_count_24h: int = 0
    avg_latency_ms: float = 0.0


class IConnector(ABC):
    """Full connector interface combining inbound and outbound."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Connector name."""
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with configuration."""
        pass

    @abstractmethod
    async def health_check(self) -> ConnectorStatus:
        """Get current health status."""
        pass


# Legacy classes for backward compatibility
@dataclass
class PlatformMessage:
    """Normalized message from any platform (legacy)."""
    platform: str          # "feishu" | "dingtalk" | "wecom" | "telegram"
    chat_id: str           # Platform-specific conversation ID
    user_id: str           # Platform-specific user ID
    user_name: str
    content: str           # Message text
    raw: Dict[str, Any] = field(default_factory=dict)  # Original payload


@dataclass
class PlatformResponse:
    """Response to send back to platform (legacy)."""
    text: str
    markdown: Optional[str] = None


class BaseConnector(ABC):
    """Abstract base class for platform connectors (legacy)."""
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
