"""Authentication middleware for FastAPI"""
from typing import List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware for protecting API routes."""

    def __init__(
        self,
        app,
        secret: str,
        public_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.secret = secret
        self.public_paths = public_paths or [
            "/",
            "/webhook",
            "/health",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/review/webhook",
            "/ws",
            "/assets",
        ]

    async def dispatch(self, request: Request, call_next):
        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Check if path is public
        path = request.url.path
        public_exact = {"/"}
        public_prefixes = [p for p in self.public_paths if p != "/"]
        if path in public_exact or any(path.startswith(p) for p in public_prefixes):
            return await call_next(request)

        # Extract and verify token (optional — allow anonymous access)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if jwt is not None:
                try:
                    payload = jwt.decode(token, self.secret, algorithms=["HS256"])
                    request.state.user = payload
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                    pass

        return await call_next(request)
