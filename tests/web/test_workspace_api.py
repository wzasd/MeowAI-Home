"""Tests for workspace API routes."""
import os
import pytest
import tempfile
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from src.thread.thread_manager import ThreadManager
from src.web.app import create_app
from src.workspace import WorktreeManager
from src.web.routes.workspace import reset_worktree_manager


@pytest.fixture
async def app_client():
    """Create a test client with a temp database and worktree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set environment variable for worktree base path
        os.environ["MEOWAI_WORKTREE_BASE"] = str(Path(tmpdir) / "worktrees")
        reset_worktree_manager()

        db_path = Path(tmpdir) / "test.db"
        ThreadManager.reset()

        app = create_app()
        tm = ThreadManager(db_path=db_path, skip_init=True)
        await tm.async_init()
        app.state.thread_manager = tm

        # Initialize registries
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

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, tmpdir

        ThreadManager.reset()
        reset_worktree_manager()
        if "MEOWAI_WORKTREE_BASE" in os.environ:
            del os.environ["MEOWAI_WORKTREE_BASE"]


@pytest.fixture
def worktree_manager(tmp_path):
    """Create a worktree manager with a temp base path."""
    manager = WorktreeManager(base_path=str(tmp_path / "worktrees"))
    return manager


@pytest.mark.asyncio
async def test_list_worktrees_empty(app_client):
    """Test listing worktrees when none exist."""
    client, tmpdir = app_client
    response = await client.get("/api/workspace/worktrees")
    assert response.status_code == 200
    data = response.json()
    assert "worktrees" in data
    assert isinstance(data["worktrees"], list)


@pytest.mark.asyncio
async def test_list_worktrees_with_entries(app_client):
    """Test listing worktrees with created entries."""
    client, tmpdir = app_client

    # Create a worktree manually
    worktree_path = Path(tmpdir) / "worktrees" / "test-thread"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    response = await client.get("/api/workspace/worktrees")
    assert response.status_code == 200
    data = response.json()
    assert "worktrees" in data
    assert len(data["worktrees"]) >= 1


@pytest.mark.asyncio
async def test_get_tree_not_found(app_client):
    """Test getting tree for non-existent worktree."""
    client, tmpdir = app_client
    response = await client.get("/api/workspace/tree?worktreeId=nonexistent&path=")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_tree_success(app_client):
    """Test getting file tree."""
    client, tmpdir = app_client

    # Create a worktree with some files
    worktree_path = Path(tmpdir) / "worktrees" / "test-tree"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    # Create test files
    (worktree_path / "file1.txt").write_text("Hello World")
    subdir = worktree_path / "subdir"
    subdir.mkdir()
    (subdir / "file2.txt").write_text("Nested file")

    response = await client.get("/api/workspace/tree?worktreeId=test-tree&path=&depth=3")
    assert response.status_code == 200
    data = response.json()
    assert "tree" in data
    assert isinstance(data["tree"], list)

    # Check that files are in tree
    paths = [node["path"] for node in data["tree"]]
    assert "file1.txt" in paths
    assert "subdir" in paths


@pytest.mark.asyncio
async def test_get_tree_path_traversal(app_client):
    """Test path traversal protection."""
    client, tmpdir = app_client

    # Create a worktree
    worktree_path = Path(tmpdir) / "worktrees" / "test-traversal"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    # Try path traversal
    response = await client.get("/api/workspace/tree?worktreeId=test-traversal&path=../../../etc&depth=1")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_file_not_found(app_client):
    """Test getting non-existent file."""
    client, tmpdir = app_client

    # Create a worktree
    worktree_path = Path(tmpdir) / "worktrees" / "test-file"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    response = await client.get("/api/workspace/file?worktreeId=test-file&path=nonexistent.txt")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_file_success(app_client):
    """Test getting file content."""
    client, tmpdir = app_client

    # Create a worktree with a file
    worktree_path = Path(tmpdir) / "worktrees" / "test-file-read"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()
    (worktree_path / "test.txt").write_text("Hello World")

    response = await client.get("/api/workspace/file?worktreeId=test-file-read&path=test.txt")
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "test.txt"
    assert data["content"] == "Hello World"
    assert data["binary"] is False
    assert "sha256" in data
    assert "mime" in data


@pytest.mark.asyncio
async def test_get_file_path_traversal(app_client):
    """Test file path traversal protection."""
    client, tmpdir = app_client

    # Create a worktree
    worktree_path = Path(tmpdir) / "worktrees" / "test-file-trav"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    response = await client.get("/api/workspace/file?worktreeId=test-file-trav&path=../../../etc/passwd")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_filename(app_client):
    """Test filename search."""
    client, tmpdir = app_client

    # Create a worktree with files
    worktree_path = Path(tmpdir) / "worktrees" / "test-search"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()
    (worktree_path / "hello.py").write_text("print('hello')")
    (worktree_path / "world.py").write_text("print('world')")

    response = await client.post("/api/workspace/search", json={
        "worktreeId": "test-search",
        "query": "hello",
        "type": "filename"
    })
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    # Should find hello.py
    assert any("hello.py" in r["path"] for r in data["results"])


@pytest.mark.asyncio
async def test_search_content(app_client):
    """Test content search."""
    client, tmpdir = app_client

    # Create a worktree with files
    worktree_path = Path(tmpdir) / "worktrees" / "test-content"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()
    (worktree_path / "main.py").write_text("def hello():\n    print('Hello World')\n    return 42")

    response = await client.post("/api/workspace/search", json={
        "worktreeId": "test-content",
        "query": "Hello World",
        "type": "content"
    })
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0
    assert any("Hello World" in r["content"] for r in data["results"])


@pytest.mark.asyncio
async def test_search_not_found(app_client):
    """Test search for non-existent worktree."""
    client, tmpdir = app_client
    response = await client.post("/api/workspace/search", json={
        "worktreeId": "nonexistent",
        "query": "test",
        "type": "content"
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reveal_not_found(app_client):
    """Test reveal for non-existent worktree."""
    client, tmpdir = app_client
    response = await client.post("/api/workspace/reveal", json={
        "worktreeId": "nonexistent",
        "path": "test.txt"
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reveal_path_traversal(app_client):
    """Test reveal path traversal protection."""
    client, tmpdir = app_client

    # Create a worktree
    worktree_path = Path(tmpdir) / "worktrees" / "test-reveal"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").mkdir()

    response = await client.post("/api/workspace/reveal", json={
        "worktreeId": "test-reveal",
        "path": "../../../etc/passwd"
    })
    assert response.status_code == 403
