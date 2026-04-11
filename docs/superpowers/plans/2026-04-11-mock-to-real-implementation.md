# MeowAI Home Mock 数据替换完整实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将所有前端 Mock 数据替换为真实后端 API，并实现完整的 Workspace 文件系统（基于 Git Worktree）。

**Architecture:** 后端使用 Git Worktree 实现线程级文件隔离，前端通过统一 API 层访问。每个模块独立实现，遵循先 API → 后 Hook → 最后 UI 的顺序。

**Tech Stack:** FastAPI + React + Zustand + Git Worktree

---

## 文件映射表

### Mock 数据文件清单

| 组件 | 文件路径 | Mock 数据 | 依赖后端模块 |
|------|---------|-----------|-------------|
| WorkspacePanel | `web/src/components/workspace/WorkspacePanel.tsx` | `MOCK_TREE` | Workspace API + Git |
| QueuePanel | `web/src/components/right-panel/QueuePanel.tsx` | `MOCK_QUEUE` | InvocationQueue API |
| SignalInboxPage | `web/src/components/signals/SignalInboxPage.tsx` | `MOCK_ARTICLES`, `MOCK_SOURCES` | Signal 系统 API |
| AuditPanel | `web/src/components/audit/AuditPanel.tsx` | `MOCK_ENTRIES` | AuditLog API |
| TaskPanel | `web/src/components/right-panel/TaskPanel.tsx` | `MOCK_TASKS` | Task API |
| QuotaBoard | `web/src/components/settings/QuotaBoard.tsx` | `MOCK_METRICS` | Metrics API |
| LeaderboardTab | `web/src/components/settings/LeaderboardTab.tsx` | `MOCK_LEADERBOARD` | Metrics API |
| TokenUsagePanel | `web/src/components/right-panel/TokenUsagePanel.tsx` | `MOCK_USAGE` | TokenUsage API |
| MissionHubPage | `web/src/components/mission/MissionHubPage.tsx` | `MOCK_TASKS` | Mission API |
| HistorySearchModal | `web/src/components/chat/HistorySearchModal.tsx` | `MOCK_RESULTS` | Search API |

---

## Phase 1: Workspace 文件系统（P0 - 最高优先级）

### 任务 1.1: Thread 模型添加 projectPath 字段

**Files:**
- Modify: `src/thread/models.py`
- Modify: `src/web/routes/threads.py` (确保返回 project_path)
- Test: `tests/thread/test_thread_models.py`

- [ ] **Step 1: 添加 project_path 字段到 Thread 模型**

在 `Thread` 类中添加：
```python
project_path: Optional[str] = None  # Git 仓库根路径
```

- [ ] **Step 2: 创建数据库迁移脚本**

创建 `migrations/add_thread_project_path.sql`：
```sql
ALTER TABLE threads ADD COLUMN project_path TEXT;
```

- [ ] **Step 3: 更新 Thread 创建 API 接受 project_path**

在 `create_thread` 端点中添加可选的 `project_path` 参数。

- [ ] **Step 4: 运行测试验证**

```bash
cd /Users/wangzhao/Documents/claude_projects/catwork
python -m pytest tests/thread/ -v -k "thread" --tb=short
```

---

### 任务 1.2: Git Worktree 管理器

**Files:**
- Create: `src/workspace/__init__.py`
- Create: `src/workspace/worktree_manager.py`
- Test: `tests/workspace/test_worktree_manager.py`

- [ ] **Step 1: 实现 WorktreeManager 类**

```python
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
```

- [ ] **Step 2: 编写测试**

```python
def test_worktree_manager_create_and_get():
    import tempfile
    import shutil

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
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/workspace/test_worktree_manager.py -v
```

---

### 任务 1.3: Workspace API 路由

**Files:**
- Create: `src/web/routes/workspace.py`
- Modify: `src/web/server.py` (注册路由)
- Test: `tests/web/test_workspace_api.py`

- [ ] **Step 1: 实现 Workspace API 路由**

```python
"""Workspace API routes for file system access."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import os
from pathlib import Path

router = APIRouter(prefix="/api/workspace", tags=["workspace"])

# In-memory store (replace with proper DI in production)
_worktree_manager = None

def get_worktree_manager():
    global _worktree_manager
    if _worktree_manager is None:
        from src.workspace.worktree_manager import WorktreeManager
        _worktree_manager = WorktreeManager()
    return _worktree_manager

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

    if not str(base_path).startswith(entry.root):
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
    if not str(file_path).startswith(entry.root):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    import hashlib
    import mimetypes

    # Check if binary
    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"

    # Read first 8KB to check binary
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
async def search_workspace(
    request: dict,
):
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
        import re
        for item in root.rglob("*"):
            if item.is_file() and item.stat().st_size < 1024 * 1024:  # Skip files > 1MB
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

    return {"results": results[:100]}  # Limit results

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
    if not str(file_path).startswith(entry.root):
        raise HTTPException(status_code=403, detail="Path traversal detected")

    # Platform-specific reveal
    import platform
    import subprocess

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", "-R", str(file_path)], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", str(file_path.parent)], check=True)
        elif system == "Windows":
            subprocess.run(["explorer", "/select,", str(file_path)], check=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reveal: {e}")

    return {"success": True}
```

- [ ] **Step 2: 在 server.py 注册路由**

```python
from src.web.routes import workspace
app.include_router(workspace.router)
```

- [ ] **Step 3: 测试 API 端点**

```bash
# Start server
meowai start &

# Test endpoints
curl http://localhost:8000/api/workspace/worktrees
curl "http://localhost:8000/api/workspace/tree?worktreeId=test&depth=2"
```

---

### 任务 1.4: 前端 useWorkspace Hook

