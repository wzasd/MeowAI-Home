"""Git Worktree manager for thread-isolated file workspaces."""
import subprocess
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorktreeEntry:
    id: str
    root: str
    branch: str
    head: str


class WorktreeManager:
    """Manages git worktrees for thread workspaces."""

    def __init__(self, base_path: str = ".claude/worktrees"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def create(self, thread_id: str, repo_root: str) -> WorktreeEntry:
        """Create a new worktree for a thread."""
        worktree_path = self.base_path / thread_id
        worktree_path.mkdir(parents=True, exist_ok=True)

        # Initialize git if needed
        git_dir = worktree_path / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=str(worktree_path),
                check=True,
            )

        return WorktreeEntry(
            id=thread_id,
            root=str(worktree_path),
            branch="main",
            head="initial",
        )

    def get(self, thread_id: str) -> Optional[WorktreeEntry]:
        """Get worktree info for a thread."""
        worktree_path = self.base_path / thread_id
        if not worktree_path.exists():
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
            )
            branch = result.stdout.strip() if result.returncode == 0 else "unknown"

            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
            )
            head = result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
        except Exception:
            branch = "main"
            head = "initial"

        return WorktreeEntry(
            id=thread_id,
            root=str(worktree_path),
            branch=branch,
            head=head,
        )

    def list_all(self) -> list[WorktreeEntry]:
        """List all worktrees."""
        entries = []
        for item in self.base_path.iterdir():
            if item.is_dir():
                entry = self.get(item.name)
                if entry:
                    entries.append(entry)
        return entries

    def delete(self, thread_id: str) -> None:
        """Delete a worktree."""
        import shutil
        worktree_path = self.base_path / thread_id
        if worktree_path.exists():
            shutil.rmtree(worktree_path)
