"""SQLite-backed vector store with cosine similarity search"""
import math
import sqlite3
import struct
from typing import List, Optional, Tuple

from src.search.embedding import EmbeddingProvider, create_embedding_provider
from src.search.cache import EmbeddingCache


class VectorStore:
    """Store and search embedding vectors in SQLite.

    Uses BLOB storage for vectors with Python-side cosine similarity.
    Supports embedding caching to avoid recomputation.
    Gracefully degrades — no external vector DB required.
    """

    def __init__(
        self,
        db_path: str,
        provider: Optional[EmbeddingProvider] = None,
        cache_db_path: Optional[str] = None,
        use_cache: bool = True,
    ):
        self.db_path = db_path
        self.provider = provider or create_embedding_provider()
        self._cache: Optional[EmbeddingCache] = None

        if use_cache:
            cache_path = cache_db_path or db_path
            self._cache = EmbeddingCache(
                cache_path,
                provider_name=self.provider.__class__.__name__,
                dimension=self.provider.dimension(),
            )

        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT NOT NULL,
            content_type TEXT NOT NULL,
            content_text TEXT NOT NULL,
            embedding BLOB,
            UNIQUE(content_id, content_type)
        )""")
        conn.commit()
        conn.close()

    async def upsert(self, content_id: str, content_type: str, text: str):
        """Store or update embedding for a content item."""
        # Check cache first
        vec = None
        if self._cache:
            vec = self._cache.get(text)

        if vec is None:
            vec = await self.provider.embed(text)
            if self._cache:
                self._cache.set(text, vec)

        blob = struct.pack(f'{len(vec)}f', *vec)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO vectors (content_id, content_type, content_text, embedding)
            VALUES (?, ?, ?, ?)
        """, (content_id, content_type, text, blob))
        conn.commit()
        conn.close()

    async def search(self, query: str, content_type: Optional[str] = None,
                     limit: int = 10) -> List[Tuple[str, str, float]]:
        """Search by cosine similarity.

        Returns: [(content_id, content_text, score)]
        """
        # Check cache for query embedding
        query_vec = None
        if self._cache:
            query_vec = self._cache.get(query)

        if query_vec is None:
            query_vec = await self.provider.embed(query)
            if self._cache:
                self._cache.set(query, query_vec)
        conn = sqlite3.connect(self.db_path)

        if content_type:
            rows = conn.execute(
                "SELECT content_id, content_text, embedding FROM vectors WHERE content_type = ?",
                (content_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT content_id, content_text, embedding FROM vectors"
            ).fetchall()
        conn.close()

        results = []
        for row in rows:
            blob = row[2]
            if not blob:
                continue
            dim = len(blob) // 4
            vec = list(struct.unpack(f'{dim}f', blob))
            score = _cosine_similarity(query_vec, vec)
            results.append((row[0], row[1], score))

        results.sort(key=lambda x: x[2], reverse=True)
        return results[:limit]

    def delete(self, content_id: str, content_type: str) -> bool:
        """Delete a vector by content_id + content_type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "DELETE FROM vectors WHERE content_id = ? AND content_type = ?",
            (content_id, content_type),
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted

    def cache_stats(self) -> Optional[dict]:
        """Get embedding cache statistics."""
        if self._cache:
            return self._cache.stats()
        return None

    def clear_cache(self) -> bool:
        """Clear embedding cache."""
        if self._cache:
            self._cache.clear()
            return True
        return False

    def get_provider_info(self) -> dict:
        """Get information about current embedding provider."""
        return {
            "type": self.provider.__class__.__name__,
            "dimension": self.provider.dimension(),
            "has_cache": self._cache is not None,
        }


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
