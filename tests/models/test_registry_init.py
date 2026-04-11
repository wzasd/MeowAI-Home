import pytest
from src.models.registry_init import initialize_registries


def test_initialize_with_real_config():
    cat_reg, agent_reg = initialize_registries("cat-config.json")
    # 用户的猫配置: 阿橘(orange), 墨点(inky), 花花(patch)
    assert cat_reg.has("orange")
    assert cat_reg.has("inky")
    assert cat_reg.has("patch")
    assert agent_reg.has("orange")
    from src.providers.claude_provider import ClaudeProvider
    assert isinstance(agent_reg.get("orange"), ClaudeProvider)
    assert isinstance(agent_reg.get("inky"), ClaudeProvider)


def test_initialize_default_cat():
    cat_reg, _ = initialize_registries("cat-config.json")
    default_id = cat_reg.get_default_id()
    assert default_id is not None
    assert cat_reg.has(default_id)


def test_initialize_file_not_found():
    with pytest.raises(FileNotFoundError):
        initialize_registries("nonexistent.json")
