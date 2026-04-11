"""Phase 6 集成测试 — 验证注册表 + Provider + 路由端到端"""
import pytest
from src.models.registry_init import initialize_registries
from src.router.agent_router_v2 import AgentRouterV2
from src.config.budgets import get_cat_budget
from src.config.model_resolver import get_cat_model
from src.config.context_windows import get_context_window_size
from src.session.chain import SessionChain
from src.invocation.tracker import InvocationTracker


def test_full_registry_initialization():
    cat_reg, agent_reg = initialize_registries("cat-config.json")
    # 用户的猫配置: 阿橘(orange), 墨点(inky), 花花(patch)
    assert cat_reg.has("orange")
    assert cat_reg.has("inky")
    assert cat_reg.has("patch")
    assert agent_reg.has("orange")
    assert agent_reg.has("inky")
    assert agent_reg.has("patch")


def test_router_end_to_end():
    cat_reg, agent_reg = initialize_registries("cat-config.json")
    router = AgentRouterV2(cat_reg, agent_reg)
    # 使用用户的猫配置
    targets = router.resolve_targets("@阿橘 写代码")
    assert targets == ["orange"]
    targets = router.resolve_targets("@阿橘 @墨点 review")
    assert "orange" in targets
    assert "inky" in targets
    service = router.get_service("orange")
    assert service is not None
    assert service.cat_id == "orange"


def test_budget_and_model_resolution():
    cat_reg, _ = initialize_registries("cat-config.json")
    budget = get_cat_budget("orange", cat_reg)
    assert budget.max_prompt_tokens > 0
    model = get_cat_model("orange", cat_reg)
    assert "claude" in model
    window = get_context_window_size(model)
    assert window is not None
    assert window >= 100000


def test_session_chain_lifecycle():
    chain = SessionChain()
    r1 = chain.create("orange", "t1", "s1")
    assert chain.get_active("orange", "t1").session_id == "s1"
    chain.seal("orange", "t1")
    assert chain.get_active("orange", "t1") is None
    r2 = chain.create("orange", "t1", "s2")
    assert chain.get_active("orange", "t1").session_id == "s2"


def test_tracker_lifecycle():
    tracker = InvocationTracker()
    c1 = tracker.start("t1", "opus")
    assert tracker.is_active("t1", "opus")
    tracker.cancel("t1", "opus")
    assert not tracker.is_active("t1", "opus")
