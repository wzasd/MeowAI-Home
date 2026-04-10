"""MCP 记忆存储 — 基于 SQLite 的简单键值记忆"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryStore:
    """项目记忆存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path.home() / ".meowai" / "memory.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (key, category)
            )
        """)
        conn.commit()
        conn.close()

    async def save(self, key: str, value: str, category: str = "general") -> Dict[str, Any]:
        """保存记忆"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO memories (key, value, category, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (key, value, category))
        conn.commit()
        conn.close()
        return {"status": "saved", "key": key, "category": category}

    async def query(
        self,
        key: str = None,
        category: str = None
    ) -> Dict[str, Any]:
        """查询记忆"""
        conn = sqlite3.connect(self.db_path)

        if key:
            rows = conn.execute(
                "SELECT key, value, category, updated_at FROM memories WHERE key = ?",
                (key,)
            ).fetchall()
        elif category:
            rows = conn.execute(
                "SELECT key, value, category, updated_at FROM memories WHERE category = ? ORDER BY updated_at DESC LIMIT 20",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value, category, updated_at FROM memories ORDER BY updated_at DESC LIMIT 20"
            ).fetchall()

        conn.close()

        results = [
            {"key": r[0], "value": r[1], "category": r[2], "updated_at": r[3]}
            for r in rows
        ]
        return {"results": results, "total": len(results)}

    async def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """搜索记忆（模糊匹配）"""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT key, value, category, updated_at FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", max_results)
        ).fetchall()
        conn.close()

        results = [
            {"key": r[0], "value": r[1], "category": r[2], "updated_at": r[3]}
            for r in rows
        ]
        return {"results": results, "total": len(results)}

    async def delete(self, key: str, category: str = "general") -> Dict[str, Any]:
        """删除记忆"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM memories WHERE key = ? AND category = ?",
            (key, category)
        )
        conn.commit()
        conn.close()
        return {"status": "deleted", "key": key}
