from typing import AsyncIterator, List

from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig, AgentMessage, InvocationOptions,
    AgentMessageType, TokenUsage
)
from src.utils.cli_spawn import spawn_cli


class ClaudeProvider(BaseProvider):
    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = ["--print"]

        # Carry over base args from config, but skip our own managed flags
        for arg in self.config.cli_args:
            if arg in ("--output-format", "stream-json"):
                continue
            args.append(arg)

        # Always use stream-json for real-time streaming
        args.extend(["--output-format", "stream-json", "--verbose"])

        if options and options.system_prompt:
            args.extend(["--append-system-prompt", options.system_prompt])
        if options and options.session_id:
            args.extend(["--resume", options.session_id])
        if options and options.effort:
            args.extend(["--effort", options.effort])
        if options and options.extra_args:
            args.extend(options.extra_args)
        args.append(prompt)
        return args

    async def invoke(self, prompt: str, options: InvocationOptions = None) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()
        args = self._build_args(prompt, options)
        timeout = options.timeout or 300.0
        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=timeout, env=self.build_env(), cwd=options.cwd
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id)
        finally:
            yield AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        event_type = event.get("type", "")
        messages = []

        # Surface system/hook events as status so users can see process state
        if event_type in ("system",):
            raw = event.get("message")
            text = raw if isinstance(raw, str) else (str(raw) if raw is not None else "")
            if text:
                messages.append(AgentMessage(type=AgentMessageType.STATUS, content=text, cat_id=self.cat_id))
            return messages

        if event_type == "assistant":
            msg_data = event.get("message", {})
            for block in msg_data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        messages.append(AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=self.cat_id))
                elif isinstance(block, dict) and block.get("type") == "thinking":
                    text = block.get("thinking") or block.get("text", "")
                    if text:
                        messages.append(AgentMessage(type=AgentMessageType.THINKING, content=text, cat_id=self.cat_id))

            usage_data = msg_data.get("usage")
            if usage_data:
                messages.append(AgentMessage(
                    type=AgentMessageType.USAGE,
                    usage=TokenUsage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
                        cache_creation_tokens=usage_data.get("cache_creation_input_tokens", 0),
                    ),
                    cat_id=self.cat_id,
                ))

        elif event_type == "result":
            messages.append(AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id))
            session_id = event.get("session_id")
            if session_id:
                for msg in messages:
                    msg.session_id = session_id

        return messages
