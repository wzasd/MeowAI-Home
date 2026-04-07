from abc import ABC, abstractmethod
from typing import AsyncIterator


class AgentService(ABC):
    """AI Agent服务基类"""

    def __init__(self, name: str, model: str, provider: str):
        self.name = name
        self.model = model
        self.provider = provider

    @abstractmethod
    async def chat(self, message: str) -> str:
        """发送消息并获取回复"""
        pass

    @abstractmethod
    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """发送消息并流式获取回复"""
        pass
