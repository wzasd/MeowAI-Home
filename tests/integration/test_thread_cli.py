import pytest
import tempfile
import asyncio
from pathlib import Path
from click.testing import CliRunner
from src.cli.main import cli
from src.thread import ThreadManager
from src.thread.stores.sqlite_store import SQLiteStore


@pytest.fixture
def isolated_env():
    """隔离的测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "meowai.db"
        ThreadManager.reset()

        # 创建 manager
        manager = ThreadManager(skip_init=True)
        store = SQLiteStore(db_path)
        asyncio.run(store.initialize())
        manager._store = store
        manager._current_thread_id = None

        runner = CliRunner()
        yield runner, manager

        ThreadManager.reset()


def test_thread_create(isolated_env):
    """测试创建 thread"""
    runner, manager = isolated_env
    result = runner.invoke(cli, ['thread', 'create', 'Test Thread'])

    assert result.exit_code == 0
    assert "创建 thread" in result.output

    threads = asyncio.run(manager.list())
    assert len(threads) == 1


def test_thread_list(isolated_env):
    """测试列出 threads"""
    runner, manager = isolated_env
    asyncio.run(manager.create("Thread 1"))
    asyncio.run(manager.create("Thread 2"))

    result = runner.invoke(cli, ['thread', 'list'])
    assert result.exit_code == 0
    assert "Thread 1" in result.output
    assert "Thread 2" in result.output


def test_thread_switch(isolated_env):
    """测试切换 thread"""
    runner, manager = isolated_env
    thread = asyncio.run(manager.create("Test"))

    result = runner.invoke(cli, ['thread', 'switch', thread.id])
    assert result.exit_code == 0
    assert "已切换到" in result.output
    assert manager.get_current().id == thread.id


def test_thread_delete(isolated_env):
    """测试删除 thread"""
    runner, manager = isolated_env
    thread = asyncio.run(manager.create("To Delete"))

    result = runner.invoke(cli, ['thread', 'delete', thread.id, '--force'])
    assert result.exit_code == 0
    assert "已删除" in result.output
    assert asyncio.run(manager.get(thread.id)) is None
