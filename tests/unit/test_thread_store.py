import pytest
from src.data.thread_store import ThreadStore
from src.data.models import Thread, Message, Role


@pytest.mark.asyncio
async def test_create_thread():
    store = ThreadStore(":memory:")
    try:
        thread = Thread(title="测试对话")
        await store.save_thread(thread)
        loaded = await store.get_thread(thread.id)
        assert loaded is not None
        assert loaded.title == "测试对话"
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_save_and_load_messages():
    store = ThreadStore(":memory:")
    try:
        thread = Thread(title="测试对话")
        msg = Message(role=Role.USER, content="你好")
        thread.add_message(msg)
        await store.save_thread(thread)

        loaded = await store.get_thread(thread.id)
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "你好"
    finally:
        await store.close()
