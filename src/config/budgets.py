import os
from typing import Optional
from src.models.types import ContextBudget
from src.models.cat_registry import CatRegistry

GLOBAL_FALLBACK_BUDGET = ContextBudget(
    max_prompt_tokens=100000, max_context_tokens=60000,
    max_messages=200, max_content_length_per_msg=10000,
)


def get_cat_budget(cat_id: str, registry: CatRegistry) -> ContextBudget:
    env_key = f"CAT_{cat_id.upper().replace('-', '_')}_MAX_PROMPT_TOKENS"
    env_val = os.environ.get(env_key)
    if env_val:
        try:
            return ContextBudget(max_prompt_tokens=int(env_val))
        except ValueError:
            pass
    config = registry.try_get(cat_id)
    if config:
        return config.budget
    return GLOBAL_FALLBACK_BUDGET
