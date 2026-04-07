from typing import AsyncIterator
from ..base import AgentService
from .config import OrangeConfig
from .personality import OrangePersonality


class OrangeService(AgentService):
    def __init__(self):
        config = OrangeConfig()
        super().__init__(config.name, config.model, config.provider)
        self.personality = OrangePersonality()

    async def chat(self, message: str) -> str:
        """Mock实现 - 返回固定回复"""
        # TODO: 实现真实的GLM-5.0 CLI调用
        return f"喵～收到你的消息：{message}。这个我熟！让我想想怎么帮你～"

    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """Mock实现 - 流式返回"""
        response = await self.chat(message)
        for char in response:
            yield char
