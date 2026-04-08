import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.thread.models import Thread, Message
from src.thread.stores.sqlite_store import SQLiteStore


@pytest.fixture
def store():
    """创建临时 store - 每个测试使用独立的事件循环"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SQLiteStore(db_path)

        # 创建新的事件循环来初始化
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(store.initialize())
        finally:
            loop.close()

        yield store

        # 清理：关闭连接
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(store.close())
        finally:
            loop.close()


@pytest.mark.asyncio
async def test_save_and_get_thread(store):
    """测试保存和获取 thread"""
    thread = Thread.create("测试", current_cat_id="orange")
    await store.save_thread(thread)

    fetched = await store.get_thread(thread.id)
    assert fetched is not None
    assert fetched.name == "测试"
    assert fetched.current_cat_id == "orange"


@pytest.mark.asyncio
async def test_list_threads(store):
    """测试列出 threads"""
    t1 = Thread.create("Thread 1")
    t2 = Thread.create("Thread 2")
    await store.save_thread(t1)
    await store.save_thread(t2)

    threads = await store.list_threads()
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_add_and_get_messages(store):
    """测试消息存储"""
    thread = Thread.create("Test")
    await store.save_thread(thread)

    msg = Message(role="user", content="Hello", cat_id=None)
    await store.add_message(thread.id, msg)

    messages = await store.get_messages(thread.id)
    assert len(messages) == 1
    assert messages[0].content == "Hello"


@pytest.mark.asyncio
async def test_search_messages(store):
    """测试消息搜索"""
    thread = Thread.create("Test")
    await store.save_thread(thread)

    await store.add_message(thread.id, Message(role="user", content="Hello world"))
    await store.add_message(thread.id, Message(role="assistant", content="Goodbye"))

    results = await store.search_messages(thread.id, "Hello")
    assert len(results) == 1
    assert results[0].content == "Hello world"
