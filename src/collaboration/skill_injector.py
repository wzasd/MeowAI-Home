from typing import Dict, List


class SkillInjector:
    """Helper for injecting skill context into agent system prompts."""

    def inject(self, agents: List[Dict], skill_id: str, skill_content: str) -> None:
        for agent_info in agents:
            service = agent_info["service"]
            original_method = service.build_system_prompt
            agent_info["_original_build_prompt"] = original_method
            service.build_system_prompt = lambda orig=original_method, sc=skill_content: orig() + f"\n\n## 激活技能\n{sc}\n---\n"

    def restore(self, agents: List[Dict]) -> None:
        for agent_info in agents:
            if "_original_build_prompt" in agent_info:
                agent_info["service"].build_system_prompt = agent_info["_original_build_prompt"]
                del agent_info["_original_build_prompt"]
