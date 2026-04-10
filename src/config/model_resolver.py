import os
from typing import Optional
from src.models.cat_registry import CatRegistry


def _get_env_key(cat_id: str) -> str:
    return f"CAT_{cat_id.upper().replace('-', '_')}_MODEL"


def get_cat_model(cat_id: str, registry: CatRegistry) -> str:
    env_val = os.environ.get(_get_env_key(cat_id))
    if env_val:
        return env_val
    config = registry.try_get(cat_id)
    if config and config.default_model:
        return config.default_model
    raise KeyError(f"No model found for cat: {cat_id}")
