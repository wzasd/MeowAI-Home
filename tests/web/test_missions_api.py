"""Tests for missions API routes."""

import pytest
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestListTasks:
    """Tests for GET /api/missions/tasks endpoint."""

    def test_list_tasks(self, client):
        """Test listing all tasks."""
        response = client.get("/api/missions/tasks")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        assert "total" in data
        assert isinstance(data["tasks"], list)

    def test_list_tasks_with_status_filter(self, client):
        """Test listing tasks with status filter."""
        response = client.get("/api/missions/tasks?status=done")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        for task in data["tasks"]:
            assert task["status"] == "done"

    def test_list_tasks_with_priority_filter(self, client):
        """Test listing tasks with priority filter."""
        response = client.get("/api/missions/tasks?priority=P0")
        assert response.status_code == 200
        data = response.json()
        assert "tasks" in data
        for task in data["tasks"]:
            assert task["priority"] == "P0"


class TestCreateTask:
    """Tests for POST /api/missions/tasks endpoint."""

    def test_create_task_minimal(self, client):
        """Test creating task with minimal data."""
        response = client.post(
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

    def test_create_task_full(self, client):
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
        response = client.post("/api/missions/tasks", json=task_data)
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


class TestGetTask:
    """Tests for GET /api/missions/tasks/{id} endpoint."""

    def test_get_task_not_found(self, client):
        """Test getting non-existent task."""
        response = client.get("/api/missions/tasks/nonexistent")
        assert response.status_code == 404

    def test_get_task_success(self, client):
        """Test getting existing task."""
        # First create a task
        create_response = client.post(
            "/api/missions/tasks",
            json={"title": "Get Test Task"}
        )
        task = create_response.json()

        # Then get it
        response = client.get(f"/api/missions/tasks/{task['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task["id"]
        assert data["title"] == "Get Test Task"


class TestUpdateTask:
    """Tests for PATCH /api/missions/tasks/{id} endpoint."""

    def test_update_task_not_found(self, client):
        """Test updating non-existent task."""
        response = client.patch(
            "/api/missions/tasks/nonexistent",
            json={"title": "Updated"}
        )
        assert response.status_code == 404

    def test_update_task_success(self, client):
        """Test updating existing task."""
        # Create a task first
        create_response = client.post(
            "/api/missions/tasks",
            json={"title": "Update Test"}
        )
        task = create_response.json()

        # Update it
        response = client.patch(
            f"/api/missions/tasks/{task['id']}",
            json={"title": "Updated Title", "priority": "P0"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["priority"] == "P0"


class TestUpdateTaskStatus:
    """Tests for POST /api/missions/tasks/{id}/status endpoint."""

    def test_update_status_not_found(self, client):
        """Test updating status of non-existent task."""
        response = client.post(
            "/api/missions/tasks/nonexistent/status",
            json={"status": "done"}
        )
        assert response.status_code == 404

    def test_update_status_success(self, client):
        """Test updating task status."""
        # Create a task
        create_response = client.post(
            "/api/missions/tasks",
            json={"title": "Status Test", "status": "backlog"}
        )
        task = create_response.json()

        # Update status
        response = client.post(
            f"/api/missions/tasks/{task['id']}/status",
            json={"status": "doing"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "doing"

    def test_update_status_all_statuses(self, client):
        """Test updating to all valid statuses."""
        statuses = ["backlog", "todo", "doing", "blocked", "done"]

        for status in statuses:
            # Create a task
            create_response = client.post(
                "/api/missions/tasks",
                json={"title": f"Status {status} Test"}
            )
            task = create_response.json()

            # Update status
            response = client.post(
                f"/api/missions/tasks/{task['id']}/status",
                json={"status": status}
            )
            assert response.status_code == 200


class TestDeleteTask:
    """Tests for DELETE /api/missions/tasks/{id} endpoint."""

    def test_delete_task_not_found(self, client):
        """Test deleting non-existent task."""
        response = client.delete("/api/missions/tasks/nonexistent")
        assert response.status_code == 404

    def test_delete_task_success(self, client):
        """Test deleting existing task."""
        # Create a task
        create_response = client.post(
            "/api/missions/tasks",
            json={"title": "Delete Test"}
        )
        task = create_response.json()

        # Delete it
        response = client.delete(f"/api/missions/tasks/{task['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify it's gone
        get_response = client.get(f"/api/missions/tasks/{task['id']}")
        assert get_response.status_code == 404


class TestGetStats:
    """Tests for GET /api/missions/stats endpoint."""

    def test_get_stats(self, client):
        """Test getting mission statistics."""
        response = client.get("/api/missions/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "backlog" in data
        assert "todo" in data
        assert "doing" in data
        assert "blocked" in data
        assert "done" in data
        assert "by_priority" in data
