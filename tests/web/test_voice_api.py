"""Tests for voice API endpoints."""

import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

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
async def test_tts_success(app_client):
    """Test TTS endpoint returns an MP3 file."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Voice Test", "project_path": tmpdir})
    assert create_resp.status_code == 200
    thread_id = create_resp.json()["id"]

    fake_mp3 = Path(tmpdir) / "fake.mp3"
    fake_mp3.write_bytes(b"fake mp3")

    with patch("src.web.routes.voice.tts_service.synthesize", return_value=str(fake_mp3)):
        response = await client.post(
            "/api/voice/tts",
            data={"text": "你好", "cat_id": "orange", "thread_id": thread_id},
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"fake mp3"


@pytest.mark.asyncio
async def test_tts_thread_not_found(app_client):
    """Test TTS endpoint returns 404 for unknown thread."""
    client, _ = app_client
    response = await client.post(
        "/api/voice/tts",
        data={"text": "你好", "cat_id": "orange", "thread_id": "no-such-thread"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tts_empty_text(app_client):
    """Test TTS endpoint returns 400 for empty text."""
    client, tmpdir = app_client
    create_resp = await client.post("/api/threads", json={"name": "Voice Test", "project_path": tmpdir})
    thread_id = create_resp.json()["id"]

    response = await client.post(
        "/api/voice/tts",
        data={"text": "   ", "cat_id": "orange", "thread_id": thread_id},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_asr_success(app_client):
    """Test ASR endpoint returns transcription text."""
    client, _ = app_client

    with patch("src.web.routes.voice.asr_service.transcribe", return_value="Hello world"):
        response = await client.post(
            "/api/voice/asr",
            files={"audio": ("test.mp3", b"fake audio", "audio/mpeg")},
            data={"language": "en"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Hello world"
    assert data["language"] == "en"


@pytest.mark.asyncio
async def test_asr_missing_api_key(app_client):
    """Test ASR endpoint returns 503 when API key is missing."""
    client, _ = app_client

    with patch("src.web.routes.voice.asr_service.api_key", None):
        response = await client.post(
            "/api/voice/asr",
            files={"audio": ("test.mp3", b"fake audio", "audio/mpeg")},
        )

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