**Files:**
- Create: `web/src/hooks/useWorkspace.ts`
- Test: `web/src/hooks/__tests__/useWorkspace.test.ts`

- [ ] **Step 1: 实现 useWorkspace Hook**

参考 Clowder AI 实现：

```typescript
"use client";

import { useCallback, useEffect, useState } from "react";
import { useThreadStore } from "../stores/threadStore";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface WorktreeEntry {
  id: string;
  root: string;
  branch: string;
  head: string;
}

export interface TreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeNode[];
}

export interface FileData {
  path: string;
  content: string;
  sha256: string;
  size: number;
  mime: string;
  truncated: boolean;
  binary?: boolean;
}

export interface SearchResult {
  path: string;
  line: number;
  content: string;
  contextBefore: string;
  contextAfter: string;
  matchType?: "filename" | "content";
}

function mergeSubtree(nodes: TreeNode[], targetPath: string, children: TreeNode[]): TreeNode[] {
  return nodes.map((node) => {
    if (node.path === targetPath && node.type === "directory") {
      return { ...node, children };
    }
    if (node.children && targetPath.startsWith(`${node.path}/`)) {
      return { ...node, children: mergeSubtree(node.children, targetPath, children) };
    }
    return node;
  });
}

export function useWorkspace() {
  const currentThreadId = useThreadStore((s) => s.currentThreadId);

  const [worktrees, setWorktrees] = useState<WorktreeEntry[]>([]);
  const [worktreeId, setWorktreeId] = useState<string | null>(null);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [file, setFile] = useState<FileData | null>(null);
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openFilePath, setOpenFilePath] = useState<string | null>(null);

  // Fetch worktrees
  const fetchWorktrees = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/workspace/worktrees`);
      if (res.ok) {
        const data = await res.json();
        setWorktrees(data.worktrees ?? []);
        // Auto-select current thread's worktree or first available
        const current = data.worktrees.find((w: WorktreeEntry) => w.id === currentThreadId);
        if (current) {
          setWorktreeId(current.id);
        } else if (data.worktrees.length > 0 && !worktreeId) {
          setWorktreeId(data.worktrees[0].id);
        }
      }
    } catch {
      /* ignore */
    }
  }, [currentThreadId, worktreeId]);

  useEffect(() => {
    fetchWorktrees();
  }, [fetchWorktrees]);

  // Fetch tree when worktree changes
  const fetchTree = useCallback(
    async (subpath?: string) => {
      if (!worktreeId) return;
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ worktreeId, depth: "3" });
        if (subpath) params.set("path", subpath);
        const res = await fetch(`${API_BASE}/api/workspace/tree?${params}`);
        if (res.ok) {
          const data = await res.json();
          setTree(data.tree ?? []);
        } else {
          setError("Failed to load file tree");
        }
      } catch {
        setError("Failed to load file tree");
      } finally {
        setLoading(false);
      }
    },
    [worktreeId]
  );

  useEffect(() => {
    if (worktreeId) fetchTree();
  }, [worktreeId, fetchTree]);

  // Lazy-load subtree
  const fetchSubtree = useCallback(
    async (dirPath: string) => {
      if (!worktreeId) return;
      try {
        const params = new URLSearchParams({ worktreeId, path: dirPath, depth: "3" });
        const res = await fetch(`${API_BASE}/api/workspace/tree?${params}`);
        if (!res.ok) return;
        const data = await res.json();
        const subtreeChildren: TreeNode[] = data.tree ?? [];
        setTree((prev) => mergeSubtree(prev, dirPath, subtreeChildren));
      } catch {
        /* ignore */
      }
    },
    [worktreeId]
  );

  // Fetch file content
  const fetchFile = useCallback(
    async (path: string) => {
      if (!worktreeId) return;
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({ worktreeId, path });
        const res = await fetch(`${API_BASE}/api/workspace/file?${params}`);
        if (res.ok) {
          const data = await res.json();
          setFile(data);
        } else {
          const data = await res.json().catch(() => ({ error: "Unknown error" }));
          setError(data.error ?? "Failed to load file");
        }
      } catch {
        setError("Failed to load file");
      } finally {
        setLoading(false);
      }
    },
    [worktreeId]
  );

  // Load file when openFilePath changes
  useEffect(() => {
    if (openFilePath) fetchFile(openFilePath);
    else setFile(null);
  }, [openFilePath, fetchFile]);

  // Search
  const search = useCallback(
    async (query: string, type: "content" | "filename" | "all" = "content") => {
      if (!worktreeId || !query.trim()) return;
      setSearchLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/api/workspace/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ worktreeId, query, type }),
        });
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.results ?? []);
        }
      } catch {
        setSearchResults([]);
        setError("Failed to search workspace");
      } finally {
        setSearchLoading(false);
      }
    },
    [worktreeId]
  );

  // Reveal in finder
  const revealInFinder = useCallback(
    async (path: string) => {
      if (!worktreeId) return;
      try {
        await fetch(`${API_BASE}/api/workspace/reveal`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ worktreeId, path }),
        });
      } catch {
        /* ignore */
      }
    },
    [worktreeId]
  );

  return {
    worktrees,
    worktreeId,
    tree,
    file,
    openFilePath,
    setOpenFilePath,
    searchResults,
    loading,
    searchLoading,
    error,
    fetchWorktrees,
    fetchTree,
    fetchSubtree,
    fetchFile,
    search,
    setSearchResults,
    revealInFinder,
  };
}
```

- [ ] **Step 2: 验证 Hook 类型正确**

```bash
cd /Users/wangzhao/Documents/claude_projects/catwork/web
npx tsc --noEmit src/hooks/useWorkspace.ts
```

---

### 任务 1.5: 重写 WorkspacePanel 组件

**Files:**
- Modify: `web/src/components/workspace/WorkspacePanel.tsx`

- [ ] **Step 1: 用 useWorkspace 替换 MOCK_TREE**

重写整个组件，使用真实的 `useWorkspace` hook：

```typescript
/** Workspace IDE panel — file tree + code viewer + terminal + browser preview. */

