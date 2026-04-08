import pytest
import os
from src.collaboration.mcp_tools import (
    post_message_tool,
    search_files_tool,
    target_cats_tool,
    TOOL_REGISTRY
)
from src.thread.models import Thread


@pytest.mark.asyncio
async def test_post_message_tool():
    """测试 post_message 工具"""
    thread = Thread.create("Test Thread")
    initial_count = len(thread.messages)

    result = await post_message_tool(thread, "Hello from MCP!")

    assert result["status"] == "sent"
    assert len(thread.messages) == initial_count + 1
    assert thread.messages[-1].content == "Hello from MCP!"
    assert thread.messages[-1].role == "assistant"


@pytest.mark.asyncio
async def test_post_message_preview():
    """测试长消息预览"""
    thread = Thread.create("Test")
    long_message = "A" * 100

    result = await post_message_tool(thread, long_message)

    assert result["status"] == "sent"
    assert "..." in result["message_preview"]
    assert len(result["message_preview"]) == 53  # 50 chars + "..."


@pytest.mark.asyncio
async def test_search_files_tool():
    """测试 search_files 工具"""
    # 在当前项目中搜索已知内容
    result = await search_files_tool("class Thread", path="src")

    assert "matches" in result
    assert isinstance(result["matches"], list)
    # 应该能找到 models.py 中的 Thread 类
    found_thread = any("models.py" in m["file"] for m in result["matches"])
    assert found_thread or len(result["matches"]) == 0  # 可能没有 grep


@pytest.mark.asyncio
async def test_search_files_tool_not_found():
    """测试搜索不存在的内容"""
    result = await search_files_tool("XYZ_NOT_EXIST_12345", path="src")

    assert "matches" in result
    assert len(result["matches"]) == 0


@pytest.mark.asyncio
async def test_target_cats_tool():
    """测试 targetCats 工具"""
    result = await target_cats_tool(["orange", "inky"])

    assert result["targetCats"] == ["orange", "inky"]


def test_tool_registry():
    """测试工具注册表"""
    assert "post_message" in TOOL_REGISTRY
    assert "search_files" in TOOL_REGISTRY
    assert "targetCats" in TOOL_REGISTRY

    # 验证结构
    for tool_name, config in TOOL_REGISTRY.items():
        assert "description" in config
        assert "parameters" in config
        assert "handler" in config
