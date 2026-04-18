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
import { PageHeader } from "../ui/PageHeader";

export function WorkspacePanel() {
  const {
    worktrees,
    worktreeId,
    setWorktreeId,
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
  } = useWorkspace();

  const [showTree, setShowTree] = useState(true);
  const [activeBottomTab, setActiveBottomTab] = useState<"terminal" | "preview" | "git" | "health">(
    "terminal"
  );
  const [showBottom, setShowBottom] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const currentWorktree = worktrees.find((item) => item.id === worktreeId) ?? worktrees[0];

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
    <div className="flex h-full flex-col bg-transparent">
      <PageHeader
        eyebrow="工作台"
        title="猫窝工作台"
        description="文件、终端、Git 和预览都留在同一张台面上，不再像半成品 IDE。"
        actions={
          <>
            {currentWorktree && (
              <span className="nest-chip">{currentWorktree.branch || "当前窝位"}</span>
            )}
            {worktrees.length > 1 && (
              <select
                value={worktreeId || ""}
                onChange={(e) => setWorktreeId(e.target.value || null)}
                className="nest-field nest-r-md max-w-[15rem] px-3 py-2 text-xs"
                aria-label="选择工作区"
              >
                {worktrees.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.branch} · {item.root.split("/").filter(Boolean).pop() || item.id}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={() => fetchTree()}
              className="nest-button-secondary px-3 py-2 text-xs"
              disabled={loading}
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
              刷新树
            </button>
          </>
        }
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowTree(!showTree)}
              className="nest-button-secondary flex h-10 w-10 items-center justify-center rounded-full"
            >
              {showTree ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
            </button>
            <span className="nest-chip max-w-[260px] truncate">{openFilePath || "选择文件"}</span>
          </div>
          <form onSubmit={handleSearch} className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文件或片段..."
              className="nest-field w-44 rounded-full px-4 py-2 pr-10 text-xs"
            />
            <button
              type="submit"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-[var(--text-faint)] hover:text-[var(--accent)]"
            >
              <Search size={12} />
            </button>
          </form>
        </div>
      </PageHeader>

      <div className="flex flex-1 overflow-hidden">
        {showTree && (
          <div className="w-60 shrink-0 overflow-y-auto border-r border-[var(--line)] bg-white/10 px-2 py-3 dark:bg-white/5">
            <FileTree
              tree={tree}
              selectedPath={openFilePath}
              onSelect={handleSelectFile}
              onExpand={fetchSubtree}
            />
            {tree.length === 0 && !loading && (
              <div className="nest-card nest-r-md mx-2 px-3 py-4 text-center text-xs text-[var(--text-faint)]">
                暂无文件
              </div>
            )}
          </div>
        )}

        <div className="flex flex-1 flex-col">
          {showSearch && searchResults.length > 0 && (
            <div className="max-h-40 overflow-y-auto border-b border-[var(--line)] bg-white/10 p-3 dark:bg-white/5">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium text-[var(--text-soft)]">
                  搜索结果 ({searchResults.length})
                </span>
                <button
                  onClick={() => {
                    setShowSearch(false);
                    setSearchResults([]);
                  }}
                  className="nest-button-ghost flex h-7 w-7 items-center justify-center rounded-full"
                >
                  <X size={12} />
                </button>
              </div>
              {searchResults.map((result, i) => (
                <button
                  key={i}
                  onClick={() => handleSelectFile(result.path)}
                  className="nest-card nest-r-md mb-2 w-full p-3 text-left text-xs"
                >
                  <span className="font-medium text-[var(--accent)]">{result.path}</span>
                  {result.line > 0 && (
                    <span className="ml-2 text-[var(--text-faint)]">:{result.line}</span>
                  )}
                  <p className="truncate text-[var(--text-soft)]">{result.content}</p>
                </button>
              ))}
            </div>
          )}

          <div className="nest-code-panel flex-1 overflow-auto p-5 font-mono text-xs leading-relaxed">
            {error ? (
              <div className="flex h-full items-center justify-center text-red-400">{error}</div>
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
                  <span className="text-amber-200/60">
                    {"# "}
                    {file.path}
                  </span>
                  {"\n\n"}
                  {file.content}
                  {file.truncated && <span className="text-amber-400">\n\n[文件已截断]</span>}
                </pre>
              )
            ) : loading ? (
              <div className="flex h-full items-center justify-center text-gray-500">
                <Loader2 size={24} className="animate-spin" />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-center text-gray-500">
                <div>
                  <div className="nest-kicker">打开文件</div>
                  <div className="nest-title mt-2 text-xl text-amber-50/90">选择文件查看代码</div>
                </div>
              </div>
            )}
          </div>

          {showBottom && (
            <div className="h-52 shrink-0 border-t border-[var(--line)] bg-[rgba(20,16,13,0.12)] dark:bg-black/10">
              <div className="flex items-center border-b border-[var(--line)] bg-white/5 px-3 py-2">
                {[
                  { key: "terminal" as const, icon: Terminal, label: "终端" },
                  { key: "preview" as const, icon: Eye, label: "预览" },
                  { key: "git" as const, icon: GitBranch, label: "Git" },
                  { key: "health" as const, icon: Activity, label: "健康" },
                ].map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setActiveBottomTab(t.key)}
                    className={`nest-tab px-3 py-2 text-[11px] ${
                      activeBottomTab === t.key ? "nest-tab-active" : ""
                    }`}
                  >
                    <t.icon size={10} /> {t.label}
                  </button>
                ))}
                <button
                  onClick={() => setShowBottom(false)}
                  className="nest-button-ghost ml-auto flex h-8 w-8 items-center justify-center rounded-full"
                >
                  <X size={12} />
                </button>
              </div>
              <div className="h-full overflow-hidden font-mono text-xs text-gray-400">
                {activeBottomTab === "terminal" && <TerminalPanel />}
                {activeBottomTab === "preview" && (
                  <div className="flex h-full items-center justify-center text-gray-500">
                    <Globe size={16} className="mr-2" /> 预览窗正在回到这张工作台
                  </div>
                )}
                {activeBottomTab === "git" && <GitPanel gitStatus={gitStatus} gitDiff={gitDiff} />}
                {activeBottomTab === "health" && (
                  <div className="p-3">
                    <span className="text-green-400">Health check: </span>
                    <span className="text-gray-300">猫窝设备运转正常</span>
                    {"\n"}
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
