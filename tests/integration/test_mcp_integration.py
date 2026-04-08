import pytest
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks
from src.thread.models import Thread


@pytest.mark.asyncio
async def test_mcp_end_to_end():
    """测试 MCP 端到端流程"""
    # 1. 创建 thread
    thread = Thread.create("MCP Test")

    # 2. 创建 MCPClient 并注册工具
    mcp = MCPClient(thread)
    for tool_name, config in TOOL_REGISTRY.items():
        mcp.register_tool(
            name=tool_name,
            description=config["description"],
            parameters=config["parameters"],
            handler=config["handler"]
        )

    # 3. 模拟猫回复（带回调）
    cat_response = """我查了一下代码。

<mcp:search_files>
{"query": "class Thread", "path": "src"}
</mcp:search_files>

<mcp:post_message>
{"content": "找到 Thread 类定义了！"}
</mcp:post_message>

请 @review 检查一下。
<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>"""

    # 4. 解析回调
    parsed = parse_callbacks(cat_response)

    # 5. 执行工具调用
    for tc in parsed.tool_calls:
        if tc.tool_name != "targetcats":
            result = await mcp.call(tc.tool_name, tc.params)
            assert result.success

    # 6. 验证结果
    assert "inky" in parsed.targetCats
    assert len(thread.messages) >= 1  # post_message 添加了消息


def test_mcp_tools_prompt():
    """测试 MCP 工具提示生成"""
    mcp = MCPClient()

    for tool_name, config in TOOL_REGISTRY.items():
        mcp.register_tool(
            name=tool_name,
            description=config["description"],
            parameters=config["parameters"],
            handler=lambda **kwargs: None
        )

    prompt = mcp.build_tools_prompt()

    assert "post_message" in prompt
    assert "search_files" in prompt
    assert "targetCats" in prompt
    assert "<mcp:工具名>" in prompt
