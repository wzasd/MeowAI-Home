from abc import ABC, abstractmethod
from typing import AsyncIterator, List

from src.models.types import CatConfig, AgentMessage, InvocationOptions


class BaseProvider(ABC):
    def __init__(self, config: CatConfig):
        self.config = config
        self.cat_id = config.cat_id
        self.name = config.display_name

    def build_system_prompt(self) -> str:
        parts = [f"你是{self.config.name}。"]
        if self.config.personality:
            parts.append(f"性格：{self.config.personality}")
        if self.config.role_description:
            parts.append(f"角色：{self.config.role_description}")
        return "\n".join(parts)

    @abstractmethod
    async def invoke(self, prompt: str, options: InvocationOptions = None) -> AsyncIterator[AgentMessage]:
        pass

    @abstractmethod
    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        pass

    @abstractmethod
    def _transform_event(self, event: dict) -> list:
        pass
