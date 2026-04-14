"""Tests for governance project SQLite persistence."""
import pytest
import tempfile
from pathlib import Path
from urllib.parse import quote
from httpx import AsyncClient, ASGITransport

from src.web.app import create_app
from src.web.routes.governance import _with_db


@pytest.fixture
async def app_client():
    """Create a test client with a temp database for governance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        app = create_app()

        # Monkey-patch default db path for the duration of tests
        import src.web.routes.governance as gov_module
        original_db_path = gov_module.DEFAULT_DB_PATH
        gov_module.DEFAULT_DB_PATH = db_path

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

        gov_module.DEFAULT_DB_PATH = original_db_path


@pytest.mark.anyio
async def test_list_empty_projects(app_client):
    """List projects when none exist."""
    import src.web.routes.governance as gov_module
    db = await gov_module._with_db()
    await db.execute("DELETE FROM governance_projects")
    await db.commit()
    await db.close()
    response = await app_client.get("/api/governance/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == []


@pytest.mark.anyio
async def test_add_and_retrieve_project(app_client):
    """Add a project and retrieve it."""
    import src.web.routes.governance as gov_module
    db = await gov_module._with_db()
    await db.execute("DELETE FROM governance_projects")
    await db.commit()
    await db.close()

    response = await app_client.post("/api/governance/projects", json={
        "project_path": "/projects/test-foo",
        "status": "healthy",
        "version": "1.2.3",
        "findings": [{"rule": "r1", "severity": "info", "message": "m1"}],
        "confirmed": True,
    })
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = await app_client.get("/api/governance/projects")
    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["project_path"] == "/projects/test-foo"
    assert projects[0]["status"] == "healthy"
    assert projects[0]["pack_version"] == "1.2.3"
    assert projects[0]["findings"][0]["rule"] == "r1"


@pytest.mark.anyio
async def test_update_existing_project(app_client):
    """Upsert updates an existing project."""
    import src.web.routes.governance as gov_module
    db = await gov_module._with_db()
    await db.execute("DELETE FROM governance_projects")
    await db.commit()
    await db.close()

    await app_client.post("/api/governance/projects", json={
        "project_path": "/projects/test-bar",
        "status": "stale",
        "version": "0.1.0",
    })

    response = await app_client.post("/api/governance/projects", json={
        "project_path": "/projects/test-bar",
        "status": "healthy",
        "version": "0.2.0",
        "findings": [],
        "confirmed": True,
    })
    assert response.status_code == 200

    response = await app_client.get("/api/governance/projects")
    projects = response.json()["projects"]
    assert len(projects) == 1
    assert projects[0]["status"] == "healthy"
    assert projects[0]["pack_version"] == "0.2.0"
    assert projects[0]["confirmed"] is True


@pytest.mark.anyio
async def test_delete_project(app_client):
    """Delete a project by path."""
    import src.web.routes.governance as gov_module
    db = await gov_module._with_db()
    await db.execute("DELETE FROM governance_projects")
    await db.commit()
    await db.close()

    await app_client.post("/api/governance/projects", json={
        "project_path": "/projects/to-delete",
        "status": "healthy",
    })

    encoded = quote("/projects/to-delete", safe="")
    response = await app_client.delete(f"/api/governance/projects/{encoded}")
    assert response.status_code == 200
    assert response.json()["deleted"] == "/projects/to-delete"

    response = await app_client.get("/api/governance/projects")
    assert response.json()["projects"] == []


@pytest.mark.anyio
async def test_delete_nonexistent_project(app_client):
    """Deleting a missing project returns 404."""
    response = await app_client.delete("/api/governance/projects/no-such-project")
    assert response.status_code == 404
