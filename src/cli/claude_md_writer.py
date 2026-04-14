import re
import shutil
from pathlib import Path

NEOWAI_START = "<!-- NEOWAI-CATS-START -->"
NEOWAI_END = "<!-- NEOWAI-CATS-END -->"

_BLOCK_PATTERN = re.compile(
    re.escape(NEOWAI_START) + r".*?" + re.escape(NEOWAI_END),
    re.DOTALL,
)


def read_neowai_block(path: Path) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8")
    match = _BLOCK_PATTERN.search(content)
    if not match:
        return ""
    return match.group(0).strip()


def write_neowai_block(path: Path, block_content: str) -> None:
    new_block = f"{NEOWAI_START}\n{block_content}\n{NEOWAI_END}"

    if not path.exists():
        path.write_text(new_block + "\n", encoding="utf-8")
        return

    original_content = path.read_text(encoding="utf-8")
    bak_path = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak_path)

    if _BLOCK_PATTERN.search(original_content):
        new_content = re.sub(_BLOCK_PATTERN, new_block, original_content)
    else:
        separator = "\n\n" if original_content and not original_content.endswith("\n") else "\n"
        if original_content.endswith("\n"):
            separator = ""
        new_content = original_content + separator + new_block + "\n"

    path.write_text(new_content, encoding="utf-8")
