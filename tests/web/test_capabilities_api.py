"""Tests for capability orchestrator API routes."""
import json
import tempfile
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with a temp database and initialized registries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        cat_reg = CatRegistry()
        agent_reg = AgentRegistry()
        try:
            from src.models.registry_init import initialize_registries
            cat_reg, agent_reg = initialize_registries("cat-config.json")
        except Exception:
            pass

        app.state.cat_registry = cat_reg
        app.state.agent_registry = agent_reg

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client, tmpdir

        ThreadManager.reset()


@pytest.mark.asyncio
async def test_get_capabilities_bootstraps(app_client):
    client, tmpdir = app_client
    response = await client.get("/api/capabilities", params={"project_path": tmpdir})
    assert response.status_code == 200
    data = response.json()
    assert data["projectPath"] == tmpdir
    assert any(item["id"] == "meowai-collab" for item in data["items"])
    # File should have been created
    assert (Path(tmpdir) / ".neowai" / "capabilities.json").exists()


@pytest.mark.asyncio
async def test_get_capabilities_existing(app_client):
    client, tmpdir = app_client
    cap_file = Path(tmpdir) / ".neowai" / "capabilities.json"
    cap_file.parent.mkdir(parents=True, exist_ok=True)
    cap_file.write_text(
        json.dumps({"version": 1, "capabilities": [{"id": "custom", "type": "mcp", "enabled": False, "source": "test"}]}),
        encoding="utf-8",
    )
    response = await client.get("/api/capabilities", params={"project_path": tmpdir})
    assert response.status_code == 200
    data = response.json()
    custom = next((item for item in data["items"] if item["id"] == "custom"), None)
    assert custom is not None
    assert custom["enabled"] is False


@pytest.mark.asyncio
async def test_patch_global_toggle(app_client):
    client, tmpdir = app_client
    cap_file = Path(tmpdir) / ".neowai" / "capabilities.json"
    cap_file.parent.mkdir(parents=True, exist_ok=True)
    cap_file.write_text(
        json.dumps({
            "version": 1,
            "capabilities": [
                {"id": "fs", "type": "mcp", "enabled": True, "source": "test"}
            ]
        }),
        encoding="utf-8",
    )
    response = await client.patch(
        "/api/capabilities",
        json={
            "capabilityId": "fs",
            "capabilityType": "mcp",
            "scope": "global",
            "enabled": False,
            "projectPath": tmpdir,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["capability"]["enabled"] is False


@pytest.mark.asyncio
async def test_patch_per_cat_toggle(app_client):
    client, tmpdir = app_client
    # Need a cat in registry to resolve properly; use first available cat
    list_resp = await client.get("/api/cats")
    cats = list_resp.json()["cats"]
    cat_id = cats[0]["id"] if cats else "orange"

    cap_file = Path(tmpdir) / ".neowai" / "capabilities.json"
    cap_file.parent.mkdir(parents=True, exist_ok=True)
    cap_file.write_text(
        json.dumps({
            "version": 1,
            "capabilities": [
                {"id": "fs", "type": "mcp", "enabled": True, "source": "test"}
            ]
        }),
        encoding="utf-8",
    )
    response = await client.patch(
        "/api/capabilities",
        json={
            "capabilityId": "fs",
            "capabilityType": "mcp",
            "scope": "cat",
            "enabled": False,
            "catId": cat_id,
            "projectPath": tmpdir,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


@pytest.mark.asyncio
async def test_patch_unknown_capability_404(app_client):
    client, tmpdir = app_client
    response = await client.patch(
        "/api/capabilities",
        json={
            "capabilityId": "nonexistent",
            "capabilityType": "mcp",
            "scope": "global",
            "enabled": False,
            "projectPath": tmpdir,
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_without_project_path_400(app_client):
    client, _ = app_client
    response = await client.get("/api/capabilities", params={"project_path": ""})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_capabilities_includes_skills(app_client):
    client, tmpdir = app_client
    skills_dir = Path(tmpdir) / "skills" / "design"
    skills_dir.mkdir(parents=True)
    (skills_dir / "SKILL.md").write_text(
        "---\n"
        "description: Design system skill\n"
        "triggers:\n  - design\n  - 设计系统\n"
        "---\n",
        encoding="utf-8",
    )
    response = await client.get("/api/capabilities", params={"project_path": tmpdir})
    assert response.status_code == 200
    data = response.json()
    design = next((item for item in data["items"] if item["id"] == "design"), None)
    assert design is not None
    assert design["type"] == "skill"
    assert design["description"] == "Design system skill"
    assert design["triggers"] == ["design", "设计系统"]


@pytest.mark.asyncio
async def test_get_capabilities_with_probe(app_client):
    client, tmpdir = app_client
    response = await client.get(
        "/api/capabilities",
        params={"project_path": tmpdir, "probe": "true"},
    )
    assert response.status_code == 200
    data = response.json()
    # Built-in MCP servers should have probe fields populated
    mcp_items = [item for item in data["items"] if item["type"] == "mcp"]
    assert len(mcp_items) > 0
    for item in mcp_items:
        assert "connectionStatus" in item
        assert item["connectionStatus"] in ("connected", "error", "timeout", "unsupported")
