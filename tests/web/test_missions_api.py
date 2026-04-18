"""Tests for Mission Hub API endpoints."""

import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.missions.store import MissionStore
from src.web.app import create_app
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

        auth_store = AuthStore(db_path=db_path)
        await auth_store.initialize()
        app.state.auth_store = auth_store

        mission_store = MissionStore(db_path=db_path)
        await mission_store.initialize()
        app.state.mission_store = mission_store

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            client.app = app
            await authenticate_client(client)
            yield client

        ThreadManager.reset()


class TestListTasks:
    """Tests for GET /api/missions/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks(self, app_client):
        """Test listing all tasks."""
        response = await app_client.get("/api/missions/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self, app_client):
        """Test listing tasks with status filter."""
        await app_client.post("/api/missions/tasks", json={"title": "F1", "status": "doing"})
        await app_client.post("/api/missions/tasks", json={"title": "F2", "status": "done"})

        response = await app_client.get("/api/missions/tasks?status=done")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        for task in data["tasks"]:
            assert task["status"] == "done"

    @pytest.mark.asyncio
    async def test_list_tasks_with_priority_filter(self, app_client):
        """Test listing tasks with priority filter."""
        await app_client.post("/api/missions/tasks", json={"title": "P1", "priority": "P0"})
        await app_client.post("/api/missions/tasks", json={"title": "P2", "priority": "P2"})

        response = await app_client.get("/api/missions/tasks?priority=P0")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        for task in data["tasks"]:
            assert task["priority"] == "P0"


class TestCreateTask:
    """Tests for POST /api/missions/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_minimal(self, app_client):
        """Test creating task with minimal data."""
        response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Test Task"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["id"] is not None
        assert data["createdAt"] is not None
        assert data["status"] == "backlog"
        assert data["priority"] == "P2"
        assert len(data.get("thread_ids", [])) > 0

    @pytest.mark.asyncio
    async def test_create_task_full(self, app_client):
        """Test creating task with all fields."""
        task_data = {
            "title": "Full Test Task",
            "description": "A test task description",
            "status": "todo",
            "priority": "P1",
            "ownerCat": "orange",
            "tags": ["test", "api"],
            "dueDate": "2026-04-30",
            "progress": 50
        }
        response = await app_client.post("/api/missions/tasks", json=task_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] == task_data["description"]
        assert data["status"] == task_data["status"]
        assert data["priority"] == task_data["priority"]
        assert data["ownerCat"] == task_data["ownerCat"]
        assert data["tags"] == task_data["tags"]
        assert data["dueDate"] == task_data["dueDate"]
        assert data["progress"] == task_data["progress"]
        assert len(data.get("thread_ids", [])) > 0

    @pytest.mark.asyncio
    async def test_create_task_creates_thread_and_system_message(self, app_client):
        """Test creating a task auto-creates a dedicated thread with system message."""
        response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Thread Test", "description": "A test task", "status": "todo"},
        )
        assert response.status_code == 200
        task = response.json()
        assert len(task.get("thread_ids", [])) > 0

        # Verify thread exists and has active_task_id set
        thread_id = task["thread_ids"][0]
        tm = app_client.app.state.thread_manager
        thread = await tm.get(thread_id)
        assert thread is not None
        assert thread.active_task_id == task["id"]

        # Verify thread has system message
        assert len(thread.messages) >= 1
        assert "Thread Test" in thread.messages[0].content


class TestGetTask:
    """Tests for GET /api/missions/tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, app_client):
        """Test getting non-existent task."""
        response = await app_client.get("/api/missions/tasks/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_success(self, app_client):
        """Test getting existing task."""
        create_response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Get Test Task"}
        )
        task = create_response.json()

        response = await app_client.get(f"/api/missions/tasks/{task['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task["id"]
        assert data["title"] == "Get Test Task"


class TestUpdateTask:
    """Tests for PATCH /api/missions/tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, app_client):
        """Test updating non-existent task."""
        response = await app_client.patch(
            "/api/missions/tasks/nonexistent",
            json={"title": "Updated"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_success(self, app_client):
        """Test updating existing task and pushing system message."""
        create_response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Update Test"}
        )
        task = create_response.json()

        response = await app_client.patch(
            f"/api/missions/tasks/{task['id']}",
            json={"title": "Updated Title", "priority": "P0"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["priority"] == "P0"

        # Verify system message was pushed to thread
        thread = await app_client.app.state.thread_manager.get(task["thread_ids"][0])
        assert any("Updated Title" in m.content or "P0" in m.content for m in thread.messages)


class TestUpdateTaskStatus:
    """Tests for POST /api/missions/tasks/{id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, app_client):
        """Test updating status of non-existent task."""
        response = await app_client.post(
            "/api/missions/tasks/nonexistent/status",
            json={"status": "done"}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_status_success(self, app_client):
        """Test updating task status."""
        create_response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Status Test", "status": "backlog"}
        )
        task = create_response.json()

        response = await app_client.post(
            f"/api/missions/tasks/{task['id']}/status",
            json={"status": "doing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "doing"

        # Verify system message was pushed
        thread = await app_client.app.state.thread_manager.get(task["thread_ids"][0])
        assert any("doing" in m.content for m in thread.messages)

    @pytest.mark.asyncio
    async def test_update_status_all_statuses(self, app_client):
        """Test updating to all valid statuses."""
        statuses = ["backlog", "todo", "doing", "blocked", "done"]

        for status in statuses:
            create_response = await app_client.post(
                "/api/missions/tasks",
                json={"title": f"Status {status} Test"}
            )
            task = create_response.json()

            response = await app_client.post(
                f"/api/missions/tasks/{task['id']}/status",
                json={"status": status}
            )
            assert response.status_code == 200


class TestDeleteTask:
    """Tests for DELETE /api/missions/tasks/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, app_client):
        """Test deleting non-existent task."""
        response = await app_client.delete("/api/missions/tasks/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_success(self, app_client):
        """Test deleting existing task."""
        create_response = await app_client.post(
            "/api/missions/tasks",
            json={"title": "Delete Test"}
        )
        task = create_response.json()

        response = await app_client.delete(f"/api/missions/tasks/{task['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        get_response = await app_client.get(f"/api/missions/tasks/{task['id']}")
        assert get_response.status_code == 404


class TestGetStats:
    """Tests for GET /api/missions/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats(self, app_client):
        """Test getting mission statistics."""
        response = await app_client.get("/api/missions/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "backlog" in data
        assert "todo" in data
        assert "doing" in data
        assert "blocked" in data
        assert "done" in data
        assert "by_priority" in data
