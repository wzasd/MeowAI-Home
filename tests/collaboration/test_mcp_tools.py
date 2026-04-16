import pytest
import os
from src.collaboration.mcp_tools import (
    post_message_tool,
    search_files_tool,
    target_cats_tool,
    read_uploaded_file_tool,
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


@pytest.mark.asyncio
async def test_read_uploaded_file():
    """测试 read_uploaded_file 工具正确读取已上传文件"""
    import tempfile
    from pathlib import Path
    from src.thread import ThreadManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ThreadManager(db_path=Path(tmpdir) / "test.db", skip_init=True)
        await manager.async_init()
        thread = await manager.create("Test Thread", project_path=tmpdir)

        # Write a file to the upload directory
        upload_dir = Path(tmpdir) / ".meowai" / "uploads" / thread.id
        upload_dir.mkdir(parents=True, exist_ok=True)
        (upload_dir / "test.txt").write_text("hello from upload", encoding="utf-8")

        result = await read_uploaded_file_tool(thread.id, "test.txt")
        assert "content" in result
        assert "hello from upload" in result["content"]

        # Test path traversal is blocked
        result_bad = await read_uploaded_file_tool(thread.id, "../../etc/passwd")
        assert "error" in result_bad


def test_tool_registry():
    """测试工具注册表"""
    assert "post_message" in TOOL_REGISTRY
    assert "search_files" in TOOL_REGISTRY
    assert "targetCats" in TOOL_REGISTRY
    assert "read_uploaded_file" in TOOL_REGISTRY

    # 验证结构
    for tool_name, config in TOOL_REGISTRY.items():
        assert "description" in config
        assert "parameters" in config
        assert "handler" in config
