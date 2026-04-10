"""Pack store for persisting pack activations"""
import json
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime


class PackStore:
    """Persist pack activations to SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pack_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_name TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                agents TEXT,  -- JSON array of cat_ids
                UNIQUE(pack_name, thread_id)
            )
        """)
        conn.commit()
        conn.close()

    def activate(self, pack_name: str, thread_id: str, agents: List[str]) -> int:
        """Activate a pack for a thread. Returns activation ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT OR REPLACE INTO pack_activations
               (pack_name, thread_id, agents) VALUES (?, ?, ?)""",
            (pack_name, thread_id, json.dumps(agents))
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id

    def deactivate(self, pack_name: str, thread_id: str) -> bool:
        """Deactivate a pack for a thread. Returns True if found."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM pack_activations WHERE pack_name = ? AND thread_id = ?",
            (pack_name, thread_id)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def get_active(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all active packs for a thread."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM pack_activations WHERE thread_id = ? ORDER BY activated_at DESC",
            (thread_id,)
        ).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "pack_name": row["pack_name"],
                "thread_id": row["thread_id"],
                "activated_at": row["activated_at"],
                "agents": json.loads(row["agents"]) if row["agents"] else [],
            })
        return results

    def is_active(self, pack_name: str, thread_id: str) -> bool:
        """Check if a pack is active for a thread."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT 1 FROM pack_activations WHERE pack_name = ? AND thread_id = ?",
            (pack_name, thread_id)
        ).fetchone()
        conn.close()
        return row is not None

    def list_all_active(self) -> List[Dict[str, Any]]:
        """List all active pack activations across all threads."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM pack_activations ORDER BY activated_at DESC"
        ).fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "pack_name": row["pack_name"],
                "thread_id": row["thread_id"],
                "activated_at": row["activated_at"],
                "agents": json.loads(row["agents"]) if row["agents"] else [],
            })
        return results
