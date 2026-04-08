from abc import ABC, abstractmethod
from typing import Any, Dict, AsyncIterator, Optional


class AgentService(ABC):
    """AI Agent服务基类"""

    def __init__(self, breed_config: Dict[str, Any]):
        self.config = breed_config
        self.name = breed_config["displayName"]
        self.personality = breed_config["personality"]
        self.catchphrases = breed_config.get("catchphrases", [])
        self.cli_config = breed_config["cli"]

    def build_system_prompt(self) -> str:
        """Build system prompt from breed configuration"""
        parts = [
            f"你是{self.name}。",
            f"性格：{self.personality}",
        ]

        if "roleDescription" in self.config:
            parts.append(f"角色：{self.config['roleDescription']}")

        if self.catchphrases:
            parts.append(f"口头禅：{'、'.join(self.catchphrases)}")

        return "\n".join(parts)

    @abstractmethod
    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """发送消息并获取回复"""
        pass

    @abstractmethod
    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """发送消息并流式获取回复"""
        pass
