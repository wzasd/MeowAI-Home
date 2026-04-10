import pytest
from src.models.registry_init import initialize_registries


def test_initialize_with_real_config():
    cat_reg, agent_reg = initialize_registries("cat-config.json")
    assert cat_reg.has("opus")
    assert cat_reg.has("sonnet")
    assert cat_reg.has("codex")
    assert cat_reg.has("gemini")
    assert agent_reg.has("opus")
    from src.providers.claude_provider import ClaudeProvider
    assert isinstance(agent_reg.get("opus"), ClaudeProvider)
    from src.providers.codex_provider import CodexProvider
    assert isinstance(agent_reg.get("codex"), CodexProvider)


def test_initialize_default_cat():
    cat_reg, _ = initialize_registries("cat-config.json")
    default_id = cat_reg.get_default_id()
    assert default_id is not None
    assert cat_reg.has(default_id)


def test_initialize_file_not_found():
    with pytest.raises(FileNotFoundError):
        initialize_registries("nonexistent.json")
