"""Tests for GovernanceBootstrapService."""
import json
import tempfile
from pathlib import Path

import pytest

from src.governance.bootstrap import GovernanceBootstrapService, GovernanceFinding
from src.config.nest_registry import NestRegistry


class FakeCatRegistry:
    def __init__(self, cats=None):
        self._cats = cats or {"orange": object()}

    def get_all_configs(self):
        return self._cats


@pytest.fixture
def tmp_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def service(tmp_project):
    cat_reg = FakeCatRegistry()
    index_path = Path(tmp_project) / "nest-index.json"
    nest_reg = NestRegistry(index_path=index_path)
    return GovernanceBootstrapService(cat_registry=cat_reg, nest_registry=nest_reg)


class TestGovernanceBootstrapService:
    def test_bootstrap_missing_project(self, service):
        result = service.bootstrap("/nonexistent/path/xyz")
        assert result.status == "missing"
        assert result.confirmed is False
        assert any(f.rule == "existence" for f in result.findings)

    def test_bootstrap_creates_nest_config_and_capabilities(self, service, tmp_project):
        result = service.bootstrap(tmp_project)
        assert result.status in ("healthy", "stale")
        assert result.confirmed is True

        neowai = Path(tmp_project) / ".neowai"
        assert neowai.exists()
        assert (neowai / "config.json").exists()
        assert (neowai / "capabilities.json").exists()

    def test_bootstrap_registers_in_nest_index(self, service, tmp_project):
        service.bootstrap(tmp_project)
        assert service.nest_registry.is_registered(tmp_project)

    def test_bootstrap_preserves_existing_capabilities(self, service, tmp_project):
        neowai = Path(tmp_project) / ".neowai"
        neowai.mkdir(parents=True)
        caps = {"version": 1, "capabilities": [{"id": "custom", "type": "mcp", "enabled": True, "source": "test"}]}
        (neowai / "capabilities.json").write_text(json.dumps(caps), encoding="utf-8")

        result = service.bootstrap(tmp_project)
        assert result.confirmed is True
        saved = json.loads((neowai / "capabilities.json").read_text(encoding="utf-8"))
        assert any(c["id"] == "custom" for c in saved["capabilities"])

    def test_health_check_missing_project(self, service):
        result = service.health_check("/nonexistent/path/xyz")
        assert result.status == "missing"

    def test_health_check_existing_project(self, service, tmp_project):
        service.bootstrap(tmp_project)
        result = service.health_check(tmp_project)
        assert result.status in ("healthy", "stale")
        assert any(f.rule == "capabilities" for f in result.findings)

    def test_bootstrap_findings_include_nest_info(self, service, tmp_project):
        result = service.bootstrap(tmp_project)
        assert any(f.rule == "nest-registry" and f.severity == "info" for f in result.findings)
        assert any(f.rule == "capabilities" for f in result.findings)
