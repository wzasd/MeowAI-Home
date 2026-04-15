"""Shared fixtures and helpers for web API tests."""
from httpx import AsyncClient


async def authenticate_client(
    client: AsyncClient,
    username: str = "testuser",
    password: str = "testpass",
    role: str = "admin",
) -> str:
    """Register and log in a test user, setting the Authorization header."""
    await client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "role": role},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token
