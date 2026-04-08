import pytest
import tempfile
from pathlib import Path
import asyncio

from click.testing import CliRunner
from src.cli.main import cli
from src.thread import ThreadManager
from src.thread.stores.sqlite_store import SQLiteStore


@pytest.fixture
def isolated_env():
    """隔离的测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "meowai.db"

        # 重置单例
        ThreadManager.reset()

        # 创建 manager
        manager = ThreadManager(skip_init=True)
        store = SQLiteStore(db_path)
        asyncio.run(store.initialize())
        manager._store = store
        manager._current_thread_id = None

        runner = CliRunner()
        yield runner, manager, db_path

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_persistence_across_sessions(isolated_env):
    """测试跨会话持久化"""
    runner, manager, db_path = isolated_env

    # 创建 thread
    result = runner.invoke(cli, ['thread', 'create', 'Persistent Thread'])
    assert result.exit_code == 0

    # 模拟新会话（重置但保持数据库）
    ThreadManager.reset()
    new_manager = ThreadManager(skip_init=True)
    new_store = SQLiteStore(db_path)
    await new_store.initialize()
    new_manager._store = new_store

    # 验证数据还在
    threads = await new_manager.list()
    assert len(threads) == 1
    assert threads[0].name == "Persistent Thread"


def test_resume_command(isolated_env):
    """测试 --resume 功能（通过直接调用 manager）"""
    runner, manager, db_path = isolated_env

    # 先创建 thread
    result = runner.invoke(cli, ['thread', 'create', 'Test Thread'])
    assert result.exit_code == 0

    # 验证 thread 已创建
    threads = asyncio.run(manager.list())
    assert len(threads) == 1
    assert threads[0].name == "Test Thread"

    # 模拟 --resume 逻辑：获取最近更新的 thread
    thread = threads[0]
    manager.switch(thread.id)

    # 验证可以获取当前 thread
    current = manager.get_current()
    assert current is not None
    assert current.name == "Test Thread"


def test_thread_info_with_messages(isolated_env):
    """测试 thread info 显示消息数"""
    runner, manager, db_path = isolated_env

    # 创建 thread
    result = runner.invoke(cli, ['thread', 'create', 'Test'])

    # 检查 thread info
    result = runner.invoke(cli, ['thread', 'info'])
    assert result.exit_code == 0
    assert "消息数" in result.output
