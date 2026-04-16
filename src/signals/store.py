"""Article store — SQLite persistence for fetched articles with FTS search."""

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.signals.fetchers import FetchedArticle
from src.signals.sources import SourceTier


class ArticleStore:
    """Persistent storage for articles with deduplication and search."""

    def __init__(self, db_path: str = "data/articles.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Articles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    source_id TEXT,
                    author TEXT,
                    summary TEXT,
                    published_at TEXT,
                    fetched_at TEXT NOT NULL,
                    status TEXT DEFAULT 'unread',
                    metadata TEXT,
                    tier TEXT DEFAULT 'p2'
                )
            """)

            # Full-text search virtual table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                    title,
                    content,
                    content_row_id
                )
            """)

            # Index for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_hash
                ON articles(content_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_source
                ON articles(source_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_status
                ON articles(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_fetched
                ON articles(fetched_at)
            """)

            # Migrate: add notes column if missing
            try:
                conn.execute("ALTER TABLE articles ADD COLUMN notes TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.commit()

    def get_notes(self, article_id: int) -> str:
        """Get study notes for an article."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT notes FROM articles WHERE id = ?",
                (article_id,)
            )
            row = cursor.fetchone()
            return row[0] or "" if row else ""

    def save_notes(self, article_id: int, notes: str) -> bool:
        """Save study notes for an article."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE articles SET notes = ? WHERE id = ?",
                (notes, article_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def store(self, article: FetchedArticle, tier: SourceTier = SourceTier.P2) -> bool:
        """Store an article, returns True if new, False if duplicate."""
        content_hash = article.content_hash

        with sqlite3.connect(self.db_path) as conn:
            # Check for duplicate
            cursor = conn.execute(
                "SELECT id FROM articles WHERE content_hash = ?",
                (content_hash,)
            )
            if cursor.fetchone():
                return False

            # Insert article
            cursor = conn.execute(
                """
                INSERT INTO articles (
                    url, title, content, content_hash, source_id,
                    author, summary, published_at, fetched_at, status, metadata, tier
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.url,
                    article.title,
                    article.content,
                    content_hash,
                    article.source_id,
                    article.author,
                    article.summary,
                    article.published_at.isoformat() if article.published_at else None,
                    datetime.utcnow().isoformat(),
                    'unread',
                    json.dumps(article.metadata) if article.metadata else None,
                    tier.value
                )
            )
            row_id = cursor.lastrowid

            # Insert into FTS index
            conn.execute(
                "INSERT INTO articles_fts (title, content, content_row_id) VALUES (?, ?, ?)",
                (article.title, article.content, row_id)
            )

            conn.commit()
            return True

    def store_many(self, articles: List[FetchedArticle], tier: SourceTier = SourceTier.P2) -> int:
        """Store multiple articles, return count of new articles."""
        count = 0
        for article in articles:
            if self.store(article, tier):
                count += 1
        return count

    def get_by_hash(self, content_hash: str) -> Optional[Dict]:
        """Get article by content hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE content_hash = ?",
                (content_hash,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_by_id(self, article_id: int) -> Optional[Dict]:
        """Get article by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM articles WHERE id = ?",
                (article_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_recent(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List most recent articles."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM articles
                ORDER BY fetched_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_by_source(self, source_id: str, limit: int = 50) -> List[Dict]:
        """List articles from a specific source."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM articles
                WHERE source_id = ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (source_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_by_status(self, status: str, limit: int = 50) -> List[Dict]:
        """List articles by status (unread, read, archived)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM articles
                WHERE status = ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (status, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_by_tier(self, tier: SourceTier, limit: int = 50) -> List[Dict]:
        """List articles by source tier."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM articles
                WHERE tier = ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (tier.value, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Full-text search articles."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Use FTS5 for ranked search
            cursor = conn.execute(
                """
                SELECT a.*, rank
                FROM articles_fts fts
                JOIN articles a ON a.id = fts.content_row_id
                WHERE articles_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_status(self, article_id: int, status: str) -> bool:
        """Update article status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE articles SET status = ? WHERE id = ?",
                (status, article_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def mark_read(self, article_id: int) -> bool:
        """Mark article as read."""
        return self.update_status(article_id, 'read')

    def mark_archived(self, article_id: int) -> bool:
        """Mark article as archived."""
        return self.update_status(article_id, 'archived')

    def delete(self, article_id: int) -> bool:
        """Delete an article."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete from FTS first
            conn.execute(
                "DELETE FROM articles_fts WHERE content_row_id = ?",
                (article_id,)
            )
            cursor = conn.execute(
                "DELETE FROM articles WHERE id = ?",
                (article_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_existing_hashes(self, hashes: Set[str]) -> Set[str]:
        """Check which hashes already exist in database."""
        if not hashes:
            return set()

        with sqlite3.connect(self.db_path) as conn:
            placeholders = ','.join('?' * len(hashes))
            cursor = conn.execute(
                f"SELECT content_hash FROM articles WHERE content_hash IN ({placeholders})",
                tuple(hashes)
            )
            return {row[0] for row in cursor.fetchall()}

    def get_stats(self) -> Dict:
        """Get article statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
            unread = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE status = 'unread'"
            ).fetchone()[0]
            by_tier = {}
            for tier in SourceTier:
                count = conn.execute(
                    "SELECT COUNT(*) FROM articles WHERE tier = ?",
                    (tier.value,)
                ).fetchone()[0]
                by_tier[tier.value] = count

            return {
                "total": total,
                "unread": unread,
                "read": total - unread,
                "by_tier": by_tier
            }
