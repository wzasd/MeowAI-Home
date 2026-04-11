"""SessionManager — SQLite-backed session lifecycle management."""
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional


class SessionStatus(str, Enum):
    ACTIVE = "active"
    SEALING = "sealing"
    SEALED = "sealed"


@dataclass
class Session:
    session_id: str
    user_id: str
    cat_id: str
    thread_id: str
    status: SessionStatus
    created_at: float
    seal_started_at: Optional[float] = None


class SessionManager:
    """Manages session lifecycle with SQLite persistence."""

    def __init__(self, db_path: str = "data/sessions.db"):
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    cat_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    seal_started_at REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_key
                ON sessions(user_id, cat_id, thread_id, status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_thread
                ON sessions(thread_id)
            """)
            conn.commit()

    def create(
        self,
        user_id: str,
        cat_id: str,
        thread_id: str,
        session_id: str,
    ) -> Session:
        """Create a new session."""
        # Seal any existing active session for this key
        self._seal_existing(user_id, cat_id, thread_id)

        created_at = time.time()
        with sqlite3.connect(self._db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, user_id, cat_id, thread_id, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (session_id, user_id, cat_id, thread_id, SessionStatus.ACTIVE, created_at),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError(f"Session {session_id} already exists")

        return Session(
            session_id=session_id,
            user_id=user_id,
            cat_id=cat_id,
            thread_id=thread_id,
            status=SessionStatus.ACTIVE,
            created_at=created_at,
        )

    def _seal_existing(self, user_id: str, cat_id: str, thread_id: str) -> None:
        """Seal any existing active session for this key."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE sessions SET status = ?
                WHERE user_id = ? AND cat_id = ? AND thread_id = ? AND status = ?
                """,
                (SessionStatus.SEALED, user_id, cat_id, thread_id, SessionStatus.ACTIVE),
            )
            conn.commit()

    def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row:
                return self._row_to_session(row)
            return None

    def get_by_key(self, user_id: str, cat_id: str, thread_id: str) -> Optional[Session]:
        """Get active session by (user_id, cat_id, thread_id) key."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM sessions
                WHERE user_id = ? AND cat_id = ? AND thread_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (user_id, cat_id, thread_id, SessionStatus.ACTIVE),
            ).fetchone()
            if row:
                return self._row_to_session(row)
            return None

    def update_status(self, session_id: str, status: SessionStatus) -> None:
        """Update session status."""
        seal_started = None
        if status == SessionStatus.SEALING:
            seal_started = time.time()

        with sqlite3.connect(self._db_path) as conn:
            if seal_started:
                conn.execute(
                    "UPDATE sessions SET status = ?, seal_started_at = ? WHERE session_id = ?",
                    (status, seal_started, session_id),
                )
            else:
                conn.execute(
                    "UPDATE sessions SET status = ? WHERE session_id = ?",
                    (status, session_id),
                )
            conn.commit()

    def seal(self, session_id: str) -> None:
        """Seal a session (active -> sealed)."""
        self.update_status(session_id, SessionStatus.SEALED)

    def delete(self, session_id: str) -> None:
        """Delete a session."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

    def reconcile_stuck(self, threshold_seconds: float = 300.0) -> int:
        """Force-seal sessions stuck in sealing state.

        Returns:
            Number of sessions force-sealed.
        """
        cutoff = time.time() - threshold_seconds
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE sessions
                SET status = ?
                WHERE status = ? AND seal_started_at < ?
                """,
                (SessionStatus.SEALED, SessionStatus.SEALING, cutoff),
            )
            conn.commit()
            return cursor.rowcount

    def list_by_thread(self, thread_id: str) -> List[Session]:
        """List all sessions for a thread."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE thread_id = ? ORDER BY created_at DESC",
                (thread_id,),
            ).fetchall()
            return [self._row_to_session(row) for row in rows]

    def list_by_cat(self, cat_id: str) -> List[Session]:
        """List all sessions for a cat."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM sessions WHERE cat_id = ? ORDER BY created_at DESC",
                (cat_id,),
            ).fetchall()
            return [self._row_to_session(row) for row in rows]

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            session_id=row["session_id"],
            user_id=row["user_id"],
            cat_id=row["cat_id"],
            thread_id=row["thread_id"],
            status=SessionStatus(row["status"]),
            created_at=row["created_at"],
            seal_started_at=row["seal_started_at"],
        )
