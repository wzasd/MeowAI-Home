from typing import AsyncIterator, List, Optional
from src.providers.base import BaseProvider
from src.models.types import (
    CatConfig,
    AgentMessage,
    InvocationOptions,
    AgentMessageType,
    TokenUsage,
)
from src.utils.cli_spawn import spawn_cli


class OpenCodeProvider(BaseProvider):
    def _build_args(self, prompt: str, options: InvocationOptions) -> list:
        args = ["run", "--format", "json"]

        if options and options.session_id:
            args.extend(["--session", options.session_id])

        if self.config.default_model:
            args.extend(["--model", self.config.default_model])

        for arg in self.config.cli_args:
            if arg in ("--format", "json", "run"):
                continue
            args.append(arg)

        if options and options.system_prompt:
            args.extend(["--system", options.system_prompt])
        if options and options.extra_args:
            args.extend(options.extra_args)

        args.append(prompt)
        return args

    async def invoke(
        self, prompt: str, options: InvocationOptions = None
    ) -> AsyncIterator[AgentMessage]:
        if options is None:
            options = InvocationOptions()
        args = self._build_args(prompt, options)
        self._session_id: Optional[str] = None
        try:
            async for event in spawn_cli(
                self.config.cli_command,
                args,
                timeout=options.timeout or 300.0,
                env=self.build_env(),
                cwd=options.cwd,
            ):
                for msg in self._transform_event(event):
                    yield msg
        except Exception as e:
            yield AgentMessage(
                type=AgentMessageType.ERROR, content=str(e), cat_id=self.cat_id
            )
        finally:
            done = AgentMessage(type=AgentMessageType.DONE, cat_id=self.cat_id)
            if self._session_id:
                done.session_id = self._session_id
            yield done

    def _transform_event(self, event: dict) -> List[AgentMessage]:
        event_type = event.get("type", "")
        messages = []

        if event_type == "text":
            part = event.get("part", {})
            text = part.get("text", "")
            if text:
                messages.append(
                    AgentMessage(
                        type=AgentMessageType.TEXT, content=text, cat_id=self.cat_id
                    )
                )
            sid = event.get("sessionID")
            if sid and not self._session_id:
                self._session_id = sid

        elif event_type == "tool_use":
            part = event.get("part", {})
            tool_name = part.get("tool", "unknown")
            state = part.get("state", {})
            status = state.get("status", "")
            tool_input = state.get("input", {})
            tool_output = state.get("output", "")

            if status == "completed":
                input_summary = self._summarize_tool_input(tool_name, tool_input)
                msg_text = f"🔧 {tool_name}({input_summary})"
                if tool_output:
                    output_preview = str(tool_output)[:200]
                    msg_text += f" → {output_preview}"
                messages.append(
                    AgentMessage(
                        type=AgentMessageType.STATUS,
                        content=msg_text,
                        cat_id=self.cat_id,
                    )
                )
            else:
                input_summary = self._summarize_tool_input(tool_name, tool_input)
                messages.append(
                    AgentMessage(
                        type=AgentMessageType.STATUS,
                        content=f"⏳ {tool_name}({input_summary})...",
                        cat_id=self.cat_id,
                    )
                )

            sid = event.get("sessionID")
            if sid and not self._session_id:
                self._session_id = sid

        elif event_type == "step_start":
            sid = event.get("sessionID")
            if sid and not self._session_id:
                self._session_id = sid

        elif event_type == "step_finish":
            part = event.get("part", {})
            tokens = part.get("tokens", {})
            if tokens:
                messages.append(
                    AgentMessage(
                        type=AgentMessageType.USAGE,
                        usage=TokenUsage(
                            input_tokens=tokens.get("input", 0),
                            output_tokens=tokens.get("output", 0),
                            cache_read_tokens=tokens.get("cache", {}).get("read", 0),
                            cache_creation_tokens=tokens.get("cache", {}).get(
                                "write", 0
                            ),
                        ),
                        cat_id=self.cat_id,
                    )
                )
            sid = event.get("sessionID")
            if sid and not self._session_id:
                self._session_id = sid

        return messages

    @staticmethod
    def _summarize_tool_input(tool_name: str, tool_input: dict) -> str:
        if not tool_input:
            return ""
        if tool_name in ("webfetch",):
            return tool_input.get("url", "")
        if tool_name in ("read", "write_file", "edit_file"):
            return tool_input.get("file_path", tool_input.get("path", ""))
        if tool_name in ("bash", "execute_command"):
            cmd = tool_input.get("command", "")
            return cmd[:80]
        items = [f"{k}={v}" for k, v in list(tool_input.items())[:3]]
        return ", ".join(items)
