"""Connector management API routes."""
import base64
import hashlib
import secrets
import time
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/connectors", tags=["connectors"])


# === Binding state (in-memory, TODO: persist to database) ===

_binding_state: Dict[str, Dict] = {}


def _init_binding(name: str):
    """Ensure binding state exists for a connector."""
    if name not in _binding_state:
        _binding_state[name] = {
            "bound": False,
            "bound_at": None,
            "bound_user": None,
            "qr_token": None,
            "qr_expires": None,
        }


# === Models ===


class ConnectorConfig(BaseModel):
    name: str
    enabled: bool
    config: Dict


class ConnectorBindingStatus(BaseModel):
    name: str
    bound: bool
    bound_at: Optional[str] = None
    bound_user: Optional[str] = None
    connector_type: Optional[str] = None


@router.get("")
async def list_connectors(request: Request) -> Dict:
    """List all configured connectors with status."""
    # Get connector router from app state if available
    router_obj = getattr(request.app.state, "connector_router", None)

    connectors = [
        {
            "name": "feishu",
            "displayName": "飞书",
            "enabled": True,
            "status": "healthy" if router_obj else "unknown",
            "features": ["text", "image", "file", "rich_card", "streaming"],
            "configFields": ["app_id", "app_secret"],
        },
        {
            "name": "dingtalk",
            "displayName": "钉钉",
            "enabled": True,
            "status": "healthy" if router_obj else "unknown",
            "features": ["text", "image", "file", "ai_card", "streaming"],
            "configFields": ["app_key", "app_secret"],
        },
        {
            "name": "weixin",
            "displayName": "微信",
            "enabled": False,
            "status": "disabled",
            "features": ["text", "image", "file", "voice"],
            "configFields": ["api_key", "base_url"],
        },
        {
            "name": "wecom_bot",
            "displayName": "企业微信机器人",
            "enabled": False,
            "status": "disabled",
            "features": ["text", "markdown", "template_card", "image", "file"],
            "configFields": ["bot_key"],
        },
    ]

    return {
        "connectors": connectors,
    }


@router.get("/{name}/status")
async def get_connector_status(name: str, request: Request) -> Dict:
    """Get detailed status for a connector."""
    router_obj = getattr(request.app.state, "connector_router", None)

    # Check if adapter exists
    adapter = None
    if router_obj and hasattr(router_obj, "_adapters"):
        adapter = router_obj._adapters.get(name)

    if not adapter:
        return {
            "name": name,
            "connected": False,
            "health": "unknown",
            "message": "Connector not initialized",
        }

    # Get health status if available
    try:
        import asyncio
        health = asyncio.run(adapter.health_check())
        return {
            "name": name,
            "connected": health.connected,
            "health": health.health.value,
            "lastError": health.last_error,
            "messageCount24h": health.message_count_24h,
            "avgLatencyMs": health.avg_latency_ms,
        }
    except Exception as e:
        return {
            "name": name,
            "connected": False,
            "health": "error",
            "message": str(e),
        }


