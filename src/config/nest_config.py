import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field, ValidationError


class NestConfig(BaseModel):
    version: int = Field(default=1, ge=1)
    project_name: str = Field(..., min_length=1)
    activated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    default_cat: str = Field(default="orange", min_length=1)
    cats: List[str] = Field(default_factory=list, min_length=1)
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {"auto_sync_claude_md": True, "collect_metrics": True}
    )


def fix_config(raw: dict, valid_cats: Dict[str, Any]) -> Tuple[dict, List[str]]:
    warnings: List[str] = []
    fixed = dict(raw)

    if "version" not in fixed or not isinstance(fixed.get("version"), int):
        fixed["version"] = 1
        warnings.append("Missing or invalid 'version'; defaulted to 1.")

    if "settings" not in fixed or not isinstance(fixed.get("settings"), dict):
        fixed["settings"] = {"auto_sync_claude_md": True, "collect_metrics": True}
        warnings.append("Missing or invalid 'settings'; defaulted to defaults.")

    cats = fixed.get("cats", [])
    if not isinstance(cats, list):
        cats = []

    original_cats = list(cats)
    filtered_cats = [c for c in original_cats if isinstance(c, str) and c in valid_cats]
    if len(filtered_cats) != len(original_cats):
        warnings.append(f"Filtered invalid cat ids from cats list.")

    if not filtered_cats:
        first_valid = list(valid_cats.keys())[0] if valid_cats else "orange"
        filtered_cats = [first_valid]
        warnings.append(f"Empty cats after filtering; defaulted to '{first_valid}'.")

    fixed["cats"] = filtered_cats

    default_cat = fixed.get("default_cat")
    if not isinstance(default_cat, str) or default_cat not in filtered_cats:
        fixed["default_cat"] = filtered_cats[0]
        warnings.append(f"Invalid default_cat; defaulted to '{filtered_cats[0]}'.")

    return fixed, warnings


def load_nest_config(
    path: Path,
    project_name: str,
    valid_cats: Dict[str, Any],
    interactive: bool = False,
) -> Tuple[NestConfig, List[str]]:
    warnings: List[str] = []

    if not path.exists():
        default = NestConfig(project_name=project_name, cats=list(valid_cats.keys())[:1] or ["orange"])
        save_nest_config(path, default)
        return default, warnings

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warnings.append(f"JSON decode error ({exc}); using default config.")
        default = NestConfig(project_name=project_name, cats=list(valid_cats.keys())[:1] or ["orange"])
        if interactive:
            save_nest_config(path, default)
        return default, warnings

    fixed, fix_warnings = fix_config(raw, valid_cats)
    warnings.extend(fix_warnings)

    fixed["project_name"] = project_name
    try:
        config = NestConfig(**fixed)
    except ValidationError as exc:
        warnings.append(f"Validation failed ({exc}); using default config.")
        default = NestConfig(project_name=project_name, cats=list(valid_cats.keys())[:1] or ["orange"])
        if interactive:
            save_nest_config(path, default)
        return default, warnings

    if interactive and fix_warnings:
        save_nest_config(path, config)

    return config, warnings


def save_nest_config(path: Path, config: NestConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
