import pytest
import tempfile
from pathlib import Path
from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence


def test_persistence_save_and_load():
    """测试保存和加载"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        persistence = ThreadPersistence(storage_path)

        # 创建 thread
        thread = Thread.create("测试会话", current_cat_id="orange")
        thread.add_message("user", "Hello")
        threads = {thread.id: thread}

        # 保存
        persistence.save(threads)
        assert persistence.exists()

        # 加载
        loaded, current_id = persistence.load()
        assert len(loaded) == 1
        assert thread.id in loaded
        assert loaded[thread.id].name == "测试会话"
        assert len(loaded[thread.id].messages) == 1


def test_persistence_load_empty():
    """测试加载不存在的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        persistence = ThreadPersistence(storage_path)

        loaded, current_id = persistence.load()
        assert loaded == {}
        assert current_id is None
        assert not persistence.exists()


def test_persistence_multiple_threads():
    """测试多个 threads"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        persistence = ThreadPersistence(storage_path)

        t1 = Thread.create("会话1", current_cat_id="orange")
        t2 = Thread.create("会话2", current_cat_id="inky")
        threads = {t1.id: t1, t2.id: t2}

        persistence.save(threads)
        loaded, current_id = persistence.load()

        assert len(loaded) == 2
        assert loaded[t1.id].current_cat_id == "orange"
        assert loaded[t2.id].current_cat_id == "inky"


def test_persistence_corrupted_file():
    """测试损坏的文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "threads.json"
        storage_path.write_text("invalid json")
        persistence = ThreadPersistence(storage_path)

        loaded, current_id = persistence.load()
        assert loaded == {}  # 返回空而不是崩溃
        assert current_id is None
