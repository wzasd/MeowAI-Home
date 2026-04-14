from typing import AsyncIterator, List
from src.providers.base import BaseProvider
from src.models.types import CatConfig, AgentMessage, InvocationOptions, AgentMessageType, TokenUsage
from src.utils.cli_spawn import spawn_cli


class GeminiProvider(BaseProvider):
    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = list(self.config.cli_args)
        if options and options.system_prompt:
            args.extend(["--system-instruction", options.system_prompt])
        if options and options.session_id:
            args.extend(["--resume", options.session_id])
        if options and options.extra_args:
            args.extend(options.extra_args)
        args.append(prompt)
        return args

    async def invoke(self, prompt: str, options: InvocationOptions = None) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()
        args = self._build_args(prompt, options)
        try:
            async for event in spawn_cli(
                self.config.cli_command, args, timeout=options.timeout or 300.0, env=self.build_env(), cwd=options.cwd
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
        if event_type == "text":
            text = event.get("text", "")
            if text:
                messages.append(AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=self.cat_id))
        elif event_type == "usage":
            messages.append(AgentMessage(
                type=AgentMessageType.USAGE,
                usage=TokenUsage(input_tokens=event.get("input_tokens", 0), output_tokens=event.get("output_tokens", 0)),
                cat_id=self.cat_id,
            ))
        elif event_type in ("done", "finish"):
            messages.append(AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id))
        return messages
