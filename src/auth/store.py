"""SQLite-based user store for authentication."""
from pathlib import Path
from typing import Optional

import aiosqlite

from src.auth.models import User
from src.thread.stores.sqlite_store import DEFAULT_DB_PATH


class AuthStore:
    """User authentication store backed by SQLite."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA foreign_keys = ON")
        return self._db

    async def initialize(self):
        """Create users table if not exists."""
        db = await self._get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                created_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username
            ON users(username)
        """)
        await db.commit()

    async def create_user(self, username: str, password: str, role: str = "member") -> User:
        """Create a new user. Raises ValueError if username already exists."""
        import time
        db = await self._get_db()
        password_hash = User.hash_password(password)
        created_at = time.time()
        try:
            cursor = await db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, created_at)
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            raise ValueError(f"Username '{username}' already exists")
        return User(
            id=cursor.lastrowid,
            username=username,
            password_hash=password_hash,
            role=role,
            created_at=created_at,
        )

    async def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by username."""
        db = await self._get_db()
        async with db.execute(
            "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
            (username,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return User(
                id=row[0],
                username=row[1],
                password_hash=row[2],
                role=row[3],
                created_at=row[4],
            )

    async def close(self):
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None
