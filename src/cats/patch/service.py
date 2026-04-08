from typing import AsyncIterator, Optional
from ..base import AgentService


class PatchService(AgentService):
    """Patch Cat (花花) - Researcher Agent (Stub)"""

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Get complete response (not implemented yet)"""
        raise NotImplementedError("PatchService not implemented yet - will be completed in Task 6")

    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Stream response (not implemented yet)"""
        raise NotImplementedError("PatchService not implemented yet - will be completed in Task 6")
        yield  # Make it a generator
