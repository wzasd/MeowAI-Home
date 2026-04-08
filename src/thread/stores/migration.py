import json
from pathlib import Path
from typing import Optional

from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence
from src.thread.stores.sqlite_store import SQLiteStore


async def migrate_json_to_sqlite(
    json_path: Optional[Path] = None,
    sqlite_path: Optional[Path] = None
) -> int:
    """从 JSON 迁移到 SQLite

    Returns:
        迁移的 thread 数量
    """
    # 加载 JSON
    json_store = ThreadPersistence(json_path)
    threads, _ = json_store.load()

    if not threads:
        return 0

    # 初始化 SQLite
    sqlite_store = SQLiteStore(sqlite_path)
    await sqlite_store.initialize()

    # 迁移每个 thread
    count = 0
    for thread in threads.values():
        await sqlite_store.save_thread(thread)
        # 迁移消息
        for msg in thread.messages:
            await sqlite_store.add_message(thread.id, msg)
        count += 1

    return count


def check_needs_migration(sqlite_path: Optional[Path] = None) -> bool:
    """检查是否需要迁移"""
    sqlite_path = sqlite_path or SQLiteStore().db_path
    json_path = ThreadPersistence().storage_path

    # 如果 SQLite 不存在但 JSON 存在，需要迁移
    return not sqlite_path.exists() and json_path.exists()
