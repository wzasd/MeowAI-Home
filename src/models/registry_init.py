import json
from pathlib import Path
from typing import Tuple

from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers import create_provider


def initialize_registries(config_path: str = "cat-config.json") -> Tuple[CatRegistry, AgentRegistry]:
    """从 cat-config.json 初始化双注册表，并 deep-merge RuntimeCatalog overlay"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    breeds = config.get("breeds", [])

    cat_reg = CatRegistry()

    # Load roster + reviewPolicy if present (V2 format)
    if "roster" in config or "reviewPolicy" in config:
        cat_reg.load_from_config(config)
    else:
        cat_reg.load_from_breeds(breeds)

    # Deep-merge runtime catalog overlay (~/.meowai/cat-catalog.json)
    _apply_runtime_overlay(cat_reg)

    # Build agent registry from cat registry
    agent_reg = AgentRegistry()
    for cat_id in cat_reg.get_all_ids():
        cat_config = cat_reg.get(cat_id)
        try:
            provider = create_provider(cat_config)
            agent_reg.register(cat_id, provider)
        except ValueError as e:
            print(f"Skipping {cat_id}: {e}")

    return cat_reg, agent_reg


def _apply_runtime_overlay(cat_reg: CatRegistry) -> None:
    """Load runtime catalog from ~/.meowai/cat-catalog.json and merge into registry."""
    from src.config.runtime_catalog import get_default_catalog_path, RuntimeCatalog

    catalog_path = get_default_catalog_path()
    if not catalog_path.exists():
        return

    try:
        catalog = RuntimeCatalog(catalog_path)
        if not catalog.list_all():
            return

        # Convert catalog entries to breeds format and load them
        for cat_data in catalog.list_all():
            cat_id = cat_data.get("id")
            if not cat_id or cat_reg.has(cat_id):
                # Update existing cat fields from overlay
                if cat_id and cat_reg.has(cat_id):
                    existing = cat_reg.get(cat_id)
                    if cat_data.get("provider"):
                        existing.provider = cat_data["provider"]
                    if cat_data.get("defaultModel"):
                        existing.default_model = cat_data["defaultModel"]
                    if cat_data.get("personality"):
                        existing.personality = cat_data["personality"]
                    if cat_data.get("displayName"):
                        existing.display_name = cat_data["displayName"]
                        existing.name = cat_data["displayName"]
                continue

            # New cat from runtime catalog — register directly
            from src.models.types import CatConfig, ContextBudget

            config = CatConfig(
                cat_id=cat_id,
                breed_id=cat_id,
                name=cat_data.get("displayName", cat_data.get("name", cat_id)),
                display_name=cat_data.get("displayName", cat_data.get("name", cat_id)),
                provider=cat_data.get("provider", ""),
                default_model=cat_data.get("defaultModel", ""),
                personality=cat_data.get("personality", ""),
                mention_patterns=cat_data.get("mentionPatterns", []),
                cli_command=cat_data.get("cli", {}).get("command", ""),
                cli_args=cat_data.get("cli", {}).get("defaultArgs", []),
                budget=ContextBudget(),
            )
            cat_reg._cats[cat_id] = config
            for pattern in config.mention_patterns:
                cat_reg._mention_index[pattern.lower().lstrip("@")] = cat_id
                cat_reg._mention_index[pattern.lower()] = cat_id

    except Exception as e:
        print(f"Warning: failed to load runtime catalog overlay: {e}")
