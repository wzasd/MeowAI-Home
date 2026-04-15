"""Tests for review API endpoints."""
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.auth.store import AuthStore
from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.review.watcher import ReviewWatcher
from src.review.router import ReviewRouterBuilder
from src.review.thread_router import ThreadRouter
from src.review.ci_tracker import CITracker
from tests.web.conftest import authenticate_client


@pytest.fixture
async def app_client():
    """Create a test client with review system initialized."""
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

        review_watcher = ReviewWatcher()
        app.state.review_watcher = review_watcher
        app.state.review_router = ReviewRouterBuilder.create_default_router()
        app.state.review_thread_router = ThreadRouter(tm)
        ci_tracker = CITracker(poll_interval=3600)
        app.state.ci_tracker = ci_tracker
        await ci_tracker.start()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await authenticate_client(client)
            yield client, review_watcher, ci_tracker

        await ci_tracker.stop()
        ThreadManager.reset()
        if hasattr(tm, '_store') and tm._store:
            await tm._store.close()


@pytest.mark.asyncio
async def test_list_pending_empty(app_client):
    """Test listing pending reviews when none exist."""
    client, _, _ = app_client
    response = await client.get("/api/review/pending")
    assert response.status_code == 200
    data = response.json()
    assert "reviews" in data
    assert data["reviews"] == []


@pytest.mark.asyncio
async def test_create_pr_tracking(app_client):
    """Test manually creating a PR tracking entry."""
    client, _, _ = app_client
    response = await client.post("/api/review/pr", json={
        "repository": "test/repo",
        "pr_number": 42,
        "pr_title": "Test PR",
        "pr_body": "This is a test PR",
        "branch": "feature/test",
        "author": "testuser",
        "labels": ["bug"],
        "reviewers": ["reviewer1"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["pr_number"] == 42
    assert data["repository"] == "test/repo"
    assert "thread_id" in data


@pytest.mark.asyncio
async def test_list_pending_after_create(app_client):
    """Test pending reviews after creating a PR."""
    client, _, _ = app_client
    await client.post("/api/review/pr", json={
        "repository": "test/repo",
        "pr_number": 1,
        "pr_title": "PR One",
    })

    response = await client.get("/api/review/pending")
    assert response.status_code == 200
    data = response.json()
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["pr_number"] == 1
    assert data["reviews"][0]["pr_title"] == "PR One"


@pytest.mark.asyncio
async def test_get_tracking(app_client):
    """Test getting tracking info for a specific PR."""
    client, _, _ = app_client
    await client.post("/api/review/pr", json={
        "repository": "test/repo",
        "pr_number": 7,
        "pr_title": "Get Me",
    })

    response = await client.get("/api/review/tracking/test/repo/7")
    assert response.status_code == 200
    data = response.json()
    assert data["pr_number"] == 7
    assert data["pr_title"] == "Get Me"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_tracking_not_found(app_client):
    """Test getting tracking for non-existent PR."""
    client, _, _ = app_client
    response = await client.get("/api/review/tracking/nonexistent/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_reviewer(app_client):
    """Test assigning a reviewer to a PR."""
    client, _, _ = app_client
    await client.post("/api/review/pr", json={
        "repository": "test/repo",
        "pr_number": 3,
        "pr_title": "Assign Me",
    })

    response = await client.post("/api/review/tracking/test/repo/3/assign", json={"cat_id": "inky"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["assigned_cat_id"] == "inky"

    # Verify via GET
    get_res = await client.get("/api/review/tracking/test/repo/3")
    assert get_res.json()["assigned_cat_id"] == "inky"


@pytest.mark.asyncio
async def test_assign_reviewer_not_found(app_client):
    """Test assigning reviewer to non-existent PR."""
    client, _, _ = app_client
    response = await client.post("/api/review/tracking/nonexistent/999/assign", json={"cat_id": "orange"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_tracking(app_client):
    """Test deleting a PR tracking entry."""
    client, _, _ = app_client
    await client.post("/api/review/pr", json={
        "repository": "test/repo",
        "pr_number": 5,
        "pr_title": "Delete Me",
    })

    response = await client.delete("/api/review/tracking/test/repo/5")
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Verify deleted
    get_res = await client.get("/api/review/tracking/test/repo/5")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_tracking_not_found(app_client):
    """Test deleting non-existent tracking."""
    client, _, _ = app_client
    response = await client.delete("/api/review/tracking/nonexistent/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_webhook_endpoint(app_client):
    """Test receiving a webhook."""
    client, watcher, _ = app_client
    payload = {
        "action": "opened",
        "pull_request": {
            "number": 101,
            "title": "Webhook PR",
            "body": "Body",
            "head": {"ref": "feature"},
            "user": {"login": "dev"},
            "labels": [],
            "requested_reviewers": [],
        },
        "repository": {"full_name": "org/repo"},
    }

    response = await client.post(
        "/api/review/webhook",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_type"] == "pull_request_opened"


@pytest.mark.asyncio
async def test_webhook_review_requested(app_client):
    """Test receiving a review_requested webhook."""
    client, watcher, _ = app_client
    payload = {
        "action": "review_requested",
        "pull_request": {
            "number": 102,
            "title": "Review Requested PR",
            "body": "Body",
            "head": {"ref": "feature"},
            "user": {"login": "dev"},
            "labels": [],
            "requested_reviewers": [{"login": "alice"}],
        },
        "repository": {"full_name": "org/repo"},
    }

    response = await client.post(
        "/api/review/webhook",
        json=payload,
        headers={"X-GitHub-Event": "pull_request"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event_type"] == "pull_request_review_requested"

    # Verify tracking was created and is pending
    tracking = watcher.get_tracking("org/repo", 102)
    assert tracking is not None
    assert tracking.status.value == "pending"


@pytest.mark.asyncio
async def test_suggest_reviewers(app_client):
    """Test reviewer suggestion endpoint."""
    client, _, _ = app_client
    response = await client.get("/api/review/suggest-reviewers?repository=test/repo&files=src/main.py,tests/test.py")
    assert response.status_code == 200
    data = response.json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_ci_status_empty(app_client):
    """Test CI status when no PRs are tracked."""
    client, _, _ = app_client
    response = await client.get("/api/review/ci/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["prs"] == []


@pytest.mark.asyncio
async def test_ci_poll(app_client):
    """Test manual CI poll."""
    client, _, _ = app_client
    response = await client.post("/api/review/ci/poll")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_imap_status_not_enabled(app_client):
    """Test IMAP status when not configured."""
    client, _, _ = app_client
    response = await client.get("/api/review/imap/status")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
