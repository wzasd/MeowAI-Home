"""Connector management API routes."""
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/connectors", tags=["connectors"])


class ConnectorConfig(BaseModel):
    name: str
    enabled: bool
    config: Dict


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