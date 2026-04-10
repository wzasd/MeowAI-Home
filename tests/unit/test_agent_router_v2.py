import pytest
from src.router.agent_router_v2 import AgentRouterV2
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.providers import create_provider


@pytest.fixture
def setup_registries():
    cat_reg = CatRegistry()
    cat_reg.load_from_breeds([
        {
            "id": "ragdoll", "catId": "opus", "name": "布偶猫",
            "displayName": "布偶猫", "mentionPatterns": ["@opus", "@布偶猫", "@宪宪"],
            "defaultVariantId": "opus-default",
            "variants": [{
                "id": "opus-default", "catId": "opus", "provider": "anthropic",
                "defaultModel": "claude-opus-4-6", "personality": "温柔",
                "cli": {"command": "claude", "defaultArgs": []},
            }],
        },
        {
            "id": "maine-coon", "catId": "codex", "name": "缅因猫",
            "displayName": "缅因猫", "mentionPatterns": ["@codex", "@缅因猫", "@砚砚"],
            "defaultVariantId": "codex-default",
            "variants": [{
                "id": "codex-default", "catId": "codex", "provider": "openai",
                "defaultModel": "gpt-5.3-codex", "personality": "严谨",
                "cli": {"command": "codex", "defaultArgs": []},
            }],
        },
    ])
    cat_reg.set_default("opus")
    agent_reg = AgentRegistry()
    for cid in cat_reg.get_all_ids():
        config = cat_reg.get(cid)
        try:
            agent_reg.register(cid, create_provider(config))
        except ValueError:
            pass
    return cat_reg, agent_reg


def test_parse_single_mention(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    targets = router.resolve_targets("@opus 帮我写代码")
    assert targets == ["opus"]

def test_parse_multiple_mentions(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    targets = router.resolve_targets("@opus @codex review this")
    assert "opus" in targets
    assert "codex" in targets

def test_parse_chinese_mention(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    targets = router.resolve_targets("@布偶猫 写代码")
    assert targets == ["opus"]

def test_no_mention_falls_to_default(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    targets = router.resolve_targets("随便聊聊")
    assert targets == ["opus"]

def test_unknown_mention_falls_to_default(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    targets = router.resolve_targets("@nonexistent 写代码")
    assert targets == ["opus"]

def test_get_service(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    service = router.get_service("opus")
    from src.providers.claude_provider import ClaudeProvider
    assert isinstance(service, ClaudeProvider)

def test_route_message_compat(setup_registries):
    cat_reg, agent_reg = setup_registries
    router = AgentRouterV2(cat_reg, agent_reg)
    results = router.route_message("@codex review")
    assert len(results) == 1
    assert results[0]["breed_id"] == "codex"
