"""Agent discovery and hot registration tests"""
import pytest
from src.models.agent_registry import AgentRegistry
from src.router.discovery import AgentDiscovery, AgentDescriptor


@pytest.fixture
def discovery():
    registry = AgentRegistry()
    return AgentDiscovery(registry)


class TestAgentDescriptor:
    def test_creation(self):
        desc = AgentDescriptor(
            cat_id="test_1",
            breed="ragdoll",
            display_name="Test Agent",
            capabilities=["coding", "debugging"],
            provider="claude",
        )
        assert desc.cat_id == "test_1"
        assert desc.breed == "ragdoll"
        assert desc.display_name == "Test Agent"
        assert desc.capabilities == ["coding", "debugging"]
        assert desc.provider == "claude"
        assert desc.config is None

    def test_creation_with_config(self):
        desc = AgentDescriptor(
            cat_id="test_2",
            breed="siamese",
            display_name="Another Agent",
            capabilities=["research"],
            provider="gemini",
            config={"model": "gemini-1.5", "temperature": 0.7},
        )
        assert desc.config == {"model": "gemini-1.5", "temperature": 0.7}


class TestAgentDiscoveryRegister:
    def test_register_new_agent(self, discovery):
        desc = AgentDescriptor(
            cat_id="new_1",
            breed="maine_coon",
            display_name="New Agent",
            capabilities=["review"],
            provider="codex",
        )
        assert discovery.register(desc) is True
        assert discovery.registry.has("new_1")

    def test_register_duplicate_fails(self, discovery):
        desc = AgentDescriptor(
            cat_id="dup_1",
            breed="ragdoll",
            display_name="Dup Agent",
            capabilities=["tdd"],
            provider="claude",
        )
        discovery.register(desc)
        assert discovery.register(desc) is False

    def test_register_preserves_capabilities(self, discovery):
        desc = AgentDescriptor(
            cat_id="cap_1",
            breed="ragdoll",
            display_name="Cap Agent",
            capabilities=["a", "b", "c"],
            provider="claude",
        )
        discovery.register(desc)
        retrieved = discovery.get_agent("cap_1")
        assert retrieved.capabilities == ["a", "b", "c"]


class TestAgentDiscoveryDeregister:
    def test_deregister_existing(self, discovery):
        desc = AgentDescriptor(
            cat_id="del_1",
            breed="ragdoll",
            display_name="Del Agent",
            capabilities=["debug"],
            provider="claude",
        )
        discovery.register(desc)
        assert discovery.deregister("del_1") is True
        assert not discovery.registry.has("del_1")

    def test_deregister_nonexistent(self, discovery):
        assert discovery.deregister("missing") is False


class TestAgentDiscoveryList:
    def test_list_empty(self, discovery):
        assert discovery.list_agents() == []

    def test_list_returns_all(self, discovery):
        discovery.register(AgentDescriptor("a1", "ragdoll", "A1", ["x"], "p1"))
        discovery.register(AgentDescriptor("a2", "siamese", "A2", ["y"], "p2"))
        agents = discovery.list_agents()
        assert len(agents) == 2
        ids = {a.cat_id for a in agents}
        assert ids == {"a1", "a2"}

    def test_list_after_deregister(self, discovery):
        discovery.register(AgentDescriptor("a1", "ragdoll", "A1", ["x"], "p1"))
        discovery.register(AgentDescriptor("a2", "siamese", "A2", ["y"], "p2"))
        discovery.deregister("a1")
        agents = discovery.list_agents()
        assert len(agents) == 1
        assert agents[0].cat_id == "a2"


class TestAgentDiscoveryGet:
    def test_get_existing(self, discovery):
        desc = AgentDescriptor("get_1", "ragdoll", "Get Agent", ["z"], "p1")
        discovery.register(desc)
        retrieved = discovery.get_agent("get_1")
        assert retrieved is not None
        assert retrieved.cat_id == "get_1"
        assert retrieved.display_name == "Get Agent"

    def test_get_nonexistent(self, discovery):
        assert discovery.get_agent("missing") is None


class TestMultipleAgents:
    def test_multiple_registration(self, discovery):
        for i in range(10):
            desc = AgentDescriptor(
                cat_id=f"agent_{i}",
                breed="ragdoll",
                display_name=f"Agent {i}",
                capabilities=["test"],
                provider="claude",
            )
            assert discovery.register(desc) is True
        assert len(discovery.list_agents()) == 10


class TestAgentConfig:
    def test_config_preserved(self, discovery):
        config = {"timeout": 30, "max_tokens": 2000}
        desc = AgentDescriptor(
            cat_id="cfg_1",
            breed="ragdoll",
            display_name="Cfg Agent",
            capabilities=["test"],
            provider="claude",
            config=config,
        )
        discovery.register(desc)
        retrieved = discovery.get_agent("cfg_1")
        assert retrieved.config == config
