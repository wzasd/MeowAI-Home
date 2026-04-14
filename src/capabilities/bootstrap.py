"""Bootstrap initial capabilities.json from discovered MCP servers."""
from pathlib import Path
from typing import List

from src.capabilities.models import (
    CapabilitiesConfig,
    CapabilityEntry,
    McpServerConfig,
    McpServerDescriptor,
)
from src.capabilities.io import write_capabilities_config
from src.capabilities.discovery import (
    DiscoveryPaths,
    discover_external_mcp_servers,
    discover_skills,
)


BUILTIN_MEOWAI_SERVER_IDS = ["meowai-memory", "meowai-collab", "meowai-signals"]


def _build_builtin_entries(project_root: str) -> List[CapabilityEntry]:
    """Placeholder built-in MCP servers for MeowAI Home."""
    return [
        CapabilityEntry(
            id="meowai-collab",
            type="mcp",
            enabled=True,
            source="meowai",
            mcpServer=McpServerConfig(
                command="python",
                args=["-m", "src.mcp_server.collab"],
            ),
        ),
        CapabilityEntry(
            id="meowai-memory",
            type="mcp",
            enabled=True,
            source="meowai",
            mcpServer=McpServerConfig(
                command="python",
                args=["-m", "src.mcp_server.memory"],
            ),
        ),
        CapabilityEntry(
            id="meowai-signals",
            type="mcp",
            enabled=True,
            source="meowai",
            mcpServer=McpServerConfig(
                command="python",
                args=["-m", "src.mcp_server.signals"],
            ),
        ),
    ]


def _to_capability_entry(server: McpServerDescriptor) -> CapabilityEntry:
    mcp = McpServerConfig(
        command=server.command,
        args=server.args,
        transport=server.transport,
        url=server.url,
        resolver=server.resolver,
        headers=server.headers,
        env=server.env,
        workingDir=server.workingDir,
    )
    return CapabilityEntry(
        id=server.name,
        type="mcp",
        enabled=server.enabled,
        source=server.source,
        mcpServer=mcp,
    )


def bootstrap_capabilities(project_root: str) -> CapabilitiesConfig:
    """Create initial capabilities.json from discovered external MCPs + built-ins."""
    home = Path.home()
    paths = DiscoveryPaths(
        claude_config=str(Path(project_root) / ".mcp.json"),
        codex_config=str(Path(project_root) / ".codex" / "config.toml"),
        gemini_config=str(Path(project_root) / ".gemini" / "settings.json"),
    )
    user_paths = DiscoveryPaths(
        claude_config=str(home / ".mcp.json"),
        codex_config=str(home / ".codex" / "config.toml"),
        gemini_config=str(home / ".gemini" / "settings.json"),
    )

    project_servers = discover_external_mcp_servers(paths)
    user_servers = discover_external_mcp_servers(user_paths)

    # Merge: project-level first, then user-level fillers
    seen_names = {s.name for s in project_servers}
    merged_servers = list(project_servers)
    for s in user_servers:
        if s.name not in seen_names:
            merged_servers.append(s)

    capabilities: List[CapabilityEntry] = []

    # Built-in servers
    for entry in _build_builtin_entries(project_root):
        capabilities.append(entry)

    # Discovered external servers
    builtin_names = set(BUILTIN_MEOWAI_SERVER_IDS)
    for server in merged_servers:
        if server.name in builtin_names:
            continue
        capabilities.append(_to_capability_entry(server))

    # Discovered skills
    discovered_skills = discover_skills(project_root)
    for skill_name, meta in discovered_skills.items():
        capabilities.append(
            CapabilityEntry(
                id=skill_name,
                type="skill",
                enabled=True,
                source="meowai",
                description=meta.description,
                triggers=meta.triggers,
            )
        )

    config = CapabilitiesConfig(version=1, capabilities=capabilities)
    write_capabilities_config(project_root, config)
    return config
