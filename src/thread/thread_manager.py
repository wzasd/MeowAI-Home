from typing import Dict, List, Optional
from datetime import datetime, timezone
import asyncio

from src.thread.models import Thread, Message
from src.thread.stores.sqlite_store import SQLiteStore
from src.thread.stores.migration import check_needs_migration, migrate_json_to_sqlite


class ThreadManager:
    """Thread 管理器（单例）"""

    _instance: Optional["ThreadManager"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path=None, skip_init=False):
        """
        Args:
            db_path: 可选的数据库路径（用于测试）
            skip_init: 如果为 True，跳过数据库初始化（用于测试，此时应在异步上下文中手动初始化）
        """
        if ThreadManager._initialized:
            return

        self._store = SQLiteStore(db_path)
        self._current_thread_id: Optional[str] = None
        self._needs_async_init = False

        # 初始化数据库
        if not skip_init:
            try:
                loop = asyncio.get_running_loop()
                # 如果在运行中的事件循环中（如测试），需要外部初始化
                self._needs_async_init = True
            except RuntimeError:
                # 没有运行的事件循环，可以安全使用 asyncio.run
                asyncio.run(self._init_db())

        ThreadManager._initialized = True

    async def async_init(self):
        """异步初始化（用于测试或在异步上下文中）"""
        await self._init_db()
        self._needs_async_init = False

    async def _init_db(self):
        """初始化数据库"""
        # 检查是否需要迁移
        if check_needs_migration():
            print("🔄 正在从旧格式迁移数据...")
            count = await migrate_json_to_sqlite()
            print(f"✅ 已迁移 {count} 个 threads")

        await self._store.initialize()

    async def create(self, name: str, current_cat_id: str = "orange") -> Thread:
        """创建新 thread"""
        thread = Thread.create(name, current_cat_id)
        await self._store.save_thread(thread)
        return thread

    async def get(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        return await self._store.get_thread(thread_id)

    async def list(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        return await self._store.list_threads(include_archived)

    def switch(self, thread_id: str) -> bool:
        """切换到指定 thread"""
        self._current_thread_id = thread_id
        return True

    def get_current(self) -> Optional[Thread]:
        """获取当前 thread（自动处理事件循环）"""
        if not self._current_thread_id:
            return None

        try:
            # 检查是否在运行的事件循环中
            loop = asyncio.get_running_loop()
            # 在已有循环中，使用 nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self._store.get_thread(self._current_thread_id))
        except RuntimeError:
            # 没有运行的事件循环，直接使用 asyncio.run()
            return asyncio.run(self._store.get_thread(self._current_thread_id))

    async def rename(self, thread_id: str, new_name: str) -> bool:
        """重命名 thread"""
        thread = await self._store.get_thread(thread_id)
        if thread:
            thread.name = new_name
            thread.updated_at = datetime.now(timezone.utc)
            await self._store.save_thread(thread)
            return True
        return False

    async def delete(self, thread_id: str) -> bool:
        """删除 thread"""
        if self._current_thread_id == thread_id:
            self._current_thread_id = None
        return await self._store.delete_thread(thread_id)

    async def archive(self, thread_id: str) -> bool:
        """归档 thread"""
        thread = await self._store.get_thread(thread_id)
        if thread:
            thread.is_archived = True
            await self._store.save_thread(thread)
            return True
        return False

    async def update_thread(self, thread: Thread):
        """
        更新 thread（只保存 metadata，不重复添加消息）

        Args:
            thread: 要更新的 thread
        """
        await self._store.save_thread(thread)
        # 注意：不再重复添加所有消息
        # 消息应该通过 add_message() 单独添加，而不是每次更新时重新插入

    async def add_message(self, thread_id: str, message: Message) -> None:
        """
        添加单条消息到 thread

        Args:
            thread_id: thread ID
            message: 要添加的消息
        """
        await self._store.add_message(thread_id, message)

    @classmethod
    def reset(cls):
        """重置单例（测试用）"""
        cls._instance = None
        cls._initialized = False
