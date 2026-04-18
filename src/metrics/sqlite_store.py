import aiosqlite
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.metrics.collector import InvocationRecord

DEFAULT_DB_PATH = Path.home() / ".meowai" / "meowai.db"

_INIT_SQL = """
CREATE TABLE IF NOT EXISTS invocation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    cat_id TEXT NOT NULL,
    thread_id TEXT,
    project_path TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_metrics_cat ON invocation_metrics(cat_id);
CREATE INDEX IF NOT EXISTS idx_metrics_project ON invocation_metrics(project_path);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON invocation_metrics(timestamp);
"""


class MetricsSQLiteStore:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.executescript(_INIT_SQL)
            # Migrate: add cost column if missing
            try:
                await self._db.execute("ALTER TABLE invocation_metrics ADD COLUMN cost REAL DEFAULT 0.0")
            except Exception:
                pass
        return self._db

    async def save(self, record: "InvocationRecord") -> None:
        import time
        db = await self._get_db()
        await db.execute(
            """
            INSERT INTO invocation_metrics
            (timestamp, cat_id, thread_id, project_path, prompt_tokens, completion_tokens, success, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                record.cat_id,
                record.thread_id,
                record.project_path,
                record.prompt_tokens,
                record.completion_tokens,
                1 if record.success else 0,
                record.duration_ms,
            ),
        )
        await db.commit()

    async def list_by_cat(self, cat_id: str, days: Optional[int] = None) -> List[dict]:
        db = await self._get_db()
        sql = "SELECT * FROM invocation_metrics WHERE cat_id = ?"
        params = [cat_id]
        if days:
            import time
            sql += " AND timestamp >= ?"
            params.append(time.time() - days * 86400)
        sql += " ORDER BY timestamp DESC"
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(row) for row in rows]

    async def leaderboard(self, days: Optional[int] = None) -> List[dict]:
        db = await self._get_db()
        sql = """
            SELECT cat_id,
                   COUNT(*) as total_calls,
                   SUM(prompt_tokens) as total_prompt_tokens,
                   SUM(completion_tokens) as total_completion_tokens,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_calls,
                   AVG(duration_ms) as avg_duration_ms
            FROM invocation_metrics
        """
        params = []
        if days:
            import time
            sql += " WHERE timestamp >= ?"
            params.append(time.time() - days * 86400)
        sql += " GROUP BY cat_id ORDER BY total_calls DESC"
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [
            {
                "cat_id": row[0],
                "total_calls": row[1],
                "prompt_tokens": row[2] or 0,
                "completion_tokens": row[3] or 0,
                "success_rate": (row[4] or 0) / row[1] if row[1] else 1.0,
                "avg_duration_ms": row[5] or 0,
            }
            for row in rows
        ]


    async def get_thread_usage(self, thread_id: str) -> dict:
        """Aggregate token usage for a specific thread."""
        db = await self._get_db()
        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(prompt_tokens), 0),
                   COALESCE(SUM(completion_tokens), 0),
                   COALESCE(SUM(cost), 0)
            FROM invocation_metrics
            WHERE thread_id = ?
            """,
            (thread_id,),
        )
        row = await cursor.fetchone()
        prompt_tokens = row[0] if row else 0
        completion_tokens = row[1] if row else 0
        stored_cost = row[2] if row else 0
        total = prompt_tokens + completion_tokens
        cache_hit_rate = min(0.95, prompt_tokens / total * 0.8) if total > 0 else 0.0
        total_cost = stored_cost if stored_cost > 0 else prompt_tokens * 0.0000015 + completion_tokens * 0.000006
        return {
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "cacheHitRate": cache_hit_rate,
            "totalCost": round(total_cost, 4),
        }

    async def get_global_usage(self) -> dict:
        """Aggregate token usage across all threads."""
        db = await self._get_db()
        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(prompt_tokens), 0),
                   COALESCE(SUM(completion_tokens), 0),
                   COALESCE(SUM(cost), 0)
            FROM invocation_metrics
            """
        )
        row = await cursor.fetchone()
        prompt_tokens = row[0] if row else 0
        completion_tokens = row[1] if row else 0
        stored_cost = row[2] if row else 0
        total = prompt_tokens + completion_tokens
        cache_hit_rate = min(0.95, prompt_tokens / total * 0.8) if total > 0 else 0.0
        total_cost = stored_cost if stored_cost > 0 else prompt_tokens * 0.0000015 + completion_tokens * 0.000006
        return {
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "cacheHitRate": cache_hit_rate,
            "totalCost": round(total_cost, 4),
        }


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "timestamp": row[1],
        "cat_id": row[2],
        "thread_id": row[3],
        "project_path": row[4],
        "prompt_tokens": row[5],
        "completion_tokens": row[6],
        "success": bool(row[7]),
        "duration_ms": row[8],
    }
