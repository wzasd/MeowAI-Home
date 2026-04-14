"""Discover external MCP servers and skills from filesystem."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.capabilities.models import McpServerDescriptor


try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib

import yaml


class DiscoveryPaths:
    """Paths to CLI config files for MCP discovery."""

    def __init__(
        self,
        claude_config: str,
        codex_config: str,
        gemini_config: str,
    ):
        self.claude_config = claude_config
        self.codex_config = codex_config
        self.gemini_config = gemini_config


def _has_usable_transport(desc: McpServerDescriptor) -> bool:
    if desc.transport == "streamableHttp":
        return bool(desc.url and desc.url.strip())
    if desc.resolver:
        return bool(desc.resolver.strip())
    return bool(desc.command and desc.command.strip())


def _read_json(path: str) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_toml(path: str) -> dict:
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _parse_claude_mcp_config(path: str) -> List[McpServerDescriptor]:
    data = _read_json(path)
    servers: List[McpServerDescriptor] = []
    for name, cfg in data.get("mcpServers", {}).items():
        if not isinstance(cfg, dict):
            continue
        desc = McpServerDescriptor(
            name=name,
            command=cfg.get("command"),
            args=cfg.get("args", []),
            enabled=cfg.get("enabled", True),
            source="external",
            env=cfg.get("env"),
        )
        if _has_usable_transport(desc):
            servers.append(desc)
    return servers


def _parse_codex_mcp_config(path: str) -> List[McpServerDescriptor]:
    data = _read_toml(path)
    servers: List[McpServerDescriptor] = []
    for name, cfg in data.get("mcpServers", {}).items():
        if not isinstance(cfg, dict):
            continue
        desc = McpServerDescriptor(
            name=name,
            command=cfg.get("command"),
            args=cfg.get("args", []),
            enabled=cfg.get("enabled", True),
            source="external",
            env=cfg.get("env"),
        )
        if _has_usable_transport(desc):
            servers.append(desc)
    return servers


def _parse_gemini_mcp_config(path: str) -> List[McpServerDescriptor]:
    data = _read_json(path)
    servers: List[McpServerDescriptor] = []
    for name, cfg in data.get("mcpServers", {}).items():
        if not isinstance(cfg, dict):
            continue
        desc = McpServerDescriptor(
            name=name,
            command=cfg.get("command"),
            args=cfg.get("args", []),
            enabled=cfg.get("enabled", True),
            source="external",
            env=cfg.get("env"),
        )
        if _has_usable_transport(desc):
            servers.append(desc)
    return servers


def deduplicate_discovered_mcp_servers(
    servers: List[McpServerDescriptor],
) -> List[McpServerDescriptor]:
    """Merge by name; if same name appears multiple times, first wins."""
    seen: Dict[str, McpServerDescriptor] = {}
    for server in servers:
        if server.name not in seen:
            seen[server.name] = server
    return list(seen.values())


def discover_external_mcp_servers(paths: DiscoveryPaths) -> List[McpServerDescriptor]:
    """Discover MCP servers from Anthropic, OpenAI, and Google CLI configs."""
    discovered = [
        *_parse_claude_mcp_config(paths.claude_config),
        *_parse_codex_mcp_config(paths.codex_config),
        *_parse_gemini_mcp_config(paths.gemini_config),
    ]
    return deduplicate_discovered_mcp_servers(discovered)


# ── Skill Discovery ──


@dataclass
class SkillMeta:
    """Metadata extracted from a skill directory."""

    name: str
    description: Optional[str] = None
    triggers: List[str] = field(default_factory=list)


def _list_skill_subdirs(skills_dir: Path) -> List[str]:
    """Return subdirectory names that contain a readable SKILL.md."""
    if not skills_dir.exists():
        return []
    names: List[str] = []
    for entry in skills_dir.iterdir():
        if entry.is_dir() and (entry / "SKILL.md").is_file():
            names.append(entry.name)
    return names


def read_skill_meta(skill_dir: str) -> SkillMeta:
    """Extract description + triggers from a SKILL.md frontmatter."""
    skill_md = Path(skill_dir) / "SKILL.md"
    name = Path(skill_dir).name
    if not skill_md.exists():
        return SkillMeta(name=name)
    try:
        content = skill_md.read_text(encoding="utf-8")
        match = re.match(r"^---\n([\s\S]*?)\n---", content)
        if not match:
            return SkillMeta(name=name)
        fm = yaml.safe_load(match.group(1)) or {}
        desc = fm.get("description")
        if isinstance(desc, str):
            desc = desc.strip()
        triggers = fm.get("triggers", [])
        if not isinstance(triggers, list):
            triggers = []
        triggers = [str(t).strip() for t in triggers if str(t).strip()]
        return SkillMeta(
            name=name,
            description=desc,
            triggers=triggers,
        )
    except Exception:
        return SkillMeta(name=name)


def read_manifest_meta(manifest_path: str) -> Dict[str, SkillMeta]:
    """Parse skills/manifest.yaml and extract skill descriptions/triggers."""
    result: Dict[str, SkillMeta] = {}
    try:
        content = Path(manifest_path).read_text(encoding="utf-8")
        parsed = yaml.safe_load(content) or {}
        skills = parsed.get("skills", {})
        if not isinstance(skills, dict):
            return result
        for skill_name, meta in skills.items():
            if not isinstance(meta, dict):
                continue
            desc = meta.get("description")
            if isinstance(desc, str):
                desc = desc.strip()
            triggers = meta.get("triggers", [])
            if not isinstance(triggers, list):
                triggers = []
            triggers = [str(t).strip() for t in triggers if str(t).strip()]
            result[str(skill_name)] = SkillMeta(
                name=str(skill_name),
                description=desc,
                triggers=triggers,
            )
    except Exception:
        pass
    return result


def discover_skills(project_root: str) -> Dict[str, SkillMeta]:
    """Discover skills from the project-level skills/ directory."""
    skills_dir = Path(project_root) / "skills"
    if not skills_dir.exists():
        return {}

    skill_names = _list_skill_subdirs(skills_dir)
    manifest_path = str(skills_dir / "manifest.yaml")
    manifest_meta = read_manifest_meta(manifest_path)

    result: Dict[str, SkillMeta] = {}
    for name in skill_names:
        meta = read_skill_meta(str(skills_dir / name))
        # Manifest overrides SKILL.md if present
        if name in manifest_meta:
            manifest = manifest_meta[name]
            meta.description = manifest.description or meta.description
            meta.triggers = manifest.triggers or meta.triggers
        result[name] = meta

    return result
