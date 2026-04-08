import pytest
from src.collaboration.mcp_client import MCPClient, MCPResult, MCPTool


@pytest.fixture
def mcp_client():
    """创建测试用的 MCPClient"""
    return MCPClient(thread=None)


@pytest.mark.asyncio
async def test_register_tool(mcp_client):
    """测试工具注册"""
    async def mock_handler(name: str):
        return {"greeting": f"Hello {name}"}

    mcp_client.register_tool(
        name="greet",
        description="Greet someone",
        parameters={"name": {"type": "string"}},
        handler=mock_handler
    )

    assert "greet" in mcp_client.get_available_tools()


@pytest.mark.asyncio
async def test_call_tool_success(mcp_client):
    """测试成功调用工具"""
    async def mock_handler(name: str):
        return {"greeting": f"Hello {name}"}

    mcp_client.register_tool(
        name="greet",
        description="Greet someone",
        parameters={"name": {"type": "string"}},
        handler=mock_handler
    )

    result = await mcp_client.call("greet", {"name": "World"})

    assert result.success is True
    assert result.tool_name == "greet"
    assert result.data["greeting"] == "Hello World"


@pytest.mark.asyncio
async def test_call_tool_not_found(mcp_client):
    """测试调用不存在的工具"""
    result = await mcp_client.call("nonexistent", {})

    assert result.success is False
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_call_tool_error(mcp_client):
    """测试工具执行出错"""
    async def error_handler():
        raise ValueError("Something went wrong")

    mcp_client.register_tool(
        name="error_tool",
        description="Tool that errors",
        parameters={},
        handler=error_handler
    )

    result = await mcp_client.call("error_tool", {})

    assert result.success is False
    assert "Something went wrong" in result.error


def test_build_tools_prompt(mcp_client):
    """测试构建工具提示"""
    async def mock_handler():
        pass

    mcp_client.register_tool(
        name="tool1",
        description="First tool",
        parameters={},
        handler=mock_handler
    )

    prompt = mcp_client.build_tools_prompt()

    assert "tool1" in prompt
    assert "First tool" in prompt
    assert "<mcp:工具名>" in prompt
