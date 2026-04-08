from src.cats.base import AgentService


class InkyService(AgentService):
    """Inky Cat (墨点) - Reviewer Agent"""

    async def chat(self, message: str, system_prompt: str = None) -> str:
        """Get complete response"""
        chunks = []
        async for chunk in self.chat_stream(message, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_stream(self, message: str, system_prompt: str = None):
        """Stream response - inherits from base class"""
        # Implementation is same as OrangeService
        # Just import and reuse
        from src.cats.orange.service import OrangeService

        # Delegate to a temporary OrangeService instance
        temp_service = OrangeService(self.config)
        async for chunk in temp_service.chat_stream(message, system_prompt):
            yield chunk
