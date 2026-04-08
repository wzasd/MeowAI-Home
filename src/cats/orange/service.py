import os
import tempfile
from typing import AsyncIterator, Optional
from ..base import AgentService
from src.utils.ndjson import parse_ndjson_stream
from src.utils.process import run_cli_command


class OrangeService(AgentService):
    """Orange Cat (阿橘) - Developer Agent"""

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Get complete response"""
        chunks = []
        async for chunk in self.chat_stream(message, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Stream response with real CLI invocation"""
        # 1. Build system prompt
        if system_prompt is None:
            system_prompt = self.build_system_prompt()

        # 2. Create temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        )
        temp_file.write(system_prompt)
        temp_file.close()

        try:
            # 3. Build CLI command
            cmd = self.cli_config["command"]
            args = self.cli_config.get("defaultArgs", []).copy()
            args.extend([
                "--append-system-prompt-file", temp_file.name,
                message
            ])

            # 4. Execute CLI
            result = await run_cli_command(
                command=cmd,
                args=args,
                timeout=300.0
            )

            # 5. Parse NDJSON
            async for event in parse_ndjson_stream(result["stdout"]):
                if isinstance(event, dict) and event.get("type") == "assistant":
                    message_data = event.get("message", {})
                    content = message_data.get("content", [])

                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                yield text
        finally:
            # 6. Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
