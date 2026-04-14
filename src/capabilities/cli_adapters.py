"""CLI config adapters for writing per-provider MCP configurations."""
import json
from pathlib import Path
from typing import Dict, List

from src.capabilities.models import McpServerDescriptor

try:
    import tomli_w
except ImportError:  # pragma: no cover
    tomli_w = None  # type: ignore


def _server_to_claude_dict(server: McpServerDescriptor) -> dict:
    result: dict = {
        "command": server.command,
        "args": server.args,
    }
    if server.env:
        result["env"] = server.env
    return result


def write_claude_mcp_config(path: str, servers: List[McpServerDescriptor]) -> None:
    """Write Anthropic-style .mcp.json."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "mcpServers": {
            server.name: _server_to_claude_dict(server)
            for server in servers
            if server.enabled and server.command
        }
    }
    file_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_toml_config(servers: List[McpServerDescriptor]) -> dict:
    """Build nested dict suitable for tomli_w."""
    mcp_servers: dict = {}
    for server in servers:
        if not server.enabled or not server.command:
            continue
        entry: dict = {
            "command": server.command,
            "args": server.args,
        }
        if server.env:
            entry["env"] = server.env
        mcp_servers[server.name] = entry
    return {"mcpServers": mcp_servers}


def write_codex_mcp_config(path: str, servers: List[McpServerDescriptor]) -> None:
    """Write OpenAI-style .codex/config.toml."""
    if tomli_w is None:
        raise RuntimeError("tomli-w is required to write Codex MCP config")
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    config = _build_toml_config(servers)
    with open(file_path, "wb") as f:
        tomli_w.dump(config, f)


def write_gemini_mcp_config(path: str, servers: List[McpServerDescriptor]) -> None:
    """Write Google-style .gemini/settings.json."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "mcpServers": {
            server.name: _server_to_claude_dict(server)
            for server in servers
            if server.enabled and server.command
        }
    }
    file_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
