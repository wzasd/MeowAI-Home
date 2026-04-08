import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from src.cli.main import cli
from src.thread import ThreadManager


@pytest.fixture
def isolated_env():
    """隔离的测试环境"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        ThreadManager.reset()
        manager = ThreadManager()
        manager._persistence.storage_path = storage_path
        manager._threads = {}
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
    assert len(manager.list()) == 1


def test_thread_list(isolated_env):
    """测试列出 threads"""
    runner, manager = isolated_env
    manager.create("Thread 1")
    manager.create("Thread 2")

    result = runner.invoke(cli, ['thread', 'list'])
    assert result.exit_code == 0
    assert "Thread 1" in result.output
    assert "Thread 2" in result.output


def test_thread_switch(isolated_env):
    """测试切换 thread"""
    runner, manager = isolated_env
    thread = manager.create("Test")

    result = runner.invoke(cli, ['thread', 'switch', thread.id])
    assert result.exit_code == 0
    assert "已切换到" in result.output
    assert manager.get_current().id == thread.id


def test_thread_delete(isolated_env):
    """测试删除 thread"""
    runner, manager = isolated_env
    thread = manager.create("To Delete")

    result = runner.invoke(cli, ['thread', 'delete', thread.id, '--force'])
    assert result.exit_code == 0
    assert "已删除" in result.output
    assert manager.get(thread.id) is None
