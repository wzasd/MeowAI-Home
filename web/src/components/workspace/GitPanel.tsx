/** Workspace Git Panel — status and diff viewer. */

import { useEffect, useState, useCallback } from "react";
import { GitBranch, RefreshCw, Loader2, FilePlus, FileMinus, FileEdit, GitCommit } from "lucide-react";
import type { GitStatus } from "../../hooks/useWorkspace";

interface GitPanelProps {
  gitStatus: () => Promise<GitStatus | null>;
  gitDiff: (path?: string) => Promise<string>;
}

function statusIcon(status: string) {
  if (status.includes("M")) return <FileEdit size={12} className="text-amber-500" />;
  if (status.includes("A")) return <FilePlus size={12} className="text-green-500" />;
  if (status.includes("D")) return <FileMinus size={12} className="text-red-500" />;
  if (status.includes("?")) return <FilePlus size={12} className="text-blue-500" />;
  return <GitCommit size={12} className="text-gray-400" />;
}

export function GitPanel({ gitStatus, gitDiff }: GitPanelProps) {
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [diff, setDiff] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [diffLoading, setDiffLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Load git status on mount — use separate flag to avoid effect-setState lint
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const s = await gitStatus();
      if (!cancelled) {
        setStatus(s);
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    const s = await gitStatus();
    setStatus(s);
    setLoading(false);
  }, [gitStatus]);

  const loadDiff = useCallback(
    async (path?: string) => {
      setDiffLoading(true);
      const d = await gitDiff(path);
      setDiff(d);
      setDiffLoading(false);
    },
    [gitDiff]
  );

  const handleFileClick = (path: string) => {
    setSelectedFile(path);
    loadDiff(path);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-gray-700 px-3 py-2">
        <div className="flex items-center gap-2 text-xs text-gray-300">
          <GitBranch size={14} className="text-purple-400" />
          <span className="font-medium">{status?.branch || "—"}</span>
          {status && !status.clean && (
            <span className="rounded bg-amber-900/30 px-1.5 py-0.5 text-[10px] text-amber-400">
              {status.files.length} 更改
            </span>
          )}
          {status && status.clean && (
            <span className="rounded bg-green-900/30 px-1.5 py-0.5 text-[10px] text-green-400">
              干净
            </span>
          )}
          {status && status.ahead > 0 && (
            <span className="text-[10px] text-gray-400">↑{status.ahead}</span>
          )}
          {status && status.behind > 0 && (
            <span className="text-[10px] text-gray-400">↓{status.behind}</span>
          )}
        </div>
        <button
          onClick={loadStatus}
          disabled={loading}
          className="rounded p-1 text-gray-400 hover:text-gray-200 disabled:opacity-50"
        >
          {loading ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* File list */}
        <div className="w-48 shrink-0 overflow-y-auto border-r border-gray-700 bg-gray-900/50">
          {status?.files.length === 0 && (
            <div className="px-3 py-4 text-center text-[10px] text-gray-500">
              工作区干净
            </div>
          )}
          {status?.files.map((f) => (
            <button
              key={f.path}
              onClick={() => handleFileClick(f.path)}
              className={`flex w-full items-center gap-1.5 px-2 py-1 text-left text-[10px] hover:bg-gray-800 ${
                selectedFile === f.path ? "bg-gray-800 text-blue-400" : "text-gray-300"
              }`}
            >
              {statusIcon(f.status)}
              <span className="truncate">{f.path}</span>
            </button>
          ))}
        </div>

        {/* Diff viewer */}
        <div className="flex flex-1 flex-col overflow-hidden bg-gray-900">
          <div className="flex items-center justify-between border-b border-gray-700 px-3 py-1">
            <span className="text-[10px] text-gray-400">
              {selectedFile || "全局 diff"}
            </span>
            {!selectedFile && (
              <button
                onClick={() => loadDiff()}
                disabled={diffLoading}
                className="text-[10px] text-gray-400 hover:text-gray-200 disabled:opacity-50"
              >
                {diffLoading ? "加载中..." : "刷新"}
              </button>
            )}
          </div>
          <div className="flex-1 overflow-auto p-2 font-mono text-[10px] leading-relaxed text-gray-300">
            {diffLoading ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 size={16} className="animate-spin text-gray-500" />
              </div>
            ) : diff ? (
              <pre className="whitespace-pre-wrap">
                {diff.split("\n").map((line, i) => {
                  let color = "text-gray-300";
                  if (line.startsWith("+")) color = "text-green-400";
                  else if (line.startsWith("-")) color = "text-red-400";
                  else if (line.startsWith("@@")) color = "text-blue-400";
                  else if (line.startsWith("diff ")) color = "text-purple-400";
                  else if (line.startsWith("index ")) color = "text-gray-500";
                  return (
                    <div key={i} className={color}>
                      {line || " "}
                    </div>
                  );
                })}
              </pre>
            ) : (
              <div className="flex h-full items-center justify-center text-gray-500">
                选择文件查看 diff
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
