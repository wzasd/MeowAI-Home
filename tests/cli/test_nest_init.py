import json
import os
from pathlib import Path

from src.cli.nest_init import run_nest_init


def test_run_nest_init_creates_nest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "src.cli.nest_init.CatRegistry",
        lambda: type(
            "MockReg",
            (),
            {
                "get_all_ids": lambda self: ["orange"],
                "get": lambda self, cid: type(
                    "Obj",
                    (),
                    {
                        "cat_id": "orange",
                        "name": "阿橘",
                        "personality": "活泼",
                        "role_description": "dev",
                        "capabilities": ["chat"],
                        "permissions": [],
                    },
                )(),
            },
        )(),
    )
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        run_nest_init(interactive=False)
        assert (tmp_path / ".neowai" / "config.json").exists()
        assert (tmp_path / "CLAUDE.md").exists()

        config = json.loads((tmp_path / ".neowai" / "config.json").read_text(encoding="utf-8"))
        assert config["project_name"] == tmp_path.name
        assert config["cats"] == ["orange"]
        assert config["default_cat"] == "orange"

        claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "<!-- NEOWAI-CATS-START -->" in claude_md
        assert "<!-- NEOWAI-CATS-END -->" in claude_md
        assert "阿橘" in claude_md
        assert "dev" in claude_md
        assert "活泼" in claude_md
        assert "chat" in claude_md

        from src.config.nest_registry import NestRegistry
        registry = NestRegistry()
        assert registry.is_registered(str(tmp_path))
    finally:
        os.chdir(old_cwd)


def test_run_nest_init_already_initialized_shows_status(tmp_path: Path, monkeypatch, capfd) -> None:
    monkeypatch.setattr(
        "src.cli.nest_init.CatRegistry",
        lambda: type(
            "MockReg",
            (),
            {
                "get_all_ids": lambda self: ["orange"],
                "get": lambda self, cid: type(
                    "Obj",
                    (),
                    {
                        "cat_id": "orange",
                        "name": "阿橘",
                        "personality": "活泼",
                        "role_description": "dev",
                        "capabilities": ["chat"],
                        "permissions": [],
                    },
                )(),
            },
        )(),
    )
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        run_nest_init(interactive=False)
        assert (tmp_path / ".neowai" / "config.json").exists()

        run_nest_init(interactive=False)
        captured = capfd.readouterr()
        assert "项目已激活" in captured.out
        assert "阿橘" not in captured.out  # status display doesn't print cat details
    finally:
        os.chdir(old_cwd)


def test_run_nest_init_no_valid_cats(tmp_path: Path, monkeypatch, capfd) -> None:
    monkeypatch.setattr(
        "src.cli.nest_init.CatRegistry",
        lambda: type(
            "MockReg",
            (),
            {
                "get_all_ids": lambda self: [],
            },
        )(),
    )
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        run_nest_init(interactive=False)
        captured = capfd.readouterr()
        assert "没有可用的 cat-config.json" in captured.out
        assert not (tmp_path / ".neowai" / "config.json").exists()
    finally:
        os.chdir(old_cwd)
