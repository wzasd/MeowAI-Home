from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional

from src.models.types import CatConfig, AgentMessage, InvocationOptions


class BaseProvider(ABC):
    def __init__(self, config: CatConfig):
        self.config = config
        self.cat_id = config.cat_id
        self.name = config.display_name

    def build_env(self) -> Dict[str, str]:
        """Resolve account credentials as env vars for CLI subprocess."""
        if not self.config.account_ref:
            return {}
        from src.config.account_resolver import resolve_account_env
        return resolve_account_env(self.config.account_ref, self.config.provider)

    def build_system_prompt(self) -> str:
        parts = [f"你是{self.config.name}。"]
        if self.config.personality:
            parts.append(f"性格：{self.config.personality}")
        if self.config.role_description:
            parts.append(f"角色：{self.config.role_description}")

        caps = getattr(self.config, "capabilities", []) or []
        perms = getattr(self.config, "permissions", []) or []
        if caps:
            parts.append(f"你的能力范围：{', '.join(caps)}。超出能力范围的任务请明确拒绝。")
        if perms:
            parts.append(f"你的操作权限：{', '.join(perms)}。没有权限的操作禁止执行。")

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
