"""Tests for the capability orchestrator."""
import json
import tempfile
from pathlib import Path

import pytest

from src.capabilities.io import read_capabilities_config, write_capabilities_config
from src.capabilities.bootstrap import bootstrap_capabilities, BUILTIN_MEOWAI_SERVER_IDS
from src.capabilities.discovery import (
    DiscoveryPaths,
    discover_external_mcp_servers,
    discover_skills,
    read_skill_meta,
    read_manifest_meta,
    SkillMeta,
)
from src.capabilities.resolver import resolve_servers_for_cat
from src.capabilities.cli_adapters import (
    write_claude_mcp_config,
    write_gemini_mcp_config,
)
from src.capabilities.orchestrator import (
    get_or_bootstrap,
    toggle_capability,
    regenerate_cli_configs,
    sync_skills,
    build_board_response,
)
from src.capabilities.models import (
    CapabilitiesConfig,
    CapabilityEntry,
    McpServerConfig,
    McpServerDescriptor,
    CatOverride,
)
from src.models.cat_registry import cat_registry


@pytest.fixture(autouse=True)
def reset_registry():
    cat_registry.reset()
    yield
    cat_registry.reset()


@pytest.fixture
def sample_breeds():
    return [
        {
            "id": "orange",
            "name": "橘猫",
            "displayName": "阿橘",
            "default": True,
            "provider": "anthropic",
            "defaultModel": "claude-opus-4-6",
            "capabilities": ["code_gen"],
            "permissions": ["write_file"],
            "cli": {"command": "claude", "defaultArgs": ["--output-format", "stream-json"]},
        }
    ]


class TestIo:
    def test_read_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(
                version=1,
                capabilities=[
                    CapabilityEntry(id="test-mcp", type="mcp", enabled=True, source="meowai")
                ],
            )
            write_capabilities_config(tmpdir, config)
            loaded = read_capabilities_config(tmpdir)
            assert loaded is not None
            assert loaded.version == 1
            assert len(loaded.capabilities) == 1
            assert loaded.capabilities[0].id == "test-mcp"

    def test_read_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert read_capabilities_config(tmpdir) is None


class TestDiscovery:
    def test_discover_from_claude_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_path = Path(tmpdir) / ".mcp.json"
            mcp_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "filesystem": {
                            "command": "node",
                            "args": ["/fs.js"],
                            "env": {"KEY": "val"}
                        }
                    }
                }),
                encoding="utf-8",
            )
            paths = DiscoveryPaths(
                claude_config=str(mcp_path),
                codex_config=str(Path(tmpdir) / ".codex" / "config.toml"),
                gemini_config=str(Path(tmpdir) / ".gemini" / "settings.json"),
            )
            servers = discover_external_mcp_servers(paths)
            assert len(servers) == 1
            assert servers[0].name == "filesystem"
            assert servers[0].command == "node"
            assert servers[0].args == ["/fs.js"]

    def test_deduplicate_by_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mcp_path = Path(tmpdir) / ".mcp.json"
            mcp_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "fs": {"command": "node", "args": ["a.js"]}
                    }
                }),
                encoding="utf-8",
            )
            gemini_path = Path(tmpdir) / ".gemini" / "settings.json"
            gemini_path.parent.mkdir(parents=True, exist_ok=True)
            gemini_path.write_text(
                json.dumps({
                    "mcpServers": {
                        "fs": {"command": "python", "args": ["b.py"]}
                    }
                }),
                encoding="utf-8",
            )
            paths = DiscoveryPaths(
                claude_config=str(mcp_path),
                codex_config=str(Path(tmpdir) / ".codex" / "config.toml"),
                gemini_config=str(gemini_path),
            )
            servers = discover_external_mcp_servers(paths)
            assert len(servers) == 1
            assert servers[0].command == "node"  # first wins


