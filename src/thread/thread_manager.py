from typing import Dict, List, Optional
from datetime import datetime, timezone
from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence


class ThreadManager:
    """Thread 管理器（单例）"""

    _instance: Optional["ThreadManager"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ThreadManager._initialized:
            return

        self._threads: Dict[str, Thread] = {}
        self._current_thread_id: Optional[str] = None
        self._persistence = ThreadPersistence()

        # 从磁盘加载
        self._load()

        ThreadManager._initialized = True

    def _load(self):
        """从磁盘加载 threads"""
        self._threads = self._persistence.load()

    def _save(self):
        """保存到磁盘"""
        self._persistence.save(self._threads)

    def create(self, name: str, current_cat_id: str = "orange") -> Thread:
        """创建新 thread"""
        thread = Thread.create(name, current_cat_id)
        self._threads[thread.id] = thread
        self._save()
        return thread

    def get(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        return self._threads.get(thread_id)

    def list(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        threads = list(self._threads.values())
        if not include_archived:
            threads = [t for t in threads if not t.is_archived]
        # 按更新时间倒序
        return sorted(threads, key=lambda t: t.updated_at, reverse=True)

    def switch(self, thread_id: str) -> bool:
        """切换到指定 thread"""
        if thread_id in self._threads:
            self._current_thread_id = thread_id
            return True
        return False

    def get_current(self) -> Optional[Thread]:
        """获取当前 thread"""
        if self._current_thread_id:
            return self._threads.get(self._current_thread_id)
        return None

    def rename(self, thread_id: str, new_name: str) -> bool:
        """重命名 thread"""
        if thread_id in self._threads:
            self._threads[thread_id].name = new_name
            self._threads[thread_id].updated_at = datetime.now(timezone.utc)
            self._save()
            return True
        return False

    def delete(self, thread_id: str) -> bool:
        """删除 thread"""
        if thread_id in self._threads:
            del self._threads[thread_id]
            if self._current_thread_id == thread_id:
                self._current_thread_id = None
            self._save()
            return True
        return False

    def archive(self, thread_id: str) -> bool:
        """归档 thread"""
        if thread_id in self._threads:
            self._threads[thread_id].is_archived = True
            self._save()
            return True
        return False

    def update_thread(self, thread: Thread):
        """更新 thread（保存修改）"""
        if thread.id in self._threads:
            self._threads[thread.id] = thread
            self._save()

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
        cls._initialized = False
