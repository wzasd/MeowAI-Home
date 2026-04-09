from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks


class MCPExecutor:
    """Helper for MCP tool registration and callback execution."""

    def register_tools(self, thread) -> MCPClient:
        client = MCPClient(thread)
        for tool_name, config in TOOL_REGISTRY.items():
            client.register_tool(
                name=tool_name,
                description=config["description"],
                parameters=config["parameters"],
                handler=config["handler"],
            )
        return client

    def build_tools_prompt(self, client: MCPClient) -> str:
        return client.build_tools_prompt()

    async def execute_callbacks(self, raw_content: str, client: MCPClient, thread):
        parsed = parse_callbacks(raw_content)
        for tool_call in parsed.tool_calls:
            if tool_call.tool_name == "targetcats":
                continue
            await client.call(tool_call.tool_name, tool_call.params)
        return parsed
