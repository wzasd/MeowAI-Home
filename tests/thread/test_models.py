import pytest
from datetime import datetime
from src.thread.models import Message, Thread


def test_message_creation():
    """测试消息创建"""
    msg = Message(role="user", content="Hello", cat_id=None)
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.cat_id is None
    assert isinstance(msg.timestamp, datetime)


def test_message_to_dict():
    """测试消息序列化"""
    msg = Message(role="assistant", content="Hi", cat_id="orange")
    data = msg.to_dict()
    assert data["role"] == "assistant"
    assert data["content"] == "Hi"
    assert data["cat_id"] == "orange"
    assert "timestamp" in data


def test_message_from_dict():
    """测试消息反序列化"""
    data = {
        "role": "user",
        "content": "Test",
        "cat_id": None,
        "timestamp": datetime.now().isoformat()
    }
    msg = Message.from_dict(data)
    assert msg.role == "user"
    assert msg.content == "Test"


def test_thread_create():
    """测试 thread 创建"""
    thread = Thread.create("测试会话", current_cat_id="inky")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "inky"
    assert len(thread.id) == 8  # 短ID
    assert len(thread.messages) == 0
    assert thread.is_archived is False
    assert thread.project_path == ""


def test_thread_create_with_project_path():
    """测试 thread 创建带 project_path"""
    thread = Thread.create("测试会话", current_cat_id="inky", project_path="/path/to/project")
    assert thread.name == "测试会话"
    assert thread.current_cat_id == "inky"
    assert thread.project_path == "/path/to/project"
    assert len(thread.id) == 8
    assert len(thread.messages) == 0


def test_thread_add_message():
    """测试添加消息"""
    thread = Thread.create("Test")
    thread.add_message("user", "Hello")
    thread.add_message("assistant", "Hi", cat_id="orange")

    assert len(thread.messages) == 2
    assert thread.messages[0].role == "user"
    assert thread.messages[1].cat_id == "orange"


def test_thread_to_dict():
    """测试 thread 序列化"""
    thread = Thread.create("Test")
    thread.add_message("user", "Hello")
    data = thread.to_dict()

    assert data["name"] == "Test"
    assert data["current_cat_id"] == "orange"
    assert len(data["messages"]) == 1
    assert "id" in data
    # project_path is empty, so it should not be included
    assert "project_path" not in data


def test_thread_to_dict_with_project_path():
    """测试 thread 序列化带 project_path"""
    thread = Thread.create("Test", project_path="/path/to/project")
    data = thread.to_dict()

    assert data["name"] == "Test"
    assert data["project_path"] == "/path/to/project"


def test_thread_from_dict():
    """测试 thread 反序列化"""
    data = {
        "id": "abc123",
        "name": "Test Thread",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [
            {"role": "user", "content": "Hi", "cat_id": None, "timestamp": datetime.now().isoformat()}
        ],
        "current_cat_id": "patch",
        "is_archived": False
    }
    thread = Thread.from_dict(data)
    assert thread.id == "abc123"
    assert thread.name == "Test Thread"
    assert thread.current_cat_id == "patch"
    assert len(thread.messages) == 1
    assert thread.project_path == ""


def test_thread_from_dict_with_project_path():
    """测试 thread 反序列化带 project_path"""
    data = {
        "id": "abc123",
        "name": "Test Thread",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "current_cat_id": "patch",
        "is_archived": False,
        "project_path": "/path/to/repo"
    }
    thread = Thread.from_dict(data)
    assert thread.id == "abc123"
    assert thread.project_path == "/path/to/repo"


def test_message_from_dict_missing_fields():
    """测试消息反序列化缺少字段"""
    data = {"role": "user", "content": "Test"}  # 缺少 timestamp
    with pytest.raises(ValueError, match="missing required fields"):
        Message.from_dict(data)


def test_message_from_dict_invalid_role():
    """测试消息反序列化无效 role"""
    data = {
        "role": "hacker",
        "content": "Test",
        "timestamp": datetime.now().isoformat()
    }
    with pytest.raises(ValueError, match="Invalid role"):
        Message.from_dict(data)


def test_add_message_invalid_role():
    """测试添加消息时无效 role"""
    thread = Thread.create("Test")
    with pytest.raises(ValueError, match="Invalid role"):
        thread.add_message("invalid", "content")
