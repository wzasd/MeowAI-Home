"""Evidence store — SQLite persistence for project knowledge with FTS search."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class EvidenceDoc:
    """Evidence document."""
    id: int = 0
    title: str = ""
    anchor: str = ""       # file path or URL
    summary: str = ""
    content: str = ""
    kind: str = "discussion"  # decision, plan, discussion, commit
    source: str = ""        # project path or thread id
    confidence: str = "mid"  # high, mid, low
    status: str = "published"  # draft, pending, published, archived
    created_at: str = ""
    updated_at: str = ""


class EvidenceStore:
    """Persistent storage for evidence documents with full-text search."""

    def __init__(self, db_path: str = "data/evidence.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_docs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    anchor TEXT,
                    summary TEXT,
                    content TEXT,
                    kind TEXT DEFAULT 'discussion',
                    source TEXT,
                    confidence TEXT DEFAULT 'mid',
                    status TEXT DEFAULT 'published',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
                    title,
                    content,
                    content_row_id
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evidence_kind
                ON evidence_docs(kind)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evidence_source
                ON evidence_docs(source)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evidence_status
                ON evidence_docs(status)
            """)
            conn.commit()

    def store(self, doc: EvidenceDoc) -> int:
        """Store an evidence document. Returns row ID."""
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO evidence_docs (
                    title, anchor, summary, content, kind, source,
                    confidence, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.title, doc.anchor, doc.summary, doc.content,
                    doc.kind, doc.source, doc.confidence, doc.status,
                    doc.created_at or now, now,
                ),
            )
            row_id = cursor.lastrowid

            # Insert into FTS index
            conn.execute(
                "INSERT INTO evidence_fts (title, content, content_row_id) VALUES (?, ?, ?)",
                (doc.title, doc.content, row_id),
            )
            conn.commit()
            return row_id

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """Full-text search evidence documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Try FTS5 first
            try:
                cursor = conn.execute(
                    """
                    SELECT d.*, rank
                    FROM evidence_fts fts
                    JOIN evidence_docs d ON d.id = fts.content_row_id
                    WHERE evidence_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (query, limit),
                )
                results = [dict(row) for row in cursor.fetchall()]
                if results:
                    return results
            except sqlite3.OperationalError:
                pass

            # Fallback: LIKE search
            cursor = conn.execute(
                """
                SELECT * FROM evidence_docs
                WHERE title LIKE ? OR content LIKE ? OR summary LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_by_id(self, doc_id: int) -> Optional[dict]:
        """Get document by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM evidence_docs WHERE id = ?",
                (doc_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_recent(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """List recent documents."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evidence_docs
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def list_by_kind(self, kind: str, limit: int = 50) -> List[dict]:
        """List documents by kind."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM evidence_docs
                WHERE kind = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (kind, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete(self, doc_id: int) -> bool:
        """Delete a document."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM evidence_fts WHERE content_row_id = ?",
                (doc_id,),
            )
            cursor = conn.execute(
                "DELETE FROM evidence_docs WHERE id = ?",
                (doc_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_status(self) -> dict:
        """Get evidence store status."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM evidence_docs").fetchone()[0]
            by_kind = {}
            for row in conn.execute(
                "SELECT kind, COUNT(*) as c FROM evidence_docs GROUP BY kind"
            ):
                by_kind[row[0]] = row[1]

            last_updated = None
            row = conn.execute(
                "SELECT MAX(updated_at) FROM evidence_docs"
            ).fetchone()
            if row and row[0]:
                last_updated = row[0]

            return {
                "backend": "sqlite",
                "healthy": True,
                "total": total,
                "by_kind": by_kind,
                "last_updated": last_updated,
            }
