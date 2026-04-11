"""Connector messages API — external system message integration."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid
import asyncio
import json

router = APIRouter(prefix="/connectors", tags=["connectors"])

# === Types ===

ContentBlockType = Literal["text", "image", "file"]
ConnectorType = Literal["feishu", "dingtalk", "weixin", "wecom", "github", "scheduler", "system"]


class ContentBlock(BaseModel):
    """Content block for rich messages."""
    type: ContentBlockType
    text: Optional[str] = None
    url: Optional[str] = None
    mime_type: Optional[str] = None


class SenderInfo(BaseModel):
    """Sender information."""
    id: str
    name: str
    avatar: Optional[str] = None


class ConnectorMessage(BaseModel):
    """Connector message model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    connector: ConnectorType
    connector_type: Literal["group", "private", "system"]
    sender: SenderInfo
    content: str
    content_blocks: List[ContentBlock] = Field(default_factory=list)
    timestamp: int = Field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    source_url: Optional[str] = None
    icon: str = "🔗"  # emoji or URL
    thread_id: Optional[str] = None


class MessageCreateRequest(BaseModel):
    """Create connector message request."""
    connector: ConnectorType
    connector_type: Literal["group", "private", "system"] = "group"
    sender: SenderInfo
    content: str
    content_blocks: List[ContentBlock] = Field(default_factory=list)
    source_url: Optional[str] = None
    icon: str = "🔗"
    thread_id: Optional[str] = None


class MessagesResponse(BaseModel):
    """Messages list response."""
    messages: List[ConnectorMessage]
    total: int


# === In-memory storage (TODO: replace with database) ===

_messages: List[ConnectorMessage] = []
_websockets: List[WebSocket] = []


def _get_connector_icon(connector: ConnectorType) -> str:
    """Get default icon for connector."""
    icons = {
        "feishu": "📱",
        "dingtalk": "💼",
        "weixin": "💬",
        "wecom": "🏢",
        "github": "🐙",
        "scheduler": "⏰",
        "system": "⚙️",
    }
    return icons.get(connector, "🔗")


def _get_connector_theme(connector: ConnectorType) -> Dict[str, str]:
    """Get theme colors for connector."""
    themes = {
        "feishu": {
            "avatar": "bg-blue-100 ring-2 ring-blue-200",
            "label": "text-blue-700",
            "bubble": "border border-blue-200 bg-blue-50",
        },
        "dingtalk": {
            "avatar": "bg-cyan-100 ring-2 ring-cyan-200",
            "label": "text-cyan-700",
            "bubble": "border border-cyan-200 bg-cyan-50",
        },
        "weixin": {
            "avatar": "bg-green-100 ring-2 ring-green-200",
            "label": "text-green-700",
            "bubble": "border border-green-200 bg-green-50",
        },
        "wecom": {
            "avatar": "bg-indigo-100 ring-2 ring-indigo-200",
            "label": "text-indigo-700",
            "bubble": "border border-indigo-200 bg-indigo-50",
        },
        "github": {
            "avatar": "bg-gray-100 ring-2 ring-gray-200",
            "label": "text-gray-700",
            "bubble": "border border-gray-200 bg-gray-50",
        },
        "scheduler": {
            "avatar": "bg-amber-100 ring-2 ring-amber-200",
            "label": "text-amber-700",
            "bubble": "border border-amber-200 bg-amber-50",
        },
        "system": {
            "avatar": "bg-purple-100 ring-2 ring-purple-200",
            "label": "text-purple-700",
            "bubble": "border border-purple-200 bg-purple-50",
        },
    }
    return themes.get(connector, themes["system"])


# === WebSocket Manager ===

class ConnectionManager:
    """WebSocket connection manager."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# === API Endpoints ===

@router.get("/messages", response_model=MessagesResponse)
async def list_messages(
    connector: Optional[ConnectorType] = None,
    thread_id: Optional[str] = None,
    limit: int = 50,
) -> MessagesResponse:
    """List connector messages with optional filtering."""
    messages = _messages

    if connector:
        messages = [m for m in messages if m.connector == connector]
    if thread_id:
        messages = [m for m in messages if m.thread_id == thread_id]

    # Sort by timestamp descending
    messages = sorted(messages, key=lambda m: m.timestamp, reverse=True)

    if limit > 0:
        messages = messages[:limit]

    return MessagesResponse(messages=messages, total=len(messages))


@router.post("/messages", response_model=ConnectorMessage)
async def create_message(request: MessageCreateRequest) -> ConnectorMessage:
    """Create a new connector message."""
    # Auto-detect icon if default was provided
    effective_icon = request.icon
    if not effective_icon or effective_icon == "🔗":
        effective_icon = _get_connector_icon(request.connector)

    message = ConnectorMessage(
        connector=request.connector,
        connector_type=request.connector_type,
        sender=request.sender,
        content=request.content,
        content_blocks=request.content_blocks,
        source_url=request.source_url,
        icon=effective_icon,
        thread_id=request.thread_id,
    )

    _messages.append(message)

    # Keep only last 1000 messages
    if len(_messages) > 1000:
        _messages.pop(0)

    # Broadcast to WebSocket clients
    await manager.broadcast({
        "type": "connector_message",
        "data": message.model_dump(),
    })

    return message


@router.get("/messages/{message_id}", response_model=ConnectorMessage)
async def get_message(message_id: str) -> ConnectorMessage:
    """Get a single message by ID."""
    for message in _messages:
        if message.id == message_id:
            return message
    raise HTTPException(status_code=404, detail="Message not found")


@router.delete("/messages/{message_id}")
async def delete_message(message_id: str) -> Dict[str, bool]:
    """Delete a connector message."""
    global _messages
    original_len = len(_messages)
    _messages = [m for m in _messages if m.id != message_id]

    if len(_messages) == original_len:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"success": True}


@router.get("/themes/{connector}")
async def get_connector_theme(connector: ConnectorType) -> Dict[str, str]:
    """Get theme for a connector."""
    return _get_connector_theme(connector)


@router.get("/icons/{connector}")
async def get_connector_icon(connector: ConnectorType) -> Dict[str, str]:
    """Get icon for a connector."""
    return {"icon": _get_connector_icon(connector)}


# === WebSocket Endpoint ===

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time connector messages."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Import HTTPException at module level
from fastapi import HTTPException
