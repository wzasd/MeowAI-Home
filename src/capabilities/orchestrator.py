"""Capability orchestrator facade — the main entry point for capability management."""
from pathlib import Path
from typing import Dict, List, Literal, Optional

from src.capabilities.models import (
    CapabilitiesConfig,
    CapabilityBoardItem,
    CapabilityBoardResponse,
    CapabilityEntry,
    McpServerDescriptor,
)
from src.capabilities.io import read_capabilities_config, write_capabilities_config
from src.capabilities.bootstrap import bootstrap_capabilities
from src.capabilities.resolver import resolve_servers_for_cat
from src.capabilities.discovery import discover_skills
from src.capabilities.cli_adapters import (
    write_claude_mcp_config,
    write_codex_mcp_config,
    write_gemini_mcp_config,
)
from src.capabilities.mcp_probe import McpProbeResult
from src.models.cat_registry import cat_registry


PROVIDER_WRITERS = {
    "anthropic": write_claude_mcp_config,
    "openai": write_codex_mcp_config,
    "google": write_gemini_mcp_config,
}

STREAMABLE_HTTP_PROVIDERS = {"anthropic"}


def get_or_bootstrap(project_root: str) -> CapabilitiesConfig:
    """Read existing capabilities.json or bootstrap a new one, then sync skills."""
    config = read_capabilities_config(project_root)
    if config is None:
        config = bootstrap_capabilities(project_root)
    else:
        if sync_skills(project_root, config):
            config = read_capabilities_config(project_root) or config
    return config


def _collect_servers_per_provider(
    config: CapabilitiesConfig,
) -> Dict[str, Dict[str, McpServerDescriptor]]:
    """Group cats by provider, collecting the union of servers each provider needs.
    A server is included for a provider if ANY cat of that provider has it enabled.
    """
    provider_servers: Dict[str, Dict[str, McpServerDescriptor]] = {}

    for cat_id in cat_registry.get_all_ids():
        entry = cat_registry.try_get(cat_id)
        if not entry:
            continue
        provider = entry.provider
        if not provider:
            continue

        if provider not in provider_servers:
            provider_servers[provider] = {}

        servers = resolve_servers_for_cat(config, cat_id)
        for server in servers:
            existing = provider_servers[provider].get(server.name)
            if not existing or (server.enabled and not existing.enabled):
                provider_servers[provider][server.name] = server

    return provider_servers


def regenerate_cli_configs(project_root: str, config: CapabilitiesConfig) -> None:
    """Generate per-provider MCP config files from capabilities.json."""
    per_provider = _collect_servers_per_provider(config)

    for provider, server_map in per_provider.items():
        writer = PROVIDER_WRITERS.get(provider)
        if not writer:
            continue

        if provider == "anthropic":
            path = str(Path(project_root) / ".mcp.json")
        elif provider == "openai":
            path = str(Path(project_root) / ".codex" / "config.toml")
        elif provider == "google":
            path = str(Path(project_root) / ".gemini" / "settings.json")
        else:
            continue

        servers = list(server_map.values())
        writer(path, servers)


def sync_skills(project_root: str, config: CapabilitiesConfig) -> bool:
    """Sync discovered skills into capabilities.json. Returns True if mutated."""
    discovered = discover_skills(project_root)
    if not discovered:
        # If skills dir doesn't exist, prune all existing skills
        before = len(config.capabilities)
        config.capabilities = [c for c in config.capabilities if c.type != "skill"]
        if len(config.capabilities) != before:
            write_capabilities_config(project_root, config)
            return True
        return False

    existing_skills = {c.id: c for c in config.capabilities if c.type == "skill"}
    discovered_names = set(discovered.keys())
    dirty = False

    # Add new / update existing
    for skill_name, meta in discovered.items():
        if skill_name in existing_skills:
            cap = existing_skills[skill_name]
            if cap.description != meta.description or (cap.triggers or []) != (meta.triggers or []):
                cap.description = meta.description
                cap.triggers = meta.triggers
                dirty = True
        else:
            config.capabilities.append(
                CapabilityEntry(
                    id=skill_name,
                    type="skill",
                    enabled=True,
                    source="meowai",
                    description=meta.description,
                    triggers=meta.triggers,
                )
            )
            dirty = True

    # Prune stale skills
    before = len(config.capabilities)
    config.capabilities = [
        c for c in config.capabilities
        if c.type != "skill" or c.id in discovered_names
    ]
    if len(config.capabilities) != before:
        dirty = True

    if dirty:
        write_capabilities_config(project_root, config)
    return dirty


def toggle_capability(
    project_root: str,
    config: CapabilitiesConfig,
    capability_id: str,
    capability_type: Literal["mcp", "skill"],
    scope: Literal["global", "cat"],
    enabled: bool,
    cat_id: Optional[str] = None,
) -> CapabilityEntry:
    """Toggle a capability globally or per-cat, returning the mutated entry."""
    cap = next(
        (c for c in config.capabilities if c.id == capability_id and c.type == capability_type),
        None,
    )
    if not cap:
        raise ValueError(f"Capability not found: {capability_id} (type={capability_type})")

    if scope == "global":
        cap.enabled = enabled
    else:
        if not cat_id:
            raise ValueError("cat_id is required when scope is 'cat'")
        existing = next((o for o in cap.overrides if o.catId == cat_id), None)
        if existing:
            existing.enabled = enabled
        else:
            from src.capabilities.models import CatOverride
            cap.overrides.append(CatOverride(catId=cat_id, enabled=enabled))
        # Clean up no-op overrides
        if enabled == cap.enabled:
            cap.overrides = [o for o in cap.overrides if o.catId != cat_id]

    write_capabilities_config(project_root, config)
    regenerate_cli_configs(project_root, config)
    return cap


def build_board_response(
    project_root: str,
    config: CapabilitiesConfig,
    probe_results: Optional[List[McpProbeResult]] = None,
) -> CapabilityBoardResponse:
    """Build the capability board response for the frontend."""
    cat_ids = cat_registry.get_all_ids()
    items: List[CapabilityBoardItem] = []
    probe_map = {r.capabilityId: r for r in (probe_results or [])}

    for cap in config.capabilities:
        cats_map: Dict[str, bool] = {}

        if cap.type == "mcp":
            for cat_id in cat_ids:
                servers = resolve_servers_for_cat(config, cat_id)
                server = next((s for s in servers if s.name == cap.id), None)
                cats_map[cat_id] = server.enabled if server else False
        else:
            # skill: for now treat as available to all cats, using global + override
            for cat_id in cat_ids:
                override = next((o for o in cap.overrides if o.catId == cat_id), None)
                cats_map[cat_id] = override.enabled if override else cap.enabled

        probe = probe_map.get(cap.id) if cap.type == "mcp" else None
        items.append(
            CapabilityBoardItem(
                id=cap.id,
                type=cap.type,
                source=cap.source,
                enabled=cap.enabled,
                description=cap.description,
                triggers=cap.triggers,
                cats=cats_map,
                connectionStatus=probe.connectionStatus if probe else None,
                tools=probe.tools if probe else None,
                probeError=probe.error if probe else None,
            )
        )

    return CapabilityBoardResponse(items=items, projectPath=project_root)
