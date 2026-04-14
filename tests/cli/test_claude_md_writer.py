from pathlib import Path

from src.cli.claude_md_writer import (
    NEOWAI_END,
    NEOWAI_START,
    read_neowai_block,
    write_neowai_block,
)


def test_append_to_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    write_neowai_block(target, "Hello cats")
    text = target.read_text(encoding="utf-8")
    assert NEOWAI_START in text
    assert NEOWAI_END in text
    assert "Hello cats" in text


def test_replace_existing_block(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "prefix\n"
        + NEOWAI_START
        + "\nOld block\n"
        + NEOWAI_END
        + "\nsuffix\n",
        encoding="utf-8",
    )
    write_neowai_block(target, "New block")
    text = target.read_text(encoding="utf-8")
    assert "prefix" in text
    assert "suffix" in text
    assert "New block" in text
    assert "Old block" not in text


def test_read_block(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "\n"
        + NEOWAI_START
        + "\n  Meow  \n"
        + NEOWAI_END
        + "\n",
        encoding="utf-8",
    )
    block = read_neowai_block(target)
    assert block == NEOWAI_START + "\n  Meow  \n" + NEOWAI_END


def test_read_missing_file_returns_empty(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    assert read_neowai_block(target) == ""


def test_append_to_non_empty_file_without_block(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("Existing content\n", encoding="utf-8")
    write_neowai_block(target, "Hello cats")
    text = target.read_text(encoding="utf-8")
    assert "Existing content" in text
    assert NEOWAI_START in text
    assert NEOWAI_END in text
    assert "Hello cats" in text


def test_write_empty_block_content(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    write_neowai_block(target, "")
    text = target.read_text(encoding="utf-8")
    assert NEOWAI_START in text
    assert NEOWAI_END in text


def test_backup_created_on_write(tmp_path: Path) -> None:
    target = tmp_path / "CLAUDE.md"
    target.write_text("Original content\n", encoding="utf-8")
    write_neowai_block(target, "Hello cats")
    bak = target.with_suffix(target.suffix + ".bak")
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == "Original content\n"
