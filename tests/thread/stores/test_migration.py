import pytest
import tempfile
from pathlib import Path

from src.thread.models import Thread
from src.thread.persistence import ThreadPersistence
from src.thread.stores.sqlite_store import SQLiteStore
from src.thread.stores.migration import migrate_json_to_sqlite, check_needs_migration


@pytest.mark.asyncio
async def test_migration():
    """测试数据迁移"""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "threads.json"
        sqlite_path = Path(tmpdir) / "meowai.db"

        # 创建 JSON 数据
        store = ThreadPersistence(json_path)
        thread = Thread.create("Test Thread", current_cat_id="orange")
        thread.add_message("user", "Hello")
        store.save({thread.id: thread})

        # 迁移
        count = await migrate_json_to_sqlite(json_path, sqlite_path)
        assert count == 1

        # 验证 SQLite 数据
        sqlite_store = SQLiteStore(sqlite_path)
        await sqlite_store.initialize()

        migrated = await sqlite_store.get_thread(thread.id)
        assert migrated.name == "Test Thread"
        assert len(migrated.messages) == 1


@pytest.mark.asyncio
async def test_check_needs_migration():
    """测试迁移检测"""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "threads.json"
        sqlite_path = Path(tmpdir) / "meowai.db"

        # 只有 JSON，需要迁移
        json_path.write_text('{"version": 1, "threads": {}}')
        assert check_needs_migration(sqlite_path) is True

        # 创建 SQLite 后，不需要迁移
        sqlite_path.write_text("")
        assert check_needs_migration(sqlite_path) is False
