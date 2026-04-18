"""Tests for tasks API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.web.routes.tasks import router, DEFAULT_DB_PATH


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear tasks storage before each test."""
    import asyncio
    import aiosqlite

    async def _clean():
        db = await aiosqlite.connect(DEFAULT_DB_PATH)
        await db.execute("DELETE FROM thread_tasks")
        await db.commit()
        await db.close()

    asyncio.run(_clean())
    yield
    asyncio.run(_clean())


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


class TestListTasks:
    """Tests for GET /api/tasks/entries"""

    def test_list_empty_tasks(self, client):
        """Test listing tasks when none exist."""
        response = client.get("/api/tasks/entries")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_all_tasks(self, client):
        """Test listing all tasks."""
        # Create some tasks
        client.post("/api/tasks/entries", json={
            "id": "task-1",
            "title": "Task 1",
            "status": "todo"
        })
        client.post("/api/tasks/entries", json={
            "id": "task-2",
            "title": "Task 2",
            "status": "doing"
        })

        response = client.get("/api/tasks/entries")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        ids = {d["id"] for d in data}
        assert "task-1" in ids
        assert "task-2" in ids

    def test_list_tasks_filtered_by_thread(self, client):
        """Test listing tasks filtered by threadId."""
        # Create tasks with different threadIds
        client.post("/api/tasks/entries", json={
            "id": "task-1",
            "title": "Task 1",
            "status": "todo",
            "threadId": "thread-a"
        })
        client.post("/api/tasks/entries", json={
            "id": "task-2",
            "title": "Task 2",
            "status": "doing",
            "threadId": "thread-b"
        })
        client.post("/api/tasks/entries", json={
            "id": "task-3",
            "title": "Task 3",
            "status": "done",
            "threadId": "thread-a"
        })

        response = client.get("/api/tasks/entries?threadId=thread-a")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(t["threadId"] == "thread-a" for t in data)


class TestCreateTask:
    """Tests for POST /api/tasks/entries"""

    def test_create_task_with_id(self, client):
        """Test creating a task with explicit ID."""
        response = client.post("/api/tasks/entries", json={
            "id": "my-task",
            "title": "My Task",
            "status": "todo"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "my-task"
        assert data["title"] == "My Task"
        assert data["status"] == "todo"
        assert "createdAt" in data

    def test_create_task_without_id(self, client):
        """Test creating a task without ID generates one."""
        response = client.post("/api/tasks/entries", json={
            "title": "Auto ID Task",
            "status": "doing"
        })
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert len(data["id"]) > 0
        assert data["title"] == "Auto ID Task"

    def test_create_task_with_all_fields(self, client):
        """Test creating a task with all optional fields."""
        response = client.post("/api/tasks/entries", json={
            "id": "full-task",
            "title": "Full Task",
            "status": "blocked",
            "ownerCat": "orange",
            "description": "A test task",
            "threadId": "thread-123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["ownerCat"] == "orange"
        assert data["description"] == "A test task"
        assert data["threadId"] == "thread-123"


class TestUpdateTaskStatus:
    """Tests for POST /api/tasks/entries/{taskId}/status"""

    def test_update_status_success(self, client):
        """Test updating task status successfully."""
        # Create a task first
        client.post("/api/tasks/entries", json={
            "id": "status-task",
            "title": "Status Task",
            "status": "todo"
        })

        response = client.post("/api/tasks/entries/status-task/status", params={"status": "doing"})
        assert response.status_code == 200
        assert response.json() == {"success": True}

        # Verify the status was updated
        list_response = client.get("/api/tasks/entries")
        tasks = list_response.json()
        assert tasks[0]["status"] == "doing"

    def test_update_status_not_found(self, client):
        """Test updating status of non-existent task."""
        response = client.post("/api/tasks/entries/nonexistent/status", params={"status": "done"})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_status_all_statuses(self, client):
        """Test updating to all valid statuses."""
        statuses = ["todo", "doing", "blocked", "done"]

        for status in statuses:
            # Create task
            task_id = f"task-{status}"
            client.post("/api/tasks/entries", json={
                "id": task_id,
                "title": f"Task {status}",
                "status": "todo"
            })

            # Update to target status
            response = client.post(f"/api/tasks/entries/{task_id}/status", params={"status": status})
            assert response.status_code == 200, f"Failed to set status to {status}"


class TestDeleteTask:
    """Tests for DELETE /api/tasks/entries/{taskId}"""

    def test_delete_task_success(self, client):
        """Test deleting a task successfully."""
        # Create a task
        client.post("/api/tasks/entries", json={
            "id": "delete-task",
            "title": "Delete Me",
            "status": "todo"
        })

        # Verify it exists
        assert len(client.get("/api/tasks/entries").json()) == 1

        # Delete it
        response = client.delete("/api/tasks/entries/delete-task")
        assert response.status_code == 200
        assert response.json() == {"success": True}

        # Verify it's gone
        assert len(client.get("/api/tasks/entries").json()) == 0

    def test_delete_task_not_found(self, client):
        """Test deleting non-existent task."""
        response = client.delete("/api/tasks/entries/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
