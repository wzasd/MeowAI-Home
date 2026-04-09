import pytest
from unittest.mock import MagicMock
from src.collaboration.skill_injector import SkillInjector


def _mock_agents():
    agent = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock(),
    }
    agent["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    return [agent]


class TestSkillInjector:
    def test_inject_wraps_build_system_prompt(self):
        agents = _mock_agents()
        injector = SkillInjector()
        injector.inject(agents, "fake_skill", "这是技能上下文")
        prompt = agents[0]["service"].build_system_prompt()
        assert "技能上下文" in prompt
        assert "你是阿橘" in prompt

    def test_restore_resets_original_prompt(self):
        agents = _mock_agents()
        injector = SkillInjector()
        original = agents[0]["service"].build_system_prompt()
        injector.inject(agents, "fake_skill", "技能内容")
        injector.restore(agents)
        restored = agents[0]["service"].build_system_prompt()
        assert restored == original
        assert "技能内容" not in restored

    def test_restore_no_inject_is_safe(self):
        agents = _mock_agents()
        injector = SkillInjector()
        injector.restore(agents)  # Should not raise