@router.post("/{name}/test")
async def test_connector(name: str, request: Request) -> Dict:
    """Test connector configuration."""
    body = await request.json()
    config = body.get("config", {})

    # Validate required fields based on connector type
    required = {
        "feishu": ["app_id", "app_secret"],
        "dingtalk": ["app_key", "app_secret"],
        "weixin": ["api_key"],
        "wecom_bot": ["bot_key"],
    }

    missing = [f for f in required.get(name, []) if not config.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {missing}"
        )

    # Try to initialize adapter
    try:
        if name == "feishu":
            from src.connectors.feishu_adapter import FeishuAdapter
            adapter = FeishuAdapter()
            success = await adapter.initialize(config)
        elif name == "dingtalk":
            from src.connectors.dingtalk_adapter import DingTalkAdapter
            adapter = DingTalkAdapter()
            success = await adapter.initialize(config)
        elif name == "weixin":
            from src.connectors.weixin_adapter import WeixinAdapter
            adapter = WeixinAdapter()
            success = await adapter.initialize(config)
        elif name == "wecom_bot":
            from src.connectors.wecom_bot_adapter import WeComBotAdapter
            adapter = WeComBotAdapter()
            success = await adapter.initialize(config)
        else:
            raise HTTPException(status_code=404, detail=f"Unknown connector: {name}")

        return {
            "success": success,
            "message": "Connection test successful" if success else "Connection failed",
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/{name}/enable")
async def enable_connector(name: str, request: Request) -> Dict:
    """Enable a connector."""
    # This would update configuration to enable the connector
    return {
        "success": True,
        "message": f"Connector {name} enabled",
    }


@router.post("/{name}/disable")
async def disable_connector(name: str, request: Request) -> Dict:
    """Disable a connector."""
    return {
        "success": True,
        "message": f"Connector {name} disabled",
    }


# === Binding / QR endpoints ===


@router.get("/{name}/binding-status")
async def get_binding_status(name: str) -> Dict:
    """Get binding status for a connector."""
    _init_binding(name)
    state = _binding_state[name]
    return {
        "name": name,
        "bound": state["bound"],
        "bound_at": state["bound_at"],
        "bound_user": state["bound_user"],
    }


@router.get("/{name}/qr")
async def get_connector_qr(name: str) -> Dict:
    """Generate a QR binding token for a connector.

    Returns a data URL that can be rendered as QR code on the frontend.
    The token is a short-lived random string that simulates an OAuth-style bind flow.
    """
    _init_binding(name)

    # Generate token
    token = secrets.token_urlsafe(32)
    expires = time.time() + 300  # 5 minutes

    _binding_state[name]["qr_token"] = token
    _binding_state[name]["qr_expires"] = expires

    # The QR payload is a simple bind URL (in production this would be an OAuth URL)
    bind_url = f"meowai://bind/{name}?token={token}&t={int(time.time())}"

    # Generate a simple SVG QR-code placeholder (data URL)
    # In production, use a proper QR library like qrcode
    qr_data_url = _generate_qr_svg_data_url(bind_url)

    return {
        "name": name,
        "qr_data_url": qr_data_url,
        "bind_url": bind_url,
        "expires_in": 300,
        "token": token,
    }


@router.post("/{name}/bind-callback")
async def bind_callback(name: str, request: Request) -> Dict:
    """Simulate a bind callback (e.g., user scanned QR and approved).

    In production, this would be called by the external platform's OAuth callback.
    """
    body = await request.json()
    token = body.get("token", "")
    user_name = body.get("user_name", "未知用户")

    _init_binding(name)
    state = _binding_state[name]

    # Verify token
    if not state["qr_token"] or state["qr_token"] != token:
        raise HTTPException(status_code=400, detail="Invalid or expired binding token")

    if state["qr_expires"] and time.time() > state["qr_expires"]:
        raise HTTPException(status_code=400, detail="Binding token expired")

    # Mark as bound
    from datetime import datetime, timezone
    state["bound"] = True
    state["bound_at"] = datetime.now(timezone.utc).isoformat()
    state["bound_user"] = user_name
    state["qr_token"] = None
    state["qr_expires"] = None

    return {
        "success": True,
        "name": name,
        "bound": True,
        "bound_user": user_name,
    }


@router.post("/{name}/unbind")
async def unbind_connector(name: str) -> Dict:
    """Unbind a connector (remove binding)."""
    _init_binding(name)
    state = _binding_state[name]

    if not state["bound"]:
        raise HTTPException(status_code=400, detail="Connector is not bound")

    state["bound"] = False
    state["bound_at"] = None
    state["bound_user"] = None

    return {
        "success": True,
        "message": f"Connector {name} unbound",
    }


def _generate_qr_svg_data_url(data: str) -> str:
    """Generate a minimal SVG placeholder that displays bind info.

    In production, replace with actual QR code generation (e.g., qrcode library).
    """
    import urllib.parse

    short_data = data[:60] + ("..." if len(data) > 60 else "")
    escaped = urllib.parse.quote(short_data)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="220" viewBox="0 0 200 220">
  <rect width="200" height="200" fill="white" stroke="#e5e7eb" stroke-width="2" rx="8"/>
  <rect x="20" y="20" width="160" height="160" fill="#f3f4f6" rx="4"/>
  <text x="100" y="90" text-anchor="middle" font-size="14" fill="#6b7280">扫描绑定</text>
  <text x="100" y="115" text-anchor="middle" font-size="11" fill="#9ca3af">{escaped}</text>
  <rect x="70" y="130" width="60" height="30" fill="#3b82f6" rx="4"/>
  <text x="100" y="150" text-anchor="middle" font-size="11" fill="white">扫码连接</text>
  <text x="100" y="215" text-anchor="middle" font-size="10" fill="#9ca3af">5分钟内有效</text>
</svg>'''

    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return f"data:image/svg+xml;base64,{encoded}"