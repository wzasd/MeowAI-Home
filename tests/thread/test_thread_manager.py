import pytest
import tempfile
from pathlib import Path
from src.thread.thread_manager import ThreadManager
from src.thread.persistence import ThreadPersistence


@pytest.fixture
def temp_manager():
    """创建使用临时存储的 ThreadManager"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        # 先重置单例
        ThreadManager.reset()
        manager = ThreadManager()
        manager._persistence = ThreadPersistence(storage_path)
        manager._threads = {}
        manager._current_thread_id = None
        yield manager
        ThreadManager.reset()


def test_singleton(temp_manager):
    """测试单例模式"""
    manager1 = temp_manager
    manager2 = ThreadManager()
    assert manager1 is manager2


def test_create_thread(temp_manager):
    """测试创建 thread"""
    thread = temp_manager.create("测试会话", current_cat_id="orange")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "orange"
    assert len(thread.id) == 8


def test_get_thread(temp_manager):
    """测试获取 thread"""
    thread = temp_manager.create("Test")
    fetched = temp_manager.get(thread.id)
    assert fetched is not None
    assert fetched.name == "Test"


def test_list_threads(temp_manager):
    """测试列出 threads"""
    temp_manager.create("Thread 1")
    temp_manager.create("Thread 2")
    threads = temp_manager.list()
    assert len(threads) == 2


def test_list_excludes_archived(temp_manager):
    """测试列出时排除归档"""
    t1 = temp_manager.create("Active")
    t2 = temp_manager.create("Archived")
    temp_manager.archive(t2.id)

    threads = temp_manager.list(include_archived=False)
    assert len(threads) == 1
    assert threads[0].name == "Active"


def test_switch_thread(temp_manager):
    """测试切换 thread"""
    t1 = temp_manager.create("Thread 1")
    t2 = temp_manager.create("Thread 2")

    assert temp_manager.switch(t1.id) is True
    assert temp_manager.get_current().id == t1.id

    assert temp_manager.switch(t2.id) is True
    assert temp_manager.get_current().id == t2.id


def test_switch_nonexistent(temp_manager):
    """测试切换到不存在的 thread"""
    assert temp_manager.switch("nonexistent") is False


def test_rename_thread(temp_manager):
    """测试重命名"""
    thread = temp_manager.create("Old Name")
    assert temp_manager.rename(thread.id, "New Name") is True
    assert temp_manager.get(thread.id).name == "New Name"


def test_delete_thread(temp_manager):
    """测试删除"""
    thread = temp_manager.create("To Delete")
    assert temp_manager.delete(thread.id) is True
    assert temp_manager.get(thread.id) is None


def test_delete_current_thread(temp_manager):
    """测试删除当前 thread"""
    thread = temp_manager.create("Current")
    temp_manager.switch(thread.id)
    temp_manager.delete(thread.id)
    assert temp_manager.get_current() is None


def test_archive_thread(temp_manager):
    """测试归档"""
    thread = temp_manager.create("To Archive")
    assert temp_manager.archive(thread.id) is True
    assert temp_manager.get(thread.id).is_archived is True
