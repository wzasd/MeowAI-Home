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
            "/webhook",
            "/health",
            "/api/auth/login",
            "/api/auth/register",
        ]

    async def dispatch(self, request: Request, call_next):
        # Check if path is public
        path = request.url.path
        if any(path.startswith(p) for p in self.public_paths):
            return await call_next(request)

        # Extract and verify token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid authorization header"},
                status_code=401
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        if jwt is None:
            return JSONResponse(
                {"error": "JWT support not available"},
                status_code=500
            )

        try:
            payload = jwt.decode(token, self.secret, algorithms=["HS256"])
            request.state.user = payload
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                {"error": "Token expired"},
                status_code=401
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                {"error": "Invalid token"},
                status_code=401
            )

        return await call_next(request)
