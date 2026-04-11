"""Tests for WorktreeManager."""
import tempfile
import shutil
import os

import pytest

from src.workspace.worktree_manager import WorktreeEntry, WorktreeManager


def test_worktree_manager_create_and_get():
    """Test creating and retrieving a worktree."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")

        # Create worktree
        entry = manager.create("thread-123", temp_dir)
        assert entry.id == "thread-123"
        assert entry.root.endswith("thread-123")

        # Get worktree
        retrieved = manager.get("thread-123")
        assert retrieved is not None
        assert retrieved.id == "thread-123"
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_manager_get_nonexistent():
    """Test getting a non-existent worktree returns None."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")
        result = manager.get("nonexistent-thread")
        assert result is None
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_manager_list_all():
    """Test listing all worktrees."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")

        # Create multiple worktrees
        manager.create("thread-1", temp_dir)
        manager.create("thread-2", temp_dir)
        manager.create("thread-3", temp_dir)

        # List all worktrees
        entries = manager.list_all()
        assert len(entries) == 3
        ids = {e.id for e in entries}
        assert ids == {"thread-1", "thread-2", "thread-3"}
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_manager_list_all_empty():
    """Test listing worktrees when none exist."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")
        entries = manager.list_all()
        assert entries == []
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_manager_delete():
    """Test deleting a worktree."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")

        # Create and then delete
        manager.create("thread-to-delete", temp_dir)
        assert manager.get("thread-to-delete") is not None

        manager.delete("thread-to-delete")
        assert manager.get("thread-to-delete") is None
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_manager_delete_nonexistent():
    """Test deleting a non-existent worktree does not raise."""
    temp_dir = tempfile.mkdtemp()
    try:
        manager = WorktreeManager(base_path=f"{temp_dir}/worktrees")
        # Should not raise
        manager.delete("nonexistent-thread")
    finally:
        shutil.rmtree(temp_dir)


def test_worktree_entry_dataclass():
    """Test WorktreeEntry dataclass."""
    entry = WorktreeEntry(
        id="test-id",
        root="/path/to/worktree",
        branch="main",
        head="abc123"
    )
    assert entry.id == "test-id"
    assert entry.root == "/path/to/worktree"
    assert entry.branch == "main"
    assert entry.head == "abc123"
