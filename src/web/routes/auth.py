"""Authentication REST endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.auth.models import User
from src.auth.store import AuthStore

router = APIRouter()


def get_auth_store(request: Request) -> AuthStore:
    return request.app.state.auth_store


def _get_secret(request: Request) -> str:
    import os
    return os.environ.get("MEOWAI_SECRET", "dev-secret-change-in-production")


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    role: Optional[str] = Field(default="member")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class UserResponse(BaseModel):
    username: str
    role: str


@router.post("/auth/register", response_model=UserResponse)
async def register(
    body: RegisterRequest,
    auth_store: AuthStore = Depends(get_auth_store),
):
    """Register a new user account."""
    valid_roles = {"admin", "member", "viewer"}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    try:
        user = await auth_store.create_user(body.username, body.password, body.role)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return UserResponse(username=user.username, role=user.role)


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    auth_store: AuthStore = Depends(get_auth_store),
):
    """Authenticate and receive a JWT token."""
    user = await auth_store.get_by_username(body.username)
    if user is None or not user.verify_password(body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    secret = _get_secret(request)
    token = user.generate_token(secret)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        username=user.username,
        role=user.role,
    )


@router.get("/auth/me", response_model=UserResponse)
async def me(request: Request):
    """Get current authenticated user info."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserResponse(username=user.get("sub"), role=user.get("role", "member"))
