"""User model and authentication utilities"""
import hashlib
import time
from dataclasses import dataclass
from typing import Optional

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore


@dataclass
class User:
    """User entity with authentication support."""
    id: int
    username: str
    password_hash: str
    role: str          # "admin" | "member" | "viewer"
    created_at: float

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        return self.password_hash == self.hash_password(password)

    def generate_token(self, secret: str, expires_in: int = 86400) -> str:
        """Generate a JWT token for this user."""
        if jwt is None:
            raise RuntimeError("PyJWT is required for token generation")
        payload = {
            "sub": self.username,
            "role": self.role,
            "exp": time.time() + expires_in,
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    @staticmethod
    def verify_token(token: str, secret: str) -> Optional[dict]:
        """Verify a JWT token and return the payload."""
        if jwt is None:
            raise RuntimeError("PyJWT is required for token verification")
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
