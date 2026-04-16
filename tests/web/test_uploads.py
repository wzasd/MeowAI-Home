"""Tests for file upload endpoints."""

import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with a temp database and temp project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client, tmpdir

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_upload_file_success(app_client):
    """Test normal upload returns metadata and file is stored."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Upload Test", "project_path": tmpdir})
    assert create_resp.status_code == 200
    thread_id = create_resp.json()["id"]

    file_content = b"Hello, MeowAI!"
    response = await client.post(
        f"/api/threads/{thread_id}/uploads",
        files={"file": ("hello.txt", file_content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "hello.txt"
    assert data["size"] == len(file_content)
    assert data["mimeType"] == "text/plain"
    assert data["url"] == f"/api/threads/{thread_id}/uploads/hello.txt"

    # Verify file exists on disk
    stored_path = Path(tmpdir) / ".meowai" / "uploads" / thread_id / "hello.txt"
    assert stored_path.read_bytes() == file_content


@pytest.mark.asyncio
async def test_upload_file_path_traversal(app_client):
    """Test malicious filename is sanitized to basename only."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Upload Test", "project_path": tmpdir})
    thread_id = create_resp.json()["id"]

    file_content = b"malicious"
    response = await client.post(
        f"/api/threads/{thread_id}/uploads",
        files={"file": ("../../etc/passwd", file_content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "passwd"

    # Verify it did NOT escape the upload directory
    bad_path = Path(tmpdir).parent / "etc" / "passwd"
    assert not bad_path.exists()
    stored_path = Path(tmpdir) / ".meowai" / "uploads" / thread_id / "passwd"
    assert stored_path.exists()


@pytest.mark.asyncio
async def test_upload_file_too_large(app_client):
    """Test oversized file returns 413."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Upload Test", "project_path": tmpdir})
    thread_id = create_resp.json()["id"]

    big_content = b"x" * (10 * 1024 * 1024 + 1)
    response = await client.post(
        f"/api/threads/{thread_id}/uploads",
        files={"file": ("big.bin", big_content, "application/octet-stream")},
    )
    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_download_file_success(app_client):
    """Test GET download returns the uploaded file."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Upload Test", "project_path": tmpdir})
    thread_id = create_resp.json()["id"]

    file_content = b"download me"
    await client.post(
        f"/api/threads/{thread_id}/uploads",
        files={"file": ("dl.txt", file_content, "text/plain")},
    )

    response = await client.get(f"/api/threads/{thread_id}/uploads/dl.txt")
    assert response.status_code == 200
    assert response.content == file_content


@pytest.mark.asyncio
async def test_download_file_path_traversal(app_client):
    """Test path traversal in download endpoint logic is blocked."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Upload Test", "project_path": tmpdir})
    thread_id = create_resp.json()["id"]

    # Call the endpoint function directly with a malicious filename
    # (HTTP clients normalize %2f before routing, so we test the logic directly)
    from fastapi import HTTPException
    from src.web.routes.uploads import download_file
    from src.web.dependencies import get_thread_manager
    from src.thread import ThreadManager

    tm = ThreadManager()
    try:
        await download_file(thread_id, "../../etc/passwd", tm=tm)
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 403
        assert "traversal" in exc.detail.lower()
