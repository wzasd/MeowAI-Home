import pytest
from src.models.agent_registry import AgentRegistry


class FakeAgentService:
    def __init__(self, cat_id: str):
        self.cat_id = cat_id
    async def invoke(self, prompt, options=None):
        yield f"response from {self.cat_id}"


class TestAgentRegistry:
    def test_register_and_get(self):
        reg = AgentRegistry()
        service = FakeAgentService("opus")
        reg.register("opus", service)
        assert reg.get("opus") is service

    def test_register_duplicate_raises(self):
        reg = AgentRegistry()
        reg.register("opus", FakeAgentService("opus"))
        with pytest.raises(ValueError, match="already registered"):
            reg.register("opus", FakeAgentService("opus"))

    def test_get_not_found_raises(self):
        reg = AgentRegistry()
        with pytest.raises(KeyError):
            reg.get("nonexistent")

    def test_has(self):
        reg = AgentRegistry()
        assert reg.has("opus") is False
        reg.register("opus", FakeAgentService("opus"))
        assert reg.has("opus") is True

    def test_get_all_entries(self):
        reg = AgentRegistry()
        s1 = FakeAgentService("opus")
        s2 = FakeAgentService("sonnet")
        reg.register("opus", s1)
        reg.register("sonnet", s2)
        entries = reg.get_all_entries()
        assert entries["opus"] is s1
        assert entries["sonnet"] is s2

    def test_reset(self):
        reg = AgentRegistry()
        reg.register("opus", FakeAgentService("opus"))
        reg.reset()
        assert reg.has("opus") is False