import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  Search,
  Plus,
  RefreshCw,
  Terminal,
  Globe,
  GitBranch,
  Activity,
  Eye,
  X,
  PanelLeftClose,
  PanelLeftOpen,
  FileText,
  Loader2,
} from "lucide-react";
import { useWorkspace, type TreeNode } from "../../hooks/useWorkspace";

const FILE_ICONS: Record<string, string> = {
  py: "🐍",
  tsx: "⚛️",
  ts: "⚛️",
  js: "📜",
  jsx: "⚛️",
  json: "📋",
  md: "📝",
  toml: "⚙️",
  yaml: "⚙️",
  yml: "⚙️",
  css: "🎨",
  scss: "🎨",
  html: "🌐",
  rs: "🦀",
  go: "🐹",
  java: "☕",
};

function FileTreeItem({
  node,
  depth,
  selectedPath,
  onSelect,
  onExpand,
}: {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onExpand: (path: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const isSelected = selectedPath === node.path;
  const ext = node.name.split(".").pop()?.toLowerCase() || "";

  const handleClick = () => {
    if (isDir) {
      setExpanded(!expanded);
      if (!expanded && !node.children) {
        onExpand(node.path);
      }
    }
    onSelect(node.path);
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 ${
          isSelected
            ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
            : "text-gray-700 dark:text-gray-300"
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isDir ? (
          expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
        ) : (
          <span className="w-3" />
        )}
        {isDir ? (
          expanded ? (
            <FolderOpen size={12} className="text-amber-500" />
          ) : (
            <Folder size={12} className="text-amber-500" />
          )
        ) : (
          <span className="text-[10px]">{FILE_ICONS[ext] || "📄"}</span>
        )}
        <span className="truncate">{node.name}</span>
      </button>
      {isDir && expanded && node.children?.map((child) => (
        <FileTreeItem
          key={child.path}
          node={child}
          depth={depth + 1}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onExpand={onExpand}
        />
      ))}
    </div>
  );
}

export function WorkspacePanel() {
  const {
    tree,
    file,
    loading,
    error,
    fetchTree,
    fetchSubtree,
    openFilePath,
    setOpenFilePath,
    search,
    searchResults,
    setSearchResults,
  } = useWorkspace();

  const [showTree, setShowTree] = useState(true);
  const [activeBottomTab, setActiveBottomTab] = useState<"terminal" | "preview" | "git" | "health">("terminal");
  const [showBottom, setShowBottom] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      await search(searchQuery, "all");
      setShowSearch(true);
    }
  };

  const handleSelectFile = (path: string) => {
    setOpenFilePath(path);
    setShowSearch(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-3 py-1.5 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTree(!showTree)}
            className="rounded p-1 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            {showTree ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
          </button>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400 truncate max-w-[200px]">
            {openFilePath || "选择文件"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <form onSubmit={handleSearch} className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索..."
              className="w-32 rounded border border-gray-200 bg-white px-2 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-700"
            />
            <button
              type="submit"
              className="absolute right-0.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-gray-400 hover:text-gray-600"
            >
              <Search size={12} />
            </button>
          </form>
          <button
            onClick={() => fetchTree()}
            className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-700"
            disabled={loading}
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File tree */}
        {showTree && (
          <div className="w-56 shrink-0 overflow-y-auto border-r border-gray-200 bg-gray-50 py-1 dark:border-gray-700 dark:bg-gray-800/50">
            {tree.map((node) => (
              <FileTreeItem
                key={node.path}
                node={node}
                depth={0}
                selectedPath={openFilePath}
                onSelect={handleSelectFile}
                onExpand={fetchSubtree}
              />
            ))}
            {tree.length === 0 && !loading && (
              <div className="px-3 py-4 text-center text-xs text-gray-400">
                暂无文件
              </div>
            )}
          </div>
        )}

        {/* Main area */}
        <div className="flex flex-1 flex-col">
          {/* Search results */}
          {showSearch && searchResults.length > 0 && (
            <div className="max-h-40 overflow-y-auto border-b border-gray-200 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  搜索结果 ({searchResults.length})
                </span>
                <button
                  onClick={() => { setShowSearch(false); setSearchResults([]); }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X size={12} />
                </button>
              </div>
              {searchResults.map((result, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectFile(result.path)}
                  className="w-full rounded p-1.5 text-left text-xs hover:bg-gray-200 dark:hover:bg-gray-700"
                >
                  <span className="font-medium text-blue-600">{result.path}</span>
                  {result.line > 0 && (
                    <span className="ml-2 text-gray-400">:{result.line}</span>
                  )}
                  <p className="truncate text-gray-500">{result.content}</p>
                </button>
              ))}
            </div>
          )}

          {/* Code area */}
          <div className="flex-1 overflow-auto bg-gray-900 p-4 font-mono text-xs leading-relaxed">
            {error ? (
              <div className="flex h-full items-center justify-center text-red-400">
                {error}
              </div>
            ) : file ? (
              file.binary ? (
                <div className="flex h-full items-center justify-center text-gray-500">
                  <FileText size={32} className="mr-4" />
                  <div>
                    <p>二进制文件</p>
                    <p className="text-sm text-gray-400">{file.mime}</p>
                  </div>
                </div>
              ) : (
                <pre className="text-gray-300">
                  <span className="text-gray-500">{"# "}{file.path}</span>{"\n\n"}
                  {file.content}
                  {file.truncated && (
                    <span className="text-amber-500">\n\n[文件已截断]</span>
                  )}
                </pre>
              )
            ) : loading ? (
              <div className="flex h-full items-center justify-center text-gray-500">
                <Loader2 size={24} className="animate-spin" />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-500">
                选择文件查看代码
              </div>
            )}
          </div>

          {/* Bottom panel */}
          {showBottom && (
            <div className="h-40 shrink-0 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center border-b border-gray-200 bg-gray-50 px-2 dark:border-gray-700 dark:bg-gray-800">
                {[
                  { key: "terminal" as const, icon: Terminal, label: "终端" },
                  { key: "preview" as const, icon: Eye, label: "预览" },
                  { key: "git" as const, icon: GitBranch, label: "Git" },
                  { key: "health" as const, icon: Activity, label: "健康" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveBottomTab(t.key)}
                    className={`flex items-center gap-1 px-2 py-1 text-[10px] font-medium ${
                      activeBottomTab === t.key
                        ? "border-b-2 border-blue-500 text-blue-600 dark:text-blue-400"
                        : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    <t.icon size={10} /> {t.label}
                  </button>
                ))}
                <button
                  onClick={() => setShowBottom(false)}
                  className="ml-auto rounded p-0.5 text-gray-400 hover:text-gray-600"
                >
                  <X size={12} />
                </button>
              </div>
              <div className="h-full overflow-auto bg-gray-900 p-2 font-mono text-xs text-gray-400">
                {activeBottomTab === "terminal" && (
                  <div>
                    <span className="text-green-400">meowai@home</span>
                    <span className="text-gray-500">:</span>
                    <span className="text-blue-400">~</span>
                    <span className="text-gray-500">$ </span>
                    <span className="animate-pulse text-gray-300">_</span>
                  </div>
                )}
                {activeBottomTab === "preview" && (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    <Globe size={16} className="mr-2" /> 预览面板（开发中）
                  </div>
                )}
                {activeBottomTab === "git" && (
                  <div>
                    <span className="text-green-400">On branch </span>
                    <span className="text-yellow-300">main</span>{"\n"}
                    <span className="text-gray-400">nothing to commit, working tree clean</span>
                  </div>
                )}
                {activeBottomTab === "health" && (
                  <div>
                    <span className="text-green-400">Health check: </span>
                    <span className="text-gray-300">All systems nominal</span>{"\n"}
                    <span className="text-gray-400">Tests: 1215/1216 passed</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证组件编译无误**

```bash
cd /Users/wangzhao/Documents/claude_projects/catwork/web
npx tsc --noEmit src/components/workspace/WorkspacePanel.tsx
```

---

## Phase 2: 任务/队列/用量面板 (P1)

### 任务 2.1: QueuePanel 真实数据

**Files:**
- Modify: `web/src/components/right-panel/QueuePanel.tsx`
- Create: `src/invocation/queue.py` (如不存在)
- Create: `src/web/routes/queue.py`

- [ ] **Step 1: 添加后端 API 路由**

```python
# src/web/routes/queue.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

router = APIRouter(prefix="/api/queue", tags=["queue"])

class QueueEntry(BaseModel):
    id: str
    content: str
    targetCats: list[str]
    status: Literal["queued", "processing", "paused"]
    createdAt: str

# In-memory queue for now (replace with proper storage)
_queue: list[QueueEntry] = []

@router.get("/entries")
async def list_queue_entries(threadId: str = None):
    """Get queue entries for a thread."""
    if threadId:
        return [e for e in _queue if e.id.startswith(threadId)]
    return _queue

@router.post("/entries/{entryId}/pause")
async def pause_entry(entryId: str):
    for e in _queue:
        if e.id == entryId:
            e.status = "paused"
            return {"success": True}
    return {"success": False, "error": "Not found"}

@router.post("/entries/{entryId}/resume")
async def resume_entry(entryId: str):
    for e in _queue:
        if e.id == entryId:
            e.status = "queued"
            return {"success": True}
    return {"success": False, "error": "Not found"}

@router.delete("/entries/{entryId}")
async def remove_entry(entryId: str):
    global _queue
    _queue = [e for e in _queue if e.id != entryId]
    return {"success": True}
```

- [ ] **Step 2: 重写 QueuePanel 使用真实 API**

```typescript
// web/src/components/right-panel/QueuePanel.tsx
import { useState, useEffect } from "react";
import { GripVertical, X, Play, Pause } from "lucide-react";

interface QueueEntry {
  id: string;
  content: string;
  targetCats: string[];
  status: "queued" | "processing" | "paused";
  createdAt: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function QueuePanel({ threadId }: { threadId: string | null }) {
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEntries = async () => {
    if (!threadId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/queue/entries?threadId=${threadId}`);
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 5000);
    return () => clearInterval(interval);
  }, [threadId]);

  const remove = async (id: string) => {
    await fetch(`${API_BASE}/api/queue/entries/${id}`, { method: "DELETE" });
    fetchEntries();
  };

  const togglePause = async (id: string, currentStatus: string) => {
    const action = currentStatus === "paused" ? "resume" : "pause";
    await fetch(`${API_BASE}/api/queue/entries/${id}/${action}`, { method: "POST" });
    fetchEntries();
  };

  if (entries.length === 0) {
    return <p className="text-sm text-gray-400">队列为空</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">调用队列</h4>
        <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          {entries.length} 条
        </span>
      </div>

      <div className="space-y-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`rounded-lg border p-2 ${
              entry.status === "processing"
                ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
                : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 cursor-grab text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <GripVertical size={12} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs text-gray-800 dark:text-gray-200">{entry.content}</p>
                <div className="mt-1 flex items-center gap-1">
                  {entry.targetCats.map((cat) => (
                    <span
                      key={cat}
                      className="rounded bg-purple-50 px-1 py-0.5 text-[10px] text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
                    >
                      @{cat}
                    </span>
                  ))}
                  <span className="text-[10px] text-gray-400">{entry.createdAt}</span>
                </div>
              </div>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => togglePause(entry.id, entry.status)}
                  className="rounded p-0.5 text-gray-400 hover:text-amber-500"
                  title={entry.status === "paused" ? "继续" : "暂停"}
                >
                  {entry.status === "paused" ? <Play size={12} /> : <Pause size={12} />}
                </button>
                <button
                  onClick={() => remove(entry.id)}
                  className="rounded p-0.5 text-gray-400 hover:text-red-500"
                  title="移除"
                >
                  <X size={12} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 任务 2.2: TokenUsagePanel 真实数据

**Files:**
- Modify: `web/src/components/right-panel/TokenUsagePanel.tsx`
- Create: `src/web/routes/metrics.py`

- [ ] **Step 1: 实现后端 Metrics API**

```python
# src/web/routes/metrics.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

class TokenUsage(BaseModel):
    promptTokens: int
    completionTokens: int
    cacheHitRate: float
    totalCost: float

@router.get("/token-usage")
async def get_token_usage(threadId: str = None):
    """Get token usage for a thread or global."""
    # TODO: Implement real tracking
    return {
        "promptTokens": 45230,
        "completionTokens": 12840,
        "cacheHitRate": 0.72,
        "totalCost": 0.38,
    }
```

- [ ] **Step 2: 重写 TokenUsagePanel**

```typescript
// web/src/components/right-panel/TokenUsagePanel.tsx
import { useState, useEffect } from "react";
import { Zap, Database, Clock } from "lucide-react";

interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  cacheHitRate: number;
  totalCost: number;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function TokenUsagePanel({ threadId }: { threadId: string | null }) {
  const [usage, setUsage] = useState<TokenUsage | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchUsage = async () => {
      setLoading(true);
      try {
        const url = threadId
          ? `${API_BASE}/api/metrics/token-usage?threadId=${threadId}`
          : `${API_BASE}/api/metrics/token-usage`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setUsage(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchUsage();
  }, [threadId]);

  if (loading || !usage) {
    return <div className="text-sm text-gray-400">加载中...</div>;
  }

  const total = usage.promptTokens + usage.completionTokens;
  const promptPct = total > 0 ? (usage.promptTokens / total) * 100 : 0;
  const completionPct = 100 - promptPct;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={<Zap size={14} className="text-blue-500" />}
          label="Prompt"
          value={`${(usage.promptTokens / 1000).toFixed(1)}k`}
        />
        <StatCard
          icon={<Zap size={14} className="text-green-500" />}
          label="Completion"
          value={`${(usage.completionTokens / 1000).toFixed(1)}k`}
        />
        <StatCard
          icon={<Database size={14} className="text-purple-500" />}
          label="缓存命中率"
          value={`${(usage.cacheHitRate * 100).toFixed(0)}%`}
        />
        <StatCard
          icon={<Clock size={14} className="text-amber-500" />}
          label="总费用"
          value={`$${usage.totalCost.toFixed(2)}`}
        />
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">Token 分布</h4>
        <div className="h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div className="flex h-full">
            <div className="bg-blue-500" style={{ width: `${promptPct}%` }} title="Prompt" />
            <div className="bg-green-500" style={{ width: `${completionPct}%` }} title="Completion" />
          </div>
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-gray-400">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-blue-500" />
            Prompt {(usage.promptTokens / 1000).toFixed(1)}k
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
            Completion {(usage.completionTokens / 1000).toFixed(1)}k
          </span>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">缓存命中率</h4>
        <div className="h-3 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div
            className="h-full rounded-full bg-purple-500 transition-all"
            style={{ width: `${usage.cacheHitRate * 100}%` }}
          />
        </div>
        <p className="mt-1 text-[10px] text-gray-400">
          {usage.cacheHitRate > 0.7 ? "缓存效率良好" : "缓存命中率偏低，考虑优化上下文策略"}
        </p>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-2 dark:border-gray-700">
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[10px] text-gray-500 dark:text-gray-400">{label}</span>
      </div>
      <p className="mt-1 text-sm font-semibold text-gray-800 dark:text-gray-200">{value}</p>
    </div>
  );
}
```

---

### 任务 2.3: TaskPanel 真实数据

**Files:**
- Modify: `web/src/components/right-panel/TaskPanel.tsx`
- Create: `src/web/routes/tasks.py`

- [ ] **Step 1: 实现后端 Tasks API**

```python
# src/web/routes/tasks.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal, Optional

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class TaskItem(BaseModel):
    id: str
    title: str
    status: Literal["todo", "doing", "blocked", "done"]
    ownerCat: Optional[str] = None
    description: Optional[str] = None

# Mock data for now
_tasks: list[TaskItem] = [
    {"id": "1", "title": "实现文件上传功能", "status": "done", "ownerCat": "orange"},
    {"id": "2", "title": "添加用户认证模块", "status": "doing", "ownerCat": "inky"},
    {"id": "3", "title": "优化数据库查询性能", "status": "todo", "ownerCat": "patch"},
]

@router.get("/entries")
async def list_tasks(threadId: str = None):
    """Get tasks for a thread."""
    return _tasks

@router.post("/entries/{taskId}/status")
async def update_task_status(taskId: str, status: str):
    for t in _tasks:
        if t.id == taskId:
            t.status = status
            return {"success": True}
    return {"success": False}
```

- [ ] **Step 2: 重写 TaskPanel 使用真实 API**

```typescript
// web/src/components/right-panel/TaskPanel.tsx
import { useState, useEffect } from "react";
import { CheckCircle2, Circle, AlertTriangle } from "lucide-react";

export interface TaskItem {
  id: string;
  title: string;
  status: "todo" | "doing" | "blocked" | "done";
  ownerCat?: string;
  description?: string;
}

const STATUS_CONFIG = {
  todo: { icon: Circle, color: "text-gray-400", label: "待办" },
  doing: { icon: Circle, color: "text-blue-500", label: "进行中" },
  blocked: { icon: AlertTriangle, color: "text-amber-500", label: "阻塞" },
  done: { icon: CheckCircle2, color: "text-green-500", label: "完成" },
};

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function TaskPanel({ threadId }: { threadId: string | null }) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const url = threadId
        ? `${API_BASE}/api/tasks/entries?threadId=${threadId}`
        : `${API_BASE}/api/tasks/entries`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [threadId]);

  const groups = {
    doing: tasks.filter((t) => t.status === "doing"),
    todo: tasks.filter((t) => t.status === "todo"),
    blocked: tasks.filter((t) => t.status === "blocked"),
    done: tasks.filter((t) => t.status === "done"),
  };

  if (loading) {
    return <div className="text-sm text-gray-400">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">任务进度</h4>
        <span className="text-xs text-gray-400">
          {groups.done.length}/{tasks.length} 完成
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full rounded-full bg-green-500 transition-all"
          style={{ width: `${tasks.length > 0 ? (groups.done.length / tasks.length) * 100 : 0}%` }}
        />
      </div>

      {(Object.entries(groups) as [keyof typeof groups, TaskItem[]][]).map(([status, items]) => {
        if (items.length === 0) return null;
        const cfg = STATUS_CONFIG[status];
        const Icon = cfg.icon;
        return (
          <div key={status}>
            <div className="mb-1 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Icon size={12} className={cfg.color} />
              <span>{cfg.label} ({items.length})</span>
            </div>
            <div className="space-y-1 pl-4">
              {items.map((task) => (
                <div
                  key={task.id}
                  className="flex items-start gap-2 rounded border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/50"
                >
                  <Icon size={14} className={`mt-0.5 shrink-0 ${cfg.color}`} />
                  <div className="min-w-0 flex-1">
                    <p className={`text-xs ${task.status === "done" ? "text-gray-400 line-through" : "text-gray-700 dark:text-gray-300"}`}>
                      {task.title}
                    </p>
                    {task.description && <p className="text-[10px] text-gray-400">{task.description}</p>}
                    {task.ownerCat && (
                      <span className="mt-0.5 inline-block rounded bg-gray-200 px-1 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                        {task.ownerCat}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

---

## Phase 3: 其他 Mock 数据面板 (P2)

### 任务 3.1: AuditPanel 真实数据

**Files:**
- Modify: `web/src/components/audit/AuditPanel.tsx`
- Create: `src/invocation/audit.py`
- Create: `src/web/routes/audit.py`

- [ ] **Step 1: 实现 AuditLog API**

```python
# src/invocation/audit.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import json
from pathlib import Path

@dataclass
class AuditEntry:
    id: str
    timestamp: str
    level: Literal["info", "warning", "error", "critical"]
    category: Literal["file", "command", "network", "auth", "system"]
    actor: str
    action: str
    details: str
    threadId: str = ""

class AuditLog:
    def __init__(self, log_dir: str = ".claude/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entry: AuditEntry):
        date = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{date}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps({
                "id": entry.id,
                "timestamp": entry.timestamp,
                "level": entry.level,
                "category": entry.category,
                "actor": entry.actor,
                "action": entry.action,
                "details": entry.details,
                "threadId": entry.threadId,
            }) + "\n")

    def query(self, limit: int = 100, **filters) -> list[AuditEntry]:
        entries = []
        for log_file in sorted(self.log_dir.glob("*.jsonl"), reverse=True):
            with open(log_file) as f:
                for line in f:
                    if len(entries) >= limit:
                        break
                    data = json.loads(line)
                    # Apply filters
                    if all(data.get(k) == v for k, v in filters.items()):
                        entries.append(AuditEntry(**data))
        return entries[:limit]
```

- [ ] **Step 2: 实现 API 路由**

```python
# src/web/routes/audit.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

router = APIRouter(prefix="/api/audit", tags=["audit"])

class AuditEntry(BaseModel):
    id: str
    timestamp: str
    level: Literal["info", "warning", "error", "critical"]
    category: Literal["file", "command", "network", "auth", "system"]
    actor: str
    action: str
    details: str
    threadId: str = ""

# Mock entries for demo
_mock_entries = [
    {"id": "1", "timestamp": "14:32:10", "level": "info", "category": "file", "actor": "orange", "action": "read_file", "details": "读取了 src/config.ts"},
    {"id": "2", "timestamp": "14:31:45", "level": "warning", "category": "command", "actor": "inky", "action": "execute_command", "details": "执行了 npm install (耗时 12s)"},
]

@router.get("/entries")
async def list_entries(
    category: str = None,
    level: str = None,
    limit: int = 100,
):
    entries = _mock_entries
    if category:
        entries = [e for e in entries if e["category"] == category]
    if level:
        entries = [e for e in entries if e["level"] == level]
    return entries[:limit]
```

- [ ] **Step 3: 重写 AuditPanel**

```typescript
// web/src/components/audit/AuditPanel.tsx
import { useState, useEffect } from "react";
import { Shield, AlertTriangle, FileText, Terminal, Filter } from "lucide-react";

interface AuditEntry {
  id: string;
  timestamp: string;
  level: "info" | "warning" | "error" | "critical";
  category: "file" | "command" | "network" | "auth" | "system";
  actor: string;
  action: string;
  details: string;
  threadId?: string;
}

const LEVEL_COLORS = {
  info: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  critical: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 animate-pulse",
};

const CATEGORY_ICONS = {
  file: FileText,
  command: Terminal,
  network: Shield,
  auth: Shield,
  system: AlertTriangle,
};

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function AuditPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState<"all" | AuditEntry["category"]>("all");
  const [levelFilter, setLevelFilter] = useState<"all" | AuditEntry["level"]>("all");
  const [loading, setLoading] = useState(false);

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filter !== "all") params.set("category", filter);
      if (levelFilter !== "all") params.set("level", levelFilter);
      const res = await fetch(`${API_BASE}/api/audit/entries?${params}`);
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 10000);
    return () => clearInterval(interval);
  }, [filter, levelFilter]);

  if (loading && entries.length === 0) {
    return <div className="p-4 text-sm text-gray-400">加载中...</div>;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-gray-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="rounded border border-gray-200 px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="all">全部类别</option>
            <option value="file">文件</option>
            <option value="command">命令</option>
            <option value="network">网络</option>
            <option value="auth">认证</option>
            <option value="system">系统</option>
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value as any)}
            className="rounded border border-gray-200 px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-700"
          >
            <option value="all">全部级别</option>
            <option value="info">信息</option>
            <option value="warning">警告</option>
            <option value="error">错误</option>
            <option value="critical">严重</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {entries.map((entry) => {
          const Icon = CATEGORY_ICONS[entry.category];
          return (
            <div key={entry.id} className="mb-2 rounded-lg border border-gray-200 bg-white p-2 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-start gap-2">
                <Icon size={14} className="mt-0.5 text-gray-400" />
                <div className="flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${LEVEL_COLORS[entry.level]}`}>
                      {entry.level.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-gray-400">{entry.timestamp}</span>
                    <span className="rounded bg-gray-100 px-1 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700">
                      @{entry.actor}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-700 dark:text-gray-300">
                    <span className="font-mono text-gray-500">{entry.action}</span>
                    <span className="mx-1 text-gray-300">·</span>
                    {entry.details}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

### 任务 3.2: 设置面板 Metrics (QuotaBoard, LeaderboardTab)

**Files:**
- Modify: `web/src/components/settings/QuotaBoard.tsx`
- Modify: `web/src/components/settings/LeaderboardTab.tsx`
- Create: `src/web/routes/metrics.py` (扩展)

- [ ] **Step 1: 扩展 Metrics API**

```python
# Add to src/web/routes/metrics.py

@router.get("/cats")
async def get_cat_metrics():
    """Get per-cat metrics."""
    return [
        {"catId": "orange", "totalInvocations": 142, "successRate": 0.97, "avgLatencyMs": 2300, "totalTokens": 520000, "trend": "up"},
        {"catId": "inky", "totalInvocations": 98, "successRate": 0.95, "avgLatencyMs": 1800, "totalTokens": 380000, "trend": "stable"},
    ]

@router.get("/leaderboard")
async def get_leaderboard():
    """Get leaderboard data."""
    return [
        {"catId": "orange", "rank": 1, "score": 96.4, "totalInvocations": 142, "successRate": 0.97, "avgLatencyMs": 2300, "badge": "gold"},
        {"catId": "tabby", "rank": 2, "score": 94.8, "totalInvocations": 45, "successRate": 0.98, "avgLatencyMs": 1500, "badge": "silver"},
    ]
```

- [ ] **Step 2: 重写 QuotaBoard**

```typescript
// web/src/components/settings/QuotaBoard.tsx
import { useState, useEffect } from "react";
import { useCatStore } from "../../stores/catStore";
import { TrendingUp, TrendingDown, Minus, Zap, Clock, MessageSquare, CheckCircle2 } from "lucide-react";

interface CatMetrics {
  catId: string;
  totalInvocations: number;
  successRate: number;
  avgLatencyMs: number;
  totalTokens: number;
  trend: "up" | "down" | "stable";
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp size={14} className="text-green-500" />;
  if (trend === "down") return <TrendingDown size={14} className="text-red-500" />;
  return <Minus size={14} className="text-gray-400" />;
};

export function QuotaBoard() {
  const cats = useCatStore((s) => s.cats);
  const [metrics, setMetrics] = useState<CatMetrics[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/metrics/cats`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-4 text-gray-400">加载中...</div>;
  }

  const totalTokens = metrics.reduce((sum, m) => sum + m.totalTokens, 0);
  const totalInvocations = metrics.reduce((sum, m) => sum + m.totalInvocations, 0);
  const avgSuccessRate = metrics.length > 0
    ? metrics.reduce((sum, m) => sum + m.successRate, 0) / metrics.length
    : 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <Zap size={18} className="text-blue-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{(totalTokens / 1000000).toFixed(1)}M</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">总 Token 消耗</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <MessageSquare size={18} className="text-green-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{totalInvocations}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">总调用次数</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <CheckCircle2 size={18} className="text-purple-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{(avgSuccessRate * 100).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">平均成功率</p>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">按猫咪分布</h4>
        <div className="space-y-2">
          {metrics.map((metric) => {
            const cat = cats.find((c) => c.id === metric.catId);
            return (
              <div key={metric.catId} className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                <span className="w-20 text-sm font-medium text-gray-800 dark:text-gray-200">{cat?.displayName || metric.catId}</span>
                <div className="flex flex-1 items-center gap-4 text-xs">
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <Zap size={10} /> {(metric.totalTokens / 1000).toFixed(0)}k tokens
                  </span>
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <MessageSquare size={10} /> {metric.totalInvocations} 次
                  </span>
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <Clock size={10} /> {metric.avgLatencyMs}ms
                  </span>
                  <span className={`font-medium ${metric.successRate > 0.95 ? "text-green-600" : "text-amber-600"}`}>
                    {(metric.successRate * 100).toFixed(0)}%
                  </span>
                  <TrendIcon trend={metric.trend} />
                </div>
                <div className="w-24">
                  <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${(metric.totalTokens / totalTokens) * 100}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
```

---

### 任务 3.3: HistorySearchModal 真实搜索

**Files:**
- Modify: `web/src/components/chat/HistorySearchModal.tsx`

- [ ] **Step 1: 更新组件使用真实 API**

```typescript
// web/src/components/chat/HistorySearchModal.tsx
import { useState, useRef, useEffect } from "react";
import { Search, Clock, MessageSquare, ArrowRight, Loader2 } from "lucide-react";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SearchResult {
  id: string;
  threadName: string;
  content: string;
  role: "user" | "assistant";
  timestamp: string;
  catId?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function HistorySearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    const search = async () => {
      if (!query.trim()) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/messages/search?q=${encodeURIComponent(query)}&limit=20`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results.map((r: any) => ({
            id: r.messageId,
            threadName: r.threadId.slice(0, 8),
            content: r.content,
            role: "assistant",
            timestamp: r.timestamp,
          })));
        }
      } finally {
        setLoading(false);
      }
    };

    const timeout = setTimeout(search, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  if (!isOpen) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-20" onClick={onClose}>
      <div className="w-full max-w-xl rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-800" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          {loading ? <Loader2 size={18} className="animate-spin text-gray-400" /> : <Search size={18} className="text-gray-400" />}
          <input
            ref={inputRef}
            className="flex-1 bg-transparent text-sm text-gray-800 outline-none placeholder:text-gray-400 dark:text-gray-200"
            placeholder="搜索对话历史..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="rounded border border-gray-200 px-1.5 py-0.5 text-[10px] text-gray-400 dark:border-gray-600">ESC</kbd>
        </div>

        <div className="max-h-80 overflow-y-auto">
          {query ? (
            results.length > 0 ? (
              results.map((result) => (
                <button
                  key={result.id}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  onClick={onClose}
                >
                  <div className="mt-0.5 shrink-0">
                    {result.role === "user" ? (
                      <MessageSquare size={14} className="text-blue-500" />
                    ) : (
                      <MessageSquare size={14} className="text-green-500" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-800 dark:text-gray-200">{result.threadName}</span>
                      {result.catId && (
                        <span className="rounded bg-purple-50 px-1 py-0.5 text-[10px] text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
                          @{result.catId}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-xs text-gray-600 dark:text-gray-400">{result.content}</p>
                    <span className="mt-0.5 flex items-center gap-1 text-[10px] text-gray-400">
                      <Clock size={10} /> {result.timestamp}
                    </span>
                  </div>
                  <ArrowRight size={14} className="shrink-0 text-gray-300" />
                </button>
              ))
            ) : (
              <div className="px-4 py-8 text-center text-sm text-gray-400">
                {loading ? "搜索中..." : "无结果"}
              </div>
            )
          ) : (
            <div className="px-4 py-8 text-center text-sm text-gray-400">
              输入关键词搜索对话历史
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 px-4 py-2 text-[10px] text-gray-400 dark:border-gray-700">
          <kbd className="rounded border border-gray-200 px-1 dark:border-gray-600">Ctrl+K</kbd> 快速搜索
        </div>
      </div>
    </div>
  );
}
```

---

### 任务 3.4: SignalInboxPage 和 MissionHubPage (P3 - 复杂系统)

这两个组件涉及完整的 Signal 系统和 Mission 系统，需要独立设计和实现。

**建议:**
1. Signal 系统 → Phase 4 (需要独立的 RSS 抓取、文章存储、学习模式等)
2. Mission 系统 → Phase 5 (需要任务依赖图、里程碑、风险评估等)

当前可以先简化：
- SignalInboxPage: 保持 mock，添加 "开发中" 提示
- MissionHubPage: 保持 mock，添加 "开发中" 提示

---

## 实施顺序总结

```
Phase 1: Workspace 文件系统 (P0)
  ├── 1.1 Thread model + projectPath
  ├── 1.2 WorktreeManager
  ├── 1.3 Workspace API 路由
  ├── 1.4 useWorkspace hook
  └── 1.5 重写 WorkspacePanel

Phase 2: 核心面板 (P1)
  ├── 2.1 QueuePanel + API
  ├── 2.2 TokenUsagePanel + API
  └── 2.3 TaskPanel + API

Phase 3: 其他面板 (P2)
  ├── 3.1 AuditPanel + API
  ├── 3.2 QuotaBoard + Leaderboard + API
  ├── 3.3 HistorySearchModal 真实搜索
  └── 3.4 Signal/Mission (保持 mock，后续独立实现)
```

---

## 验证清单

每个任务完成后验证：
- [ ] TypeScript 编译通过 (`npx tsc --noEmit`)
- [ ] 后端 API 测试通过 (`pytest tests/...`)
- [ ] 前端功能在浏览器中正常工作
- [ ] Mock 数据已完全移除

项目整体完成后验证：
- [ ] `grep -r "MOCK_" web/src/` 返回空
- [ ] `grep -r "mockData" web/src/` 返回空
- [ ] Workspace 文件树可以浏览真实文件
- [ ] 所有面板显示来自后端的数据
