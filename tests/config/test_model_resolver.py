import pytest
from src.config.model_resolver import get_cat_model
from src.config.context_windows import get_context_window_size
from src.models.cat_registry import CatRegistry


@pytest.fixture
def registry():
    reg = CatRegistry()
    reg.load_from_breeds([{
        "id": "ragdoll", "catId": "opus", "name": "布偶猫",
        "displayName": "布偶猫", "mentionPatterns": ["@opus"],
        "defaultVariantId": "opus-default",
        "variants": [{
            "id": "opus-default", "catId": "opus", "provider": "anthropic",
            "defaultModel": "claude-opus-4-6",
        }],
    }])
    return reg


def test_get_model_from_registry(registry):
    model = get_cat_model("opus", registry)
    assert model == "claude-opus-4-6"


def test_get_model_env_override(registry, monkeypatch):
    monkeypatch.setenv("CAT_OPUS_MODEL", "claude-sonnet-4-6")
    model = get_cat_model("opus", registry)
    assert model == "claude-sonnet-4-6"


def test_get_model_not_found_raises(registry):
    with pytest.raises(KeyError):
        get_cat_model("nonexistent", registry)


def test_context_window_exact_match():
    assert get_context_window_size("claude-opus-4-6") == 200000


def test_context_window_prefix_match():
    assert get_context_window_size("claude-opus-4-6-20260101") == 200000


def test_context_window_unknown():
    assert get_context_window_size("unknown-model") is None


def test_context_window_gemini():
    assert get_context_window_size("gemini-3.1-pro-preview") == 1000000
