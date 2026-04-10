import json
from pathlib import Path
from typing import Tuple

from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers import create_provider


def initialize_registries(config_path: str = "cat-config.json") -> Tuple[CatRegistry, AgentRegistry]:
    """从 cat-config.json 初始化双注册表"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    breeds = config.get("breeds", [])

    cat_reg = CatRegistry()
    cat_reg.load_from_breeds(breeds)

    agent_reg = AgentRegistry()
    for cat_id in cat_reg.get_all_ids():
        cat_config = cat_reg.get(cat_id)
        try:
            provider = create_provider(cat_config)
            agent_reg.register(cat_id, provider)
        except ValueError as e:
            print(f"Skipping {cat_id}: {e}")

    return cat_reg, agent_reg
