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
