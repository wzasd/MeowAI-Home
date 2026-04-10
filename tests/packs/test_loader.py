"""Pack loader tests"""
import pytest
import tempfile
from pathlib import Path
from src.packs.loader import PackLoader


@pytest.fixture
def loader():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield PackLoader(tmpdir)


class TestPackLoaderLoad:
    def test_load_valid_yaml(self, loader):
        # Create a test pack file
        pack_content = """
name: tdd-pack
display_name: TDD Development Team
description: Test-driven development team
agents:
  - cat_id: tester
    breed: siamese
    role: Test Engineer
  - cat_id: implementer
    breed: maine_coon
    role: Implementer
skills:
  - tdd
  - debugging
workflow: tdd
"""
        pack_path = Path(loader.packs_dir) / "tdd-pack.yaml"
        pack_path.write_text(pack_content)

        pack = loader.load("tdd-pack")
        assert pack is not None
        assert pack["name"] == "tdd-pack"
        assert pack["display_name"] == "TDD Development Team"
        assert len(pack["agents"]) == 2

    def test_load_missing_returns_none(self, loader):
        pack = loader.load("nonexistent")
        assert pack is None

    def test_load_invalid_yaml_raises(self, loader):
        pack_path = Path(loader.packs_dir) / "bad.yaml"
        pack_path.write_text("invalid: yaml: content: [")
        with pytest.raises(Exception):
            loader.load("bad")


class TestPackLoaderList:
    def test_list_empty_directory(self, loader):
        assert loader.list_packs() == []

    def test_list_returns_yaml_files(self, loader):
        (Path(loader.packs_dir) / "pack1.yaml").write_text("name: p1")
        (Path(loader.packs_dir) / "pack2.yaml").write_text("name: p2")
        (Path(loader.packs_dir) / "readme.txt").write_text("not a pack")

        packs = loader.list_packs()
        assert sorted(packs) == ["pack1", "pack2"]


class TestPackLoaderValidate:
    def test_valid_pack_no_errors(self, loader):
        pack = {
            "name": "test-pack",
            "display_name": "Test Pack",
            "agents": [
                {"cat_id": "a1", "breed": "ragdoll"},
            ],
        }
        errors = loader.validate(pack)
        assert errors == []

    def test_missing_name(self, loader):
        pack = {"display_name": "Test", "agents": []}
        errors = loader.validate(pack)
        assert "Missing required field: name" in errors

    def test_missing_display_name(self, loader):
        pack = {"name": "test", "agents": []}
        errors = loader.validate(pack)
        assert "Missing required field: display_name" in errors

    def test_missing_agents(self, loader):
        pack = {"name": "test", "display_name": "Test"}
        errors = loader.validate(pack)
        assert "Missing required field: agents" in errors

    def test_agents_not_list(self, loader):
        pack = {"name": "test", "display_name": "Test", "agents": "not a list"}
        errors = loader.validate(pack)
        assert "agents must be a list" in errors

    def test_empty_agents(self, loader):
        pack = {"name": "test", "display_name": "Test", "agents": []}
        errors = loader.validate(pack)
        assert "agents list cannot be empty" in errors

    def test_agent_missing_cat_id(self, loader):
        pack = {"name": "test", "display_name": "Test", "agents": [{"breed": "x"}]}
        errors = loader.validate(pack)
        assert "agent[0] missing cat_id" in errors

    def test_agent_missing_breed(self, loader):
        pack = {"name": "test", "display_name": "Test", "agents": [{"cat_id": "x"}]}
        errors = loader.validate(pack)
        assert "agent[0] missing breed" in errors
