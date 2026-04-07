from datetime import datetime
from src.data.models import Message, Thread, Role


def test_message_creation():
    msg = Message(
        role=Role.USER,
        content="你好阿橘"
    )
    assert msg.role == Role.USER
    assert msg.content == "你好阿橘"
    assert isinstance(msg.timestamp, datetime)


def test_thread_creation():
    thread = Thread(title="测试对话")
    assert thread.title == "测试对话"
    assert len(thread.messages) == 0


def test_thread_add_message():
    thread = Thread(title="测试对话")
    msg = Message(role=Role.USER, content="你好")
    thread.add_message(msg)
    assert len(thread.messages) == 1
    assert thread.messages[0].content == "你好"
