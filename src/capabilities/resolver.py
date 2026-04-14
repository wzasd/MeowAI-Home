"""Resolve effective MCP servers for a specific cat."""
from typing import List

from src.capabilities.models import (
    CapabilitiesConfig,
    CapabilityEntry,
    McpServerDescriptor,
)
from src.models.cat_registry import cat_registry


STREAMABLE_HTTP_PROVIDERS = {"anthropic"}


def _has_usable_transport(server: McpServerDescriptor) -> bool:
    if server.transport == "streamableHttp":
        # streamableHttp compatibility is gated by provider, not generic transport
        return False
    if server.resolver:
        return bool(server.resolver.strip())
    return bool(server.command and server.command.strip())


def _resolve_single_server(
    cap: CapabilityEntry,
    provider: str,
    cat_id: str,
) -> McpServerDescriptor:
    """Resolve one capability entry into an effective MCP server descriptor."""
    mcp = cap.mcpServer
    if not mcp:
        raise ValueError(f"MCP capability {cap.id} is missing mcpServer configuration")

    override = next((o for o in cap.overrides if o.catId == cat_id), None)
    enabled_from_config = override.enabled if override else cap.enabled

    transport_supported = (
        mcp.transport == "streamableHttp"
        and provider in STREAMABLE_HTTP_PROVIDERS
        and bool(mcp.url and mcp.url.strip())
    ) or _has_usable_transport(
        McpServerDescriptor(
            name=cap.id,
            command=mcp.command,
            args=mcp.args or [],
            transport=mcp.transport,
            url=mcp.url,
            resolver=mcp.resolver,
        )
    )

    enabled = enabled_from_config and transport_supported

    desc = McpServerDescriptor(
        name=cap.id,
        command=mcp.command,
        args=mcp.args or [],
        enabled=enabled,
        source=cap.source,
        transport=mcp.transport,
        url=mcp.url,
        resolver=mcp.resolver,
        headers=mcp.headers,
        env=mcp.env,
        workingDir=mcp.workingDir,
    )
    return desc


def resolve_servers_for_cat(
    config: CapabilitiesConfig,
    cat_id: str,
) -> List[McpServerDescriptor]:
    """Return effective MCP servers for a cat, applying overrides and transport filters."""
    cat_config = cat_registry.try_get(cat_id)
    provider = cat_config.provider if cat_config else ""

    results: List[McpServerDescriptor] = []
    for cap in config.capabilities:
        if cap.type != "mcp" or not cap.mcpServer:
            continue
        results.append(_resolve_single_server(cap, provider, cat_id))
    return results
