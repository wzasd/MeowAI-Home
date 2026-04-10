import pytest
from src.config.budgets import get_cat_budget, GLOBAL_FALLBACK_BUDGET
from src.models.cat_registry import CatRegistry


@pytest.fixture
def registry_with_budgets():
    reg = CatRegistry()
    reg.load_from_breeds([{
        "id": "ragdoll", "catId": "opus", "name": "布偶猫", "displayName": "布偶猫",
        "mentionPatterns": ["@opus"], "defaultVariantId": "opus-default",
        "variants": [{
            "id": "opus-default", "catId": "opus", "provider": "anthropic",
            "defaultModel": "claude-opus-4-6",
            "contextBudget": {"maxPromptTokens": 180000, "maxContextTokens": 160000, "maxMessages": 200, "maxContentLengthPerMsg": 10000},
        }],
    }])
    return reg


def test_get_cat_budget_from_registry(registry_with_budgets):
    budget = get_cat_budget("opus", registry_with_budgets)
    assert budget.max_prompt_tokens == 180000


def test_get_cat_budget_fallback():
    budget = get_cat_budget("unknown", CatRegistry())
    assert budget.max_prompt_tokens == GLOBAL_FALLBACK_BUDGET.max_prompt_tokens


def test_env_override(registry_with_budgets, monkeypatch):
    monkeypatch.setenv("CAT_OPUS_MAX_PROMPT_TOKENS", "999")
    assert get_cat_budget("opus", registry_with_budgets).max_prompt_tokens == 999
