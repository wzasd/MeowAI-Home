"""FastAPI routes for multi-platform webhook handling"""
from typing import Dict, List
from fastapi import APIRouter, Request, HTTPException

from src.connectors.base import BaseConnector, PlatformMessage

router = APIRouter(prefix="/webhook")

_connectors: Dict[str, BaseConnector] = {}


def register_connector(connector: BaseConnector):
    """Register a platform connector for webhook handling."""
    _connectors[connector.platform] = connector


def unregister_connector(platform: str):
    """Unregister a platform connector."""
    if platform in _connectors:
        del _connectors[platform]


def list_connectors() -> List[str]:
    """List registered connector platforms."""
    return list(_connectors.keys())


def _get_connector(platform: str) -> BaseConnector:
    """Get a connector by platform name."""
    return _connectors.get(platform)


@router.post("/{platform}")
async def handle_webhook(platform: str, request: Request):
    """Receive webhook from platform, validate, parse, and forward to thread system."""
    connector = _get_connector(platform)
    if not connector:
        raise HTTPException(404, detail=f"Unknown platform: {platform}")

    body = await request.body()
    headers = dict(request.headers)

    if not await connector.validate_request(headers, body):
        raise HTTPException(401, detail="Invalid signature")

    payload = await request.json()
    msg = connector.parse_message(payload)
    if not msg:
        return {"status": "ignored", "reason": "no message parsed"}

    thread_id = connector.map_chat_to_thread(msg.chat_id)
    # TODO: Forward to A2AController for processing
    return {
        "status": "ok",
        "thread_id": thread_id,
        "platform": platform,
        "user": msg.user_name,
    }
