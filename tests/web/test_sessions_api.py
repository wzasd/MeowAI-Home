"""Tests for Session Chain API endpoints."""

import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.session.chain import SessionChain
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with a temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm
        app.state.cat_registry = CatRegistry()
        app.state.agent_registry = AgentRegistry()
        app.state.session_chain = SessionChain()

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.app = app  # Store app reference for tests
            await authenticate_client(client)
            yield client

        ThreadManager.reset()


@pytest.fixture
async def app_client_with_sessions():
    """Create a test client with pre-populated sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        # Setup registries
        cat_registry = CatRegistry()
        agent_registry = AgentRegistry()

        # Register test cats for name lookup
        from src.models.types import CatConfig, ContextBudget

        orange_config = CatConfig(
            cat_id="orange",
            breed_id="orange_breed",
            name="Orange",
            display_name="Orange",
            provider="openai",
            default_model="gpt-4",
            budget=ContextBudget(),
        )
        cat_registry.register("orange", orange_config)

        patch_config = CatConfig(
            cat_id="patch",
            breed_id="patch_breed",
            name="Patch",
            display_name="Patch",
            provider="openai",
            default_model="gpt-4",
            budget=ContextBudget(),
        )
        cat_registry.register("patch", patch_config)

        app.state.cat_registry = cat_registry
        app.state.agent_registry = agent_registry

        # Pre-populate sessions
        session_chain = SessionChain()
        session_chain.create("orange", "thread-1", "session-1")
        session_chain.create("orange", "thread-1", "session-2")
        session_chain.create("patch", "thread-1", "session-3")
        session_chain.create("orange", "thread-2", "session-4")
        app.state.session_chain = session_chain

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.app = app
            await authenticate_client(client)
            yield client

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_list_thread_sessions(app_client_with_sessions):
    """Test GET /api/threads/{thread_id}/sessions."""
    client = app_client_with_sessions
    response = await client.get("/api/threads/thread-1/sessions")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3

    # Check session structure
    for session in data:
        assert "session_id" in session
        assert "cat_id" in session
        assert "cat_name" in session
        assert "status" in session
        assert "created_at" in session
        assert session["status"] in ["active", "sealed"]

    # Check that cat name is resolved
    orange_sessions = [s for s in data if s["cat_id"] == "orange"]
    assert all(s["cat_name"] == "Orange" for s in orange_sessions)


@pytest.mark.asyncio
async def test_list_thread_sessions_empty(app_client):
    """Test GET /api/threads/{thread_id}/sessions with no sessions."""
    client = app_client
    response = await client.get("/api/threads/nonexistent/sessions")
    assert response.status_code == 200

    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_list_cat_sessions(app_client_with_sessions):
    """Test GET /api/threads/{thread_id}/cats/{cat_id}/sessions."""
    client = app_client_with_sessions
    response = await client.get("/api/threads/thread-1/cats/orange/sessions")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert all(s["cat_id"] == "orange" for s in data)


@pytest.mark.asyncio
async def test_get_session(app_client_with_sessions):
    """Test GET /api/sessions/{session_id}."""
    client = app_client_with_sessions
    response = await client.get("/api/sessions/session-1")
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == "session-1"
    assert data["cat_id"] == "orange"
    assert data["status"] == "sealed"
    assert data["cat_name"] == "Orange"


@pytest.mark.asyncio
async def test_get_session_not_found(app_client):
    """Test GET /api/sessions/{session_id} with invalid ID."""
    client = app_client
    response = await client.get("/api/sessions/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_seal_session(app_client_with_sessions):
    """Test POST /api/sessions/{session_id}/seal."""
    client = app_client_with_sessions

    # Verify latest session is active
    response = await client.get("/api/sessions/session-2")
    assert response.json()["status"] == "active"

    # Seal the latest active session
    response = await client.post("/api/sessions/session-2/seal")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "session-2"
    assert data["status"] == "sealed"

    # Verify session is now sealed
    response = await client.get("/api/sessions/session-2")
    assert response.json()["status"] == "sealed"


@pytest.mark.asyncio
async def test_seal_already_sealed_session(app_client_with_sessions):
    """Test sealing an already sealed session."""
    client = app_client_with_sessions

    # session-1 is already sealed (auto-sealed when session-2 was created)
    response = await client.post("/api/sessions/session-1/seal")
    assert response.status_code == 200
    assert response.json()["message"] == "Session is already sealed"


@pytest.mark.asyncio
async def test_seal_session_not_found(app_client):
    """Test sealing a non-existent session."""
    client = app_client
    response = await client.post("/api/sessions/nonexistent/seal")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unseal_session(app_client_with_sessions):
    """Test POST /api/sessions/{session_id}/unseal."""
    client = app_client_with_sessions

    # session-1 was auto-sealed when session-2 was created
    response = await client.post("/api/sessions/session-1/unseal")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "session-1"
    assert data["status"] == "active"

    # Verify session is active
    response = await client.get("/api/sessions/session-1")
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_unseal_already_active_session(app_client_with_sessions):
    """Test unsealing an already active session."""
    client = app_client_with_sessions

    # session-2 is the latest active session
    response = await client.post("/api/sessions/session-2/unseal")
    assert response.status_code == 200
    assert response.json()["message"] == "Session is already active"


@pytest.mark.asyncio
async def test_unseal_session_not_found(app_client):
    """Test unsealing a non-existent session."""
    client = app_client
    response = await client.post("/api/sessions/nonexistent/unseal")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_session_shows_restore_failures(app_client_with_sessions):
    """Test that session shows consecutive restore failures."""
    client = app_client_with_sessions

    # Manually set restore failures
    session_chain = client.app.state.session_chain
    for (cat_id, thread_id), records in session_chain._chains.items():
        for record in records:
            if record.session_id == "session-1":
                record.consecutive_restore_failures = 2

    response = await client.get("/api/sessions/session-1")
    assert response.status_code == 200

    data = response.json()
    assert data["consecutive_restore_failures"] == 2
