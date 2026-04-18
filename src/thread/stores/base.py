from abc import ABC, abstractmethod
from typing import List, Optional
from src.thread.models import Thread, Message


class ThreadStore(ABC):
    """Thread 存储抽象接口"""

    @abstractmethod
    async def save_thread(self, thread: Thread) -> None:
        """保存或更新 thread"""
        pass

    @abstractmethod
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """获取指定 thread"""
        pass

    @abstractmethod
    async def list_threads(self, include_archived: bool = False) -> List[Thread]:
        """列出所有 threads"""
        pass

    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """删除 thread"""
        pass

    @abstractmethod
    async def search_threads(self, query: str) -> List[Thread]:
        """搜索 threads"""
        pass


class MessageStore(ABC):
    """Message 存储抽象接口"""

    @abstractmethod
    async def add_message(self, thread_id: str, message: Message) -> None:
        """添加消息"""
        pass

    @abstractmethod
    async def get_messages(self, thread_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """分页获取消息"""
        pass

    @abstractmethod
    async def delete_message(self, thread_id: str, message_id: str) -> bool:
        """删除消息"""
        pass

    @abstractmethod
    async def update_message(self, thread_id: str, message_id: str, content: str) -> bool:
        """更新消息内容"""
        pass

    @abstractmethod
    async def search_messages(self, thread_id: str, query: str) -> List[Message]:
        """搜索消息内容"""
        pass
