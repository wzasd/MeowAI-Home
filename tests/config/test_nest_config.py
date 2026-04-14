import json
from pathlib import Path

import pytest

from src.config.nest_config import NestConfig, fix_config, load_nest_config, save_nest_config


def test_nest_config_defaults():
    config = NestConfig(project_name="demo", cats=["orange"])
    assert config.version == 1
    assert config.project_name == "demo"
    assert config.default_cat == "orange"
    assert config.cats == ["orange"]
    assert config.settings["auto_sync_claude_md"] is True
    assert config.settings["collect_metrics"] is True
    assert config.activated_at


def test_fix_config_invalid_default_cat():
    raw = {
        "version": 1,
        "cats": ["tabby", "siamese"],
        "default_cat": "invalid",
        "settings": {"auto_sync_claude_md": False},
    }
    valid_cats = {"tabby": {}, "siamese": {}}
    fixed, warnings = fix_config(raw, valid_cats)
    assert fixed["default_cat"] == "tabby"
    assert any("Invalid default_cat" in w for w in warnings)


def test_load_nest_config_not_exists_creates_default(tmp_path: Path):
    path = tmp_path / "nest.json"
    valid_cats = {"orange": {}}
    config, warnings = load_nest_config(path, project_name="demo", valid_cats=valid_cats)
    assert path.exists()
    assert config.project_name == "demo"
    assert config.cats == ["orange"]
    assert config.version == 1


def test_fix_config_filters_invalid_cats_and_defaults():
    raw = {"cats": ["ghost", "orange"], "default_cat": "ghost"}
    valid_cats = {"orange": {}}
    fixed, warnings = fix_config(raw, valid_cats)
    assert fixed["cats"] == ["orange"]
    assert fixed["default_cat"] == "orange"
    assert any("Filtered invalid cat ids" in w for w in warnings)
    assert any("Empty cats after filtering" not in w for w in warnings)


def test_load_nest_config_json_decode_error(tmp_path: Path):
    path = tmp_path / "nest.json"
    path.write_text("not json", encoding="utf-8")
    valid_cats = {"orange": {}}
    config, warnings = load_nest_config(path, project_name="demo", valid_cats=valid_cats)
    assert any("JSON decode error" in w for w in warnings)
    assert config.project_name == "demo"
    # non-interactive should not overwrite the bad file
    assert path.read_text(encoding="utf-8") == "not json"


def test_load_nest_config_interactive_saves_fixed(tmp_path: Path):
    path = tmp_path / "nest.json"
    raw = {"version": 1, "cats": ["ghost"], "default_cat": "ghost"}
    path.write_text(json.dumps(raw), encoding="utf-8")
    valid_cats = {"orange": {}}
    config, warnings = load_nest_config(path, project_name="demo", valid_cats=valid_cats, interactive=True)
    assert config.cats == ["orange"]
    # file should be overwritten because interactive=True and there were warnings
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["cats"] == ["orange"]


def test_load_nest_config_validation_falls_back_to_default(tmp_path: Path):
    path = tmp_path / "nest.json"
    raw = {"version": -5, "cats": [], "default_cat": "", "settings": {}}
    path.write_text(json.dumps(raw), encoding="utf-8")
    valid_cats = {"orange": {}}
    config, warnings = load_nest_config(path, project_name="demo", valid_cats=valid_cats)
    assert config.project_name == "demo"
    assert config.cats == ["orange"]
    assert any("Validation failed" in w for w in warnings)


def test_load_nest_config_empty_valid_cats(tmp_path: Path):
    path = tmp_path / "nest.json"
    raw = {"version": 1, "cats": ["ghost"], "default_cat": "ghost"}
    path.write_text(json.dumps(raw), encoding="utf-8")
    config, warnings = load_nest_config(path, project_name="demo", valid_cats={})
    assert config.cats == ["orange"]
    assert config.default_cat == "orange"
    assert any("Empty cats after filtering" in w for w in warnings)
