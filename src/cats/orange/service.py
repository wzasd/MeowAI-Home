import os
import tempfile
from typing import AsyncIterator, Optional
from ..base import AgentService
from src.utils.process import run_cli_command, run_cli_command_stream


class OrangeService(AgentService):
    """Orange Cat (阿橘) - Developer Agent"""

    async def chat(self, message: str, system_prompt: Optional[str] = None) -> str:
        """Get complete response"""
        chunks = []
        async for chunk in self.chat_stream(message, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_stream(self, message: str, system_prompt: Optional[str] = None) -> AsyncIterator[str]:
        """Stream response with real CLI invocation - true streaming"""
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
            # 3. Build CLI command with stream-json output
            cmd = self.cli_config["command"]
            args = self.cli_config.get("defaultArgs", []).copy()
            args.extend([
                "--append-system-prompt-file", temp_file.name,
                "--output-format", "stream-json",
                "--include-partial-messages",
                message
            ])

            # 4. Stream CLI output in real-time
            async for line in run_cli_command_stream(cmd, args, timeout=300.0):
                # Parse each NDJSON line immediately
                if not line.strip():
                    continue
                try:
                    import json
                    event = json.loads(line)
                    if event.get("type") == "stream_event":
                        # Handle partial streaming events
                        stream_event = event.get("event", {})
                        if stream_event.get("type") == "content_block_delta":
                            delta = stream_event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    yield text
                    elif event.get("type") == "assistant":
                        # Handle final assistant message
                        message_data = event.get("message", {})
                        content = message_data.get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield text
                except json.JSONDecodeError:
                    continue
        finally:
            # 5. Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
