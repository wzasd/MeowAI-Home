"""Workspace API routes for file system access."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

router = APIRouter(prefix="/workspace", tags=["workspace"])

# Import worktree manager
from src.workspace import WorktreeManager

_worktree_manager = None


def get_worktree_manager():
    global _worktree_manager
    if _worktree_manager is None:
        # Allow overriding base path via environment variable for testing
        base_path = os.environ.get("MEOWAI_WORKTREE_BASE", ".claude/worktrees")
        _worktree_manager = WorktreeManager(base_path=base_path)
    return _worktree_manager


def reset_worktree_manager():
    """Reset the global worktree manager (for testing)."""
    global _worktree_manager
    _worktree_manager = None


class WorktreeListResponse(BaseModel):
    worktrees: list[dict]


class TreeNode(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    children: Optional[list["TreeNode"]] = None


class TreeResponse(BaseModel):
    tree: list[TreeNode]


class FileData(BaseModel):
    path: str
    content: str
    sha256: str
    size: int
    mime: str
    truncated: bool
    binary: bool = False


class SearchResult(BaseModel):
    path: str
    line: int
    content: str
    context_before: str = ""
    context_after: str = ""


class SearchResponse(BaseModel):
    results: list[SearchResult]


@router.get("/worktrees", response_model=WorktreeListResponse)
async def list_worktrees():
    """List all available worktrees."""
    manager = get_worktree_manager()
    entries = manager.list_all()
    return {
        "worktrees": [
            {
                "id": e.id,
                "root": e.root,
                "branch": e.branch,
                "head": e.head,
            }
            for e in entries
        ]
    }


@router.get("/tree", response_model=TreeResponse)
async def get_tree(
    worktreeId: str = Query(..., description="Worktree ID"),
    path: str = Query("", description="Subdirectory path"),
    depth: int = Query(3, description="Depth to fetch"),
):
    """Get file tree for a worktree."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    base_path = Path(entry.root)
    if path:
        base_path = base_path / path

    # Resolve path and check for traversal
    resolved_path = base_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    def build_tree(p: Path, current_depth: int) -> list[TreeNode]:
        if current_depth <= 0:
            return []

        nodes = []
        try:
            for item in sorted(p.iterdir()):
                if item.name.startswith(".") and item.name != ".git":
                    continue

                rel_path = str(item.relative_to(entry.root))
                if item.is_dir():
                    children = build_tree(item, current_depth - 1) if current_depth > 1 else None
                    nodes.append(TreeNode(
                        name=item.name,
                        path=rel_path,
                        type="directory",
                        children=children,
                    ))
                else:
                    nodes.append(TreeNode(
                        name=item.name,
                        path=rel_path,
                        type="file",
                    ))
        except PermissionError:
            pass
        return nodes

    tree = build_tree(base_path, depth)
    return {"tree": tree}


@router.get("/file")
async def get_file(
    worktreeId: str = Query(...),
    path: str = Query(...),
):
    """Get file content."""
    manager = get_worktree_manager()
    entry = manager.get(worktreeId)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    file_path = Path(entry.root) / path
    resolved_path = file_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    import hashlib
    import mimetypes

    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"

    # Check if binary
    is_binary = False
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(8192)
            if b'\x00' in chunk:
                is_binary = True
    except Exception:
        pass

    if is_binary:
        return FileData(
            path=path,
            content="",
            sha256="",
            size=file_path.stat().st_size,
            mime=mime,
            truncated=True,
            binary=True,
        )

    # Read text content (max 1MB)
    content = file_path.read_text(encoding="utf-8", errors="replace")
    truncated = len(content) > 1000000
    if truncated:
        content = content[:1000000]

    sha256 = hashlib.sha256(content.encode()).hexdigest()

    return FileData(
        path=path,
        content=content,
        sha256=sha256,
        size=len(content),
        mime=mime,
        truncated=truncated,
        binary=False,
    )


@router.post("/search", response_model=SearchResponse)
async def search_workspace(request: dict):
    """Search files in workspace."""
    worktree_id = request.get("worktreeId")
    query = request.get("query", "")
    search_type = request.get("type", "content")

    manager = get_worktree_manager()
    entry = manager.get(worktree_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    results = []
    root = Path(entry.root)

    if search_type == "filename":
        for item in root.rglob("*"):
            if query.lower() in item.name.lower():
                rel_path = str(item.relative_to(root))
                results.append(SearchResult(
                    path=rel_path,
                    line=0,
                    content=item.name,
                ))
    else:  # content search
        for item in root.rglob("*"):
            if item.is_file() and item.stat().st_size < 1024 * 1024:
                try:
                    content = item.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")
                    for i, line in enumerate(lines, 1):
                        if query.lower() in line.lower():
                            rel_path = str(item.relative_to(root))
                            results.append(SearchResult(
                                path=rel_path,
                                line=i,
                                content=line.strip()[:200],
                                context_before=lines[max(0, i-2):i-1][0] if i > 1 else "",
                                context_after=lines[i:i+1][0] if i < len(lines) else "",
                            ))
                except Exception:
                    continue

    return {"results": results[:100]}


@router.post("/reveal")
async def reveal_in_finder(request: dict):
    """Reveal file in system file manager."""
    worktree_id = request.get("worktreeId")
    path = request.get("path", "")

    manager = get_worktree_manager()
    entry = manager.get(worktree_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Worktree not found")

    file_path = Path(entry.root) / path
    resolved_path = file_path.resolve()
    resolved_root = Path(entry.root).resolve()
    if not str(resolved_path).startswith(str(resolved_root)):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", "-R", str(file_path)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(file_path.parent)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", "/select,", str(file_path)], check=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reveal: {e}")

    return {"success": True}