class TestBootstrap:
    def test_bootstrap_creates_version_1_with_builtins(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = bootstrap_capabilities(tmpdir)
            assert config.version == 1
            ids = {c.id for c in config.capabilities}
            for builtin in BUILTIN_MEOWAI_SERVER_IDS:
                assert builtin in ids
            # Verify file was written
            assert (Path(tmpdir) / ".neowai" / "capabilities.json").exists()


class TestResolver:
    def test_resolve_applies_global_enabled(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        config = CapabilitiesConfig(
            capabilities=[
                CapabilityEntry(
                    id="fs",
                    type="mcp",
                    enabled=False,
                    source="external",
                    mcpServer=McpServerConfig(command="node", args=["fs.js"]),
                )
            ]
        )
        servers = resolve_servers_for_cat(config, "orange")
        assert len(servers) == 1
        assert servers[0].enabled is False

    def test_resolve_applies_per_cat_override(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        config = CapabilitiesConfig(
            capabilities=[
                CapabilityEntry(
                    id="fs",
                    type="mcp",
                    enabled=True,
                    source="external",
                    mcpServer=McpServerConfig(command="node", args=["fs.js"]),
                    overrides=[CatOverride(catId="orange", enabled=False)],
                )
            ]
        )
        servers = resolve_servers_for_cat(config, "orange")
        assert len(servers) == 1
        assert servers[0].enabled is False

    def test_resolve_filters_incompatible_transport(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        config = CapabilitiesConfig(
            capabilities=[
                CapabilityEntry(
                    id="remote",
                    type="mcp",
                    enabled=True,
                    source="external",
                    mcpServer=McpServerConfig(
                        transport="streamableHttp", url="http://example.com"
                    ),
                )
            ]
        )
        # anthropic provider supports streamableHttp
        servers = resolve_servers_for_cat(config, "orange")
        assert len(servers) == 1
        assert servers[0].enabled is True

        # Change cat to openai
        cat_registry.reset()
        cat_registry.load_from_breeds([
            {
                "id": "codex",
                "name": "Codex",
                "displayName": "Codex",
                "provider": "openai",
                "defaultModel": "gpt-4o",
                "capabilities": [],
                "permissions": [],
                "cli": {"command": "codex", "defaultArgs": []},
            }
        ])
        servers = resolve_servers_for_cat(config, "codex")
        assert len(servers) == 1
        assert servers[0].enabled is False


class TestCliAdapters:
    def test_write_claude_mcp_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / ".mcp.json")
            servers = [
                McpServerDescriptor(name="fs", command="node", args=["fs.js"], enabled=True, source="external"),
                McpServerDescriptor(name="disabled", command="node", args=["x.js"], enabled=False, source="external"),
            ]
            write_claude_mcp_config(path, servers)
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            assert "fs" in data["mcpServers"]
            assert "disabled" not in data["mcpServers"]
            assert data["mcpServers"]["fs"]["command"] == "node"

    def test_write_gemini_mcp_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / ".gemini" / "settings.json")
            servers = [
                McpServerDescriptor(name="fs", command="node", args=["fs.js"], enabled=True, source="external"),
            ]
            write_gemini_mcp_config(path, servers)
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            assert "fs" in data["mcpServers"]


class TestOrchestrator:
    def test_get_or_bootstrap_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(version=1, capabilities=[])
            write_capabilities_config(tmpdir, config)
            result = get_or_bootstrap(tmpdir)
            assert result.version == 1

    def test_get_or_bootstrap_creates_new(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_or_bootstrap(tmpdir)
            assert result.version == 1
            assert any(c.id == "meowai-collab" for c in result.capabilities)

    def test_toggle_global(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(
                capabilities=[
                    CapabilityEntry(id="fs", type="mcp", enabled=True, source="external")
                ]
            )
            write_capabilities_config(tmpdir, config)
            cap = toggle_capability(tmpdir, config, "fs", "mcp", "global", False)
            assert cap.enabled is False
            reloaded = read_capabilities_config(tmpdir)
            assert reloaded is not None
            assert reloaded.capabilities[0].enabled is False

    def test_toggle_per_cat(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(
                capabilities=[
                    CapabilityEntry(id="fs", type="mcp", enabled=True, source="external")
                ]
            )
            write_capabilities_config(tmpdir, config)
            cap = toggle_capability(tmpdir, config, "fs", "mcp", "cat", False, cat_id="orange")
            assert any(o.catId == "orange" and o.enabled is False for o in cap.overrides)
            assert len(cap.overrides) == 1

    def test_regenerate_cli_configs(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(
                capabilities=[
                    CapabilityEntry(
                        id="fs",
                        type="mcp",
                        enabled=True,
                        source="external",
                        mcpServer=McpServerConfig(command="node", args=["fs.js"]),
                    )
                ]
            )
            write_capabilities_config(tmpdir, config)
            regenerate_cli_configs(tmpdir, config)
            assert (Path(tmpdir) / ".mcp.json").exists()


class TestSkillDiscovery:
    def test_discover_skills_reads_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills" / "foo"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\n"
                "name: foo\n"
                "description: A test skill\n"
                "triggers:\n  - new feature\n  - 立项\n"
                "---\n"
                "# Foo Skill\n",
                encoding="utf-8",
            )
            discovered = discover_skills(tmpdir)
            assert "foo" in discovered
            assert discovered["foo"].description == "A test skill"
            assert discovered["foo"].triggers == ["new feature", "立项"]

    def test_discover_skills_uses_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills" / "bar"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\n"
                "name: bar\n"
                "description: From skill md\n"
                "triggers:\n  - a\n"
                "---\n",
                encoding="utf-8",
            )
            (Path(tmpdir) / "skills" / "manifest.yaml").write_text(
                "skills:\n"
                "  bar:\n"
                "    description: From manifest\n"
                "    triggers:\n      - b\n      - c\n",
                encoding="utf-8",
            )
            discovered = discover_skills(tmpdir)
            assert discovered["bar"].description == "From manifest"
            assert discovered["bar"].triggers == ["b", "c"]

    def test_read_skill_meta_no_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "baz"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# No frontmatter\n", encoding="utf-8")
            meta = read_skill_meta(str(skill_dir))
            assert meta.name == "baz"
            assert meta.description is None
            assert meta.triggers == []

    def test_read_manifest_meta_invalid_skills_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "manifest.yaml"
            manifest.write_text("skills: not_a_dict\n", encoding="utf-8")
            result = read_manifest_meta(str(manifest))
            assert result == {}


class TestSkillSync:
    def test_sync_skills_adds_new(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills" / "foo"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\ndescription: Foo skill\ntriggers:\n  - foo\n---\n",
                encoding="utf-8",
            )
            config = CapabilitiesConfig(version=1, capabilities=[])
            dirty = sync_skills(tmpdir, config)
            assert dirty is True
            assert any(c.id == "foo" and c.type == "skill" for c in config.capabilities)

    def test_sync_skills_updates_meta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills" / "bar"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\ndescription: Updated desc\ntriggers:\n  - updated\n---\n",
                encoding="utf-8",
            )
            config = CapabilitiesConfig(
                version=1,
                capabilities=[
                    CapabilityEntry(
                        id="bar",
                        type="skill",
                        enabled=False,
                        source="meowai",
                        description="Old desc",
                        triggers=["old"],
                    )
                ],
            )
            dirty = sync_skills(tmpdir, config)
            assert dirty is True
            bar = next(c for c in config.capabilities if c.id == "bar")
            assert bar.description == "Updated desc"
            assert bar.triggers == ["updated"]
            assert bar.enabled is False  # preserved

    def test_sync_skills_prunes_stale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # No skills directory
            config = CapabilitiesConfig(
                version=1,
                capabilities=[
                    CapabilityEntry(id="gone", type="skill", enabled=True, source="meowai")
                ],
            )
            dirty = sync_skills(tmpdir, config)
            assert dirty is True
            assert not any(c.id == "gone" for c in config.capabilities)

    def test_sync_skills_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills" / "stable"
            skills_dir.mkdir(parents=True)
            (skills_dir / "SKILL.md").write_text(
                "---\ndescription: Stable\n---\n",
                encoding="utf-8",
            )
            config = CapabilitiesConfig(
                version=1,
                capabilities=[
                    CapabilityEntry(
                        id="stable",
                        type="skill",
                        enabled=True,
                        source="meowai",
                        description="Stable",
                    )
                ],
            )
            dirty = sync_skills(tmpdir, config)
            assert dirty is False


class TestBoardResponse:
    def test_capability_board_includes_triggers(self, sample_breeds):
        cat_registry.load_from_breeds(sample_breeds)
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CapabilitiesConfig(
                version=1,
                capabilities=[
                    CapabilityEntry(
                        id="design",
                        type="skill",
                        enabled=True,
                        source="meowai",
                        description="Design skill",
                        triggers=["design", "design system"],
                    )
                ],
            )
            response = build_board_response(tmpdir, config)
            item = next(i for i in response.items if i.id == "design")
            assert item.triggers == ["design", "design system"]
            assert item.description == "Design skill"
