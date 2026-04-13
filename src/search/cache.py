"""Embedding cache to avoid recomputing embeddings for same text."""
import hashlib
import sqlite3
import struct
from typing import List, Optional


class EmbeddingCache:
    """SQLite-based embedding cache.

    Caches text -> embedding mappings to avoid re-computing
    expensive API calls for frequently accessed content.
    """

    def __init__(self, db_path: str, provider_name: str, dimension: int):
        self.db_path = db_path
        self.provider_name = provider_name
        self.dimension = dimension
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                text_hash TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                text_preview TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_provider
            ON embedding_cache(provider)
        """)
        conn.commit()
        conn.close()

    def _hash_text(self, text: str) -> str:
        """Generate hash for text lookup."""
        return hashlib.sha256(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if exists."""
        text_hash = self._hash_text(text)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT embedding FROM embedding_cache WHERE text_hash = ? AND provider = ?",
            (text_hash, self.provider_name)
        ).fetchone()
        conn.close()

        if row:
            blob = row[0]
            dim = len(blob) // 4
            return list(struct.unpack(f'{dim}f', blob))
        return None

    def set(self, text: str, embedding: List[float]):
        """Cache embedding for text."""
        text_hash = self._hash_text(text)
        preview = text[:200]  # Store preview for debugging
        blob = struct.pack(f'{len(embedding)}f', *embedding)

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO embedding_cache
               (text_hash, provider, text_preview, embedding)
               VALUES (?, ?, ?, ?)""",
            (text_hash, self.provider_name, preview, blob)
        )
        conn.commit()
        conn.close()

    def invalidate(self, text: str) -> bool:
        """Remove cached entry for text."""
        text_hash = self._hash_text(text)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM embedding_cache WHERE text_hash = ? AND provider = ?",
            (text_hash, self.provider_name)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def clear(self):
        """Clear all cached embeddings for this provider."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM embedding_cache WHERE provider = ?", (self.provider_name,))
        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        total = conn.execute(
            "SELECT COUNT(*) FROM embedding_cache WHERE provider = ?",
            (self.provider_name,)
        ).fetchone()[0]
        oldest = conn.execute(
            "SELECT MIN(created_at) FROM embedding_cache WHERE provider = ?",
            (self.provider_name,)
        ).fetchone()[0]
        conn.close()
        return {"total_entries": total, "oldest_entry": oldest}
