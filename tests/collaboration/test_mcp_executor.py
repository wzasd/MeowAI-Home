import pytest
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.thread.models import Thread


class TestMCPExecutor:
    def test_register_tools_creates_client_with_tools(self):
        thread = Thread.create("test")
        executor = MCPExecutor()
        client = executor.register_tools(thread)
        assert isinstance(client, MCPClient)
        for tool_name in TOOL_REGISTRY:
            assert client.get_tool(tool_name) is not None

    def test_build_tools_prompt(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)
        prompt = executor.build_tools_prompt(client)
        assert "可用工具" in prompt
        assert "post_message" in prompt

    @pytest.mark.asyncio
    async def test_execute_callbacks_parses_and_executes(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)
        raw_content = 'Hello <mcp:post_message>{"content": "test msg"}</mcp:post_message>'
        result = await executor.execute_callbacks(raw_content, client, thread)
        assert "post_message" not in result.clean_content
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "post_message"

    @pytest.mark.asyncio
    async def test_execute_callbacks_skips_targetcats(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)
        raw_content = 'Go <mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
        result = await executor.execute_callbacks(raw_content, client, thread)
        assert result.targetCats == ["inky"]
