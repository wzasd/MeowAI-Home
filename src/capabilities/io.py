"""Atomic read/write for .neowai/capabilities.json."""
import json
from pathlib import Path
from typing import Optional

from src.capabilities.models import CapabilitiesConfig


CAPABILITIES_FILENAME = "capabilities.json"
NEOWAI_DIR = ".neowai"


def _safe_path(project_root: str) -> Path:
    root = Path(project_root).resolve()
    file_path = root / NEOWAI_DIR / CAPABILITIES_FILENAME
    # Ensure the resolved file path stays within project root
    try:
        file_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes project root: {file_path}") from exc
    return file_path


def read_capabilities_config(project_root: str) -> Optional[CapabilitiesConfig]:
    """Read capabilities.json if it exists and is valid."""
    file_path = _safe_path(project_root)
    if not file_path.exists():
        return None
    try:
        raw = file_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return CapabilitiesConfig.model_validate(data)
    except Exception:
        return None


def write_capabilities_config(project_root: str, config: CapabilitiesConfig) -> None:
    """Write capabilities.json, creating .neowai directory if needed."""
    file_path = _safe_path(project_root)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(config.model_dump(exclude_none=True), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
