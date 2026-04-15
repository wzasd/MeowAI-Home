"""Tests for scheduler API endpoints."""
import os
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.scheduler.runner import TaskRunner, TaskGovernance
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with scheduler initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        from src.models.cat_registry import CatRegistry
        from src.models.agent_registry import AgentRegistry
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

        # Initialize task runner with temp db
        task_governance = TaskGovernance()
        task_runner = TaskRunner(db_path=str(Path(tmpdir) / "scheduler.db"), governance=task_governance)
        app.state.task_runner = task_runner

        from src.scheduler.pipeline import Pipeline, ActorResolver
        scheduler_pipeline = Pipeline(actor_resolver=ActorResolver(cat_registry=cat_reg), governance=task_governance)
        app.state.scheduler_pipeline = scheduler_pipeline

        from src.scheduler.templates import SCHEDULER_TEMPLATES
        for tmpl in SCHEDULER_TEMPLATES:
            async def _default_executor(context):
                pass
            scheduler_pipeline.register_executor(tmpl["id"], _default_executor)

        await task_runner.start()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client, task_runner

        await task_runner.stop()
        ThreadManager.reset()
        if hasattr(tm, '_store') and tm._store:
            await tm._store.close()


@pytest.mark.asyncio
async def test_list_templates(app_client):
    """Test listing scheduler templates."""
    client, _ = app_client
    response = await client.get("/api/scheduler/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert len(data["templates"]) >= 3
    ids = [t["id"] for t in data["templates"]]
    assert "reminder" in ids
    assert "repo-activity" in ids
    assert "web-digest" in ids


@pytest.mark.asyncio
async def test_list_tasks_empty(app_client):
    """Test listing tasks when none exist."""
    client, runner = app_client
    # Clear any existing tasks
    for task in runner.list_tasks():
        runner.unregister_task(task.id)

    response = await client.get("/api/scheduler/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert data["tasks"] == []


@pytest.mark.asyncio
async def test_create_task_interval(app_client):
    """Test creating an interval task."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks", json={
        "name": "Test Interval Task",
        "description": "A test task",
        "trigger": "interval",
        "schedule": "60",
        "enabled": True,
        "task_template": "reminder",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Interval Task"
    assert data["trigger"] == "interval"
    assert data["schedule"] == "60"
    assert data["enabled"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_task_cron(app_client):
    """Test creating a cron task."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks", json={
        "name": "Daily Digest",
        "description": "Daily summary",
        "trigger": "cron",
        "schedule": "0 9 * * *",
        "enabled": False,
        "task_template": "web-digest",
        "task_config": {"max_articles": 10},
    })
    assert response.status_code == 200
    data = response.json()
    assert data["trigger"] == "cron"
    assert data["schedule"] == "0 9 * * *"
    assert data["enabled"] is False
    assert data["task_config"]["max_articles"] == 10


@pytest.mark.asyncio
async def test_create_task_invalid_trigger(app_client):
    """Test creating a task with invalid trigger."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks", json={
        "name": "Bad Task",
        "trigger": "unknown",
        "schedule": "60",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_task(app_client):
    """Test getting a single task."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Get Me",
        "trigger": "interval",
        "schedule": "120",
    })
    task_id = create_res.json()["id"]

    response = await client.get(f"/api/scheduler/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_task_not_found(app_client):
    """Test getting non-existent task."""
    client, _ = app_client
    response = await client.get("/api/scheduler/tasks/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_task(app_client):
    """Test updating a task."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Update Me",
        "trigger": "interval",
        "schedule": "120",
    })
    task_id = create_res.json()["id"]

    response = await client.patch(f"/api/scheduler/tasks/{task_id}", json={
        "name": "Updated Name",
        "schedule": "300",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["schedule"] == "300"


@pytest.mark.asyncio
async def test_update_task_not_found(app_client):
    """Test updating non-existent task."""
    client, _ = app_client
    response = await client.patch("/api/scheduler/tasks/nonexistent", json={
        "name": "Updated",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enable_disable_task(app_client):
    """Test enabling and disabling a task."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Toggle Me",
        "trigger": "interval",
        "schedule": "120",
        "enabled": False,
    })
    task_id = create_res.json()["id"]

    # Enable
    response = await client.post(f"/api/scheduler/tasks/{task_id}/enable")
    assert response.status_code == 200
    assert response.json()["enabled"] is True

    # Disable
    response = await client.post(f"/api/scheduler/tasks/{task_id}/disable")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


@pytest.mark.asyncio
async def test_enable_task_not_found(app_client):
    """Test enabling non-existent task."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks/nonexistent/enable")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_disable_task_not_found(app_client):
    """Test disabling non-existent task."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks/nonexistent/disable")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_task(app_client):
    """Test manually triggering a task."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Trigger Me",
        "trigger": "interval",
        "schedule": "120",
    })
    task_id = create_res.json()["id"]

    response = await client.post(f"/api/scheduler/tasks/{task_id}/trigger")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["task_id"] == task_id


@pytest.mark.asyncio
async def test_trigger_task_not_found(app_client):
    """Test triggering non-existent task."""
    client, _ = app_client
    response = await client.post("/api/scheduler/tasks/nonexistent/trigger")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task(app_client):
    """Test deleting a task."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Delete Me",
        "trigger": "interval",
        "schedule": "120",
    })
    task_id = create_res.json()["id"]

    response = await client.delete(f"/api/scheduler/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify deleted
    get_res = await client.get(f"/api/scheduler/tasks/{task_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_not_found(app_client):
    """Test deleting non-existent task."""
    client, _ = app_client
    response = await client.delete("/api/scheduler/tasks/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_governance_pause_resume(app_client):
    """Test global pause and resume."""
    client, _ = app_client

    pause_res = await client.post("/api/scheduler/governance", json={"action": "pause_all"})
    assert pause_res.status_code == 200
    assert pause_res.json()["action"] == "pause_all"

    resume_res = await client.post("/api/scheduler/governance", json={"action": "resume_all"})
    assert resume_res.status_code == 200
    assert resume_res.json()["action"] == "resume_all"


@pytest.mark.asyncio
async def test_governance_invalid_action(app_client):
    """Test invalid governance action."""
    client, _ = app_client
    response = await client.post("/api/scheduler/governance", json={"action": "invalid"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_task_logs(app_client):
    """Test getting task logs."""
    client, _ = app_client
    create_res = await client.post("/api/scheduler/tasks", json={
        "name": "Log Task",
        "trigger": "interval",
        "schedule": "120",
    })
    task_id = create_res.json()["id"]

    response = await client.get(f"/api/scheduler/tasks/{task_id}/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)
