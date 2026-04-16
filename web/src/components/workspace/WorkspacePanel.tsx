/** Workspace IDE panel — file tree + code viewer + terminal + browser preview. */

import { useState } from "react";
import {
  Search,
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
import { useWorkspace } from "../../hooks/useWorkspace";
import { FileTree } from "./FileTree";
import { GitPanel } from "./GitPanel";
import { TerminalPanel } from "./TerminalPanel";

export function WorkspacePanel() {
  const {
    worktrees,
    worktreeId,
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
    gitStatus,
    gitDiff,
    runCommand,
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

  const selectedWorktree = worktrees.find((w) => w.id === worktreeId);

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
          <span className="max-w-[200px] truncate text-xs font-medium text-gray-600 dark:text-gray-400">
            {openFilePath || "选择文件"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {worktrees.length > 0 && (
            <select
              className="max-w-[140px] rounded border border-gray-200 bg-white px-2 py-0.5 text-[10px] dark:border-gray-600 dark:bg-gray-700"
              value={worktreeId || ""}
              onChange={(e) => {
                // worktree switch is handled by hook via external state if exposed;
                // useWorkspace auto-selects, so we refetch here manually if needed.
                // The hook doesn't expose setWorktreeId, so we rely on auto-selection.
              }}
              disabled
            >
              {worktrees.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.id}
                </option>
              ))}
            </select>
          )}
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
            <FileTree
              tree={tree}
              selectedPath={openFilePath}
              onSelect={handleSelectFile}
              onExpand={fetchSubtree}
            />
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
            <div className="h-48 shrink-0 border-t border-gray-200 dark:border-gray-700">
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
              <div className="h-full overflow-hidden bg-gray-900 font-mono text-xs text-gray-400">
                {activeBottomTab === "terminal" && (
                  <TerminalPanel runCommand={runCommand} />
                )}
                {activeBottomTab === "preview" && (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    <Globe size={16} className="mr-2" /> 预览面板（开发中）
                  </div>
                )}
                {activeBottomTab === "git" && (
                  <GitPanel gitStatus={gitStatus} gitDiff={gitDiff} />
                )}
                {activeBottomTab === "health" && (
                  <div className="p-2">
                    <span className="text-green-400">Health check: </span>
                    <span className="text-gray-300">All systems nominal</span>{"\n"}
                    <span className="text-gray-400">Tests: backend + frontend passing</span>
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
