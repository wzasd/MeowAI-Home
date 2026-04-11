"""Tests for Queue API endpoints."""
import pytest
from fastapi.testclient import TestClient

from src.web.routes.queue import router, _queue_entries


@pytest.fixture
def client():
    """Create test client with queue router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_queue():
    """Clear queue before each test."""
    _queue_entries.clear()
    yield
    _queue_entries.clear()


class TestListEntries:
    """Tests for GET /api/queue/entries"""

    def test_empty_list(self, client):
        """Should return empty list when no entries."""
        response = client.get("/api/queue/entries")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_entries(self, client):
        """Should return all entries."""
        entry = {
            "id": "test1",
            "content": "Test content",
            "targetCats": ["orange"],
            "status": "queued",
            "createdAt": "2024-01-01T10:00:00"
        }
        client.post("/api/queue/entries", json=entry)

        response = client.get("/api/queue/entries")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test1"

    def test_filter_by_thread(self, client):
        """Should filter entries by threadId."""
        entry1 = {
            "id": "t1",
            "content": "Content 1",
            "targetCats": ["orange"],
            "status": "queued",
            "createdAt": "2024-01-01T10:00:00",
            "threadId": "thread-a"
        }
        entry2 = {
            "id": "t2",
            "content": "Content 2",
            "targetCats": ["inky"],
            "status": "queued",
            "createdAt": "2024-01-01T11:00:00",
            "threadId": "thread-b"
        }
        client.post("/api/queue/entries", json=entry1)
        client.post("/api/queue/entries", json=entry2)

        response = client.get("/api/queue/entries?threadId=thread-a")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "t1"


class TestCreateEntry:
    """Tests for POST /api/queue/entries"""

    def test_create_entry(self, client):
        """Should create a new entry."""
        entry = {
            "id": "new1",
            "content": "New entry",
            "targetCats": ["patch"],
            "status": "queued",
            "createdAt": "2024-01-01T12:00:00"
        }
        response = client.post("/api/queue/entries", json=entry)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "new1"
        assert data["content"] == "New entry"

    def test_create_entry_auto_id(self, client):
        """Should auto-generate id if not provided."""
        entry = {
            "content": "Auto ID entry",
            "targetCats": ["orange"],
            "status": "queued",
            "createdAt": ""
        }
        response = client.post("/api/queue/entries", json=entry)
        assert response.status_code == 200
        data = response.json()
        assert len(data["id"]) > 0
        assert data["createdAt"] != ""


class TestPauseEntry:
    """Tests for POST /api/queue/entries/{id}/pause"""

    def test_pause_entry(self, client):
        """Should pause an entry."""
        entry = {
            "id": "pause1",
            "content": "To be paused",
            "targetCats": ["orange"],
            "status": "queued",
            "createdAt": "2024-01-01T10:00:00"
        }
        client.post("/api/queue/entries", json=entry)

        response = client.post("/api/queue/entries/pause1/pause")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert _queue_entries["pause1"].status == "paused"

    def test_pause_not_found(self, client):
        """Should return 404 for non-existent entry."""
        response = client.post("/api/queue/entries/nonexistent/pause")
        assert response.status_code == 404


class TestResumeEntry:
    """Tests for POST /api/queue/entries/{id}/resume"""

    def test_resume_entry(self, client):
        """Should resume a paused entry."""
        entry = {
            "id": "resume1",
            "content": "To be resumed",
            "targetCats": ["orange"],
            "status": "paused",
            "createdAt": "2024-01-01T10:00:00"
        }
        client.post("/api/queue/entries", json=entry)

        response = client.post("/api/queue/entries/resume1/resume")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert _queue_entries["resume1"].status == "queued"

    def test_resume_not_found(self, client):
        """Should return 404 for non-existent entry."""
        response = client.post("/api/queue/entries/nonexistent/resume")
        assert response.status_code == 404


class TestRemoveEntry:
    """Tests for DELETE /api/queue/entries/{id}"""

    def test_remove_entry(self, client):
        """Should remove an entry."""
        entry = {
            "id": "remove1",
            "content": "To be removed",
            "targetCats": ["orange"],
            "status": "queued",
            "createdAt": "2024-01-01T10:00:00"
        }
        client.post("/api/queue/entries", json=entry)

        response = client.delete("/api/queue/entries/remove1")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "remove1" not in _queue_entries

    def test_remove_not_found(self, client):
        """Should return 404 for non-existent entry."""
        response = client.delete("/api/queue/entries/nonexistent")
        assert response.status_code == 404
