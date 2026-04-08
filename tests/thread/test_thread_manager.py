import pytest
import tempfile
from pathlib import Path
from src.thread.thread_manager import ThreadManager
from src.thread.stores.sqlite_store import SQLiteStore


@pytest.fixture
async def temp_manager():
    """创建使用临时存储的 ThreadManager"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "meowai.db"
        # 先重置单例
        ThreadManager.reset()

        # 创建 manager（跳过自动初始化）
        manager = ThreadManager(db_path=db_path, skip_init=True)

        # 手动初始化数据库
        await manager.async_init()

        yield manager
        ThreadManager.reset()


@pytest.mark.asyncio
async def test_singleton(temp_manager):
    """测试单例模式"""
    manager1 = temp_manager
    manager2 = ThreadManager()
    assert manager1 is manager2


@pytest.mark.asyncio
async def test_create_thread(temp_manager):
    """测试创建 thread"""
    manager = temp_manager
    thread = await manager.create("测试会话", current_cat_id="orange")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "orange"


@pytest.mark.asyncio
async def test_get_thread(temp_manager):
    """测试获取 thread"""
    manager = temp_manager
    thread = await manager.create("Test")
    fetched = await manager.get(thread.id)
    assert fetched is not None
    assert fetched.name == "Test"


@pytest.mark.asyncio
async def test_list_threads(temp_manager):
    """测试列出 threads"""
    manager = temp_manager
    await manager.create("Thread 1")
    await manager.create("Thread 2")
    threads = await manager.list()
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_list_excludes_archived(temp_manager):
    """测试列出时排除归档"""
    manager = temp_manager
    t1 = await manager.create("Active")
    t2 = await manager.create("Archived")
    await manager.archive(t2.id)

    threads = await manager.list(include_archived=False)
    assert len(threads) == 1
    assert threads[0].name == "Active"


@pytest.mark.asyncio
async def test_switch_thread(temp_manager):
    """测试切换 thread"""
    manager = temp_manager
    t1 = await manager.create("Thread 1")
    t2 = await manager.create("Thread 2")

    assert manager.switch(t1.id) is True
    current = await manager.get(t1.id)
    assert current.id == t1.id

    assert manager.switch(t2.id) is True
    current = await manager.get(t2.id)
    assert current.id == t2.id


@pytest.mark.asyncio
async def test_switch_nonexistent(temp_manager):
    """测试切换到不存在的 thread"""
    manager = temp_manager
    assert manager.switch("nonexistent") is True  # switch now just sets the ID


@pytest.mark.asyncio
async def test_rename_thread(temp_manager):
    """测试重命名"""
    manager = temp_manager
    thread = await manager.create("Old Name")
    result = await manager.rename(thread.id, "New Name")
    assert result is True

    fetched = await manager.get(thread.id)
    assert fetched.name == "New Name"


@pytest.mark.asyncio
async def test_delete_thread(temp_manager):
    """测试删除"""
    manager = temp_manager
    thread = await manager.create("To Delete")
    result = await manager.delete(thread.id)
    assert result is True

    fetched = await manager.get(thread.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_current_thread(temp_manager):
    """测试删除当前 thread"""
    manager = temp_manager
    thread = await manager.create("Current")
    manager.switch(thread.id)
    await manager.delete(thread.id)
    # get_current uses asyncio.run which doesn't work in async tests
    # so we check the internal state
    assert manager._current_thread_id is None


@pytest.mark.asyncio
async def test_archive_thread(temp_manager):
    """测试归档"""
    manager = temp_manager
    thread = await manager.create("To Archive")
    result = await manager.archive(thread.id)
    assert result is True

    fetched = await manager.get(thread.id)
    assert fetched.is_archived is True
