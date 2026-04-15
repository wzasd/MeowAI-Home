"use client";

import { useCallback, useEffect, useState } from "react";
import { useThreadStore } from "../stores/threadStore";
import { api } from "../api/client";
import type {
  WorktreeEntry,
  TreeNode,
  FileData,
  SearchResult,
  GitStatus,
  TerminalResult,
} from "../api/client";

export type {
  WorktreeEntry,
  TreeNode,
  FileData,
  SearchResult,
  GitStatusItem,
  GitStatus,
  TerminalResult,
} from "../api/client";

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
      const data = await api.workspace.listWorktrees();
      setWorktrees(data.worktrees ?? []);
      // Auto-select current thread's worktree or first available
      const current = data.worktrees.find((w: WorktreeEntry) => w.id === currentThreadId);
      if (current) {
        setWorktreeId(current.id);
      } else if (data.worktrees.length > 0 && !worktreeId) {
        setWorktreeId(data.worktrees[0].id);
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
        const data = await api.workspace.getTree(worktreeId, subpath, 3);
        setTree(data.tree ?? []);
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
        const data = await api.workspace.getTree(worktreeId, dirPath, 3);
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
        const data = await api.workspace.getFile(worktreeId, path);
        setFile(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load file");
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
        const data = await api.workspace.search(worktreeId, query, type);
        setSearchResults(data.results ?? []);
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
        await api.workspace.reveal(worktreeId, path);
      } catch {
        /* ignore */
      }
    },
    [worktreeId]
  );

  // Git status
  const gitStatus = useCallback(async (): Promise<GitStatus | null> => {
    if (!worktreeId) return null;
    try {
      return await api.workspace.gitStatus(worktreeId);
    } catch {
      return null;
    }
  }, [worktreeId]);

  // Git diff
  const gitDiff = useCallback(async (path?: string): Promise<string> => {
    if (!worktreeId) return "";
    try {
      const data = await api.workspace.gitDiff(worktreeId, path);
      return data.diff || "";
    } catch {
      return "";
    }
  }, [worktreeId]);

  // Terminal command
  const runCommand = useCallback(
    async (command: string): Promise<TerminalResult> => {
      if (!worktreeId) {
        return { stdout: "", stderr: "No worktree selected", returncode: -1 };
      }
      try {
        return await api.workspace.runCommand(worktreeId, command);
      } catch (err) {
        return {
          stdout: "",
          stderr: err instanceof Error ? err.message : "Failed to execute command",
          returncode: -1,
        };
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
    gitStatus,
    gitDiff,
    runCommand,
  };
}
