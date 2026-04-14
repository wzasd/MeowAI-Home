/** GovernanceSettings — external project governance health panel with SQLite-backed CRUD. */

import { useState, useEffect, useCallback } from "react";
import { RefreshCw, CheckCircle2, AlertTriangle, XCircle, HelpCircle, Loader2, Plus, Trash2 } from "lucide-react";
import { api } from "../../api/client";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface GovernanceFinding {
  rule: string;
  severity: string;
  message: string;
}

interface GovernanceProject {
  project_path: string;
  status: "healthy" | "stale" | "missing" | "never-synced";
  pack_version: string | null;
  last_synced_at: string | null;
  findings: GovernanceFinding[];
  confirmed: boolean;
}

const STATUS_STYLES: Record<string, { icon: typeof CheckCircle2; bg: string; text: string; label: string }> = {
  healthy: { icon: CheckCircle2, bg: "bg-green-50 dark:bg-green-900/20", text: "text-green-700 dark:text-green-400", label: "正常" },
  stale: { icon: AlertTriangle, bg: "bg-yellow-50 dark:bg-yellow-900/20", text: "text-yellow-700 dark:text-yellow-400", label: "过期" },
  missing: { icon: XCircle, bg: "bg-red-50 dark:bg-red-900/20", text: "text-red-700 dark:text-red-400", label: "缺失" },
  "never-synced": { icon: HelpCircle, bg: "bg-gray-50 dark:bg-gray-700/50", text: "text-gray-600 dark:text-gray-400", label: "未同步" },
};

export function GovernanceSettings() {
  const [projects, setProjects] = useState<GovernanceProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newPath, setNewPath] = useState("");

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.governance.listProjects();
      setProjects(data.projects ?? []);
    } catch (e: any) {
      setError(e.message || "加载治理状态失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleConfirm = async (projectPath: string) => {
    setConfirming(projectPath);
    try {
      await api.governance.confirmProject(projectPath);
      await fetchProjects();
    } catch (e: any) {
      setError(e.message || "同步失败");
    } finally {
      setConfirming(null);
    }
  };

  const handleAdd = async () => {
    if (!newPath.trim()) return;
    setAdding(true);
    try {
      await api.governance.addProject({
        project_path: newPath.trim(),
        status: "healthy",
        findings: [],
        confirmed: true,
      });
      setNewPath("");
      await fetchProjects();
    } catch (e: any) {
      setError(e.message || "添加失败");
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (projectPath: string) => {
    if (!confirm(`确定删除项目 ${projectPath} 的治理记录？`)) return;
    try {
      await api.governance.deleteProject(projectPath);
      await fetchProjects();
    } catch (e: any) {
      setError(e.message || "删除失败");
    }
  };

  if (loading && projects.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">加载治理状态中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">外部项目治理状态</h3>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchProjects}
            className="text-xs text-blue-500 hover:text-blue-700"
          >
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={newPath}
          onChange={(e) => setNewPath(e.target.value)}
          placeholder="输入项目路径，如 /Users/name/projects/demo"
          className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={adding || !newPath.trim()}
          className="flex items-center gap-1 rounded bg-blue-500 px-3 py-1 text-xs text-white hover:bg-blue-600 disabled:opacity-50"
        >
          <Plus size={14} />
          新增
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="py-8 text-center text-gray-400">
          <p className="text-sm">暂无外部项目治理记录</p>
          <p className="mt-1 text-xs">在上方添加项目以开始治理跟踪</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left dark:bg-gray-800">
              <tr>
                <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">项目路径</th>
                <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">状态</th>
                <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">版本</th>
                <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">上次同步</th>
                <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {projects.map((p) => {
                const style = STATUS_STYLES[p.status] || STATUS_STYLES["never-synced"];
                const StatusIcon = style.icon;
                const shortPath = p.project_path.split(/[/\\]/).slice(-2).join("/");
                const syncDate = p.last_synced_at
                  ? new Date(p.last_synced_at).toLocaleDateString("zh-CN")
                  : "—";

                return (
                  <tr key={p.project_path} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-2 font-mono text-xs text-gray-700 dark:text-gray-300" title={p.project_path}>
                      {shortPath}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
                      >
                        <StatusIcon size={12} />
                        {style.label}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
                      {p.pack_version || "—"}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">{syncDate}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        {(p.status === "stale" || p.status === "never-synced") && (
                          <button
                            type="button"
                            onClick={() => handleConfirm(p.project_path)}
                            disabled={confirming === p.project_path}
                            className="rounded bg-blue-500 px-2 py-1 text-xs text-white hover:bg-blue-600 disabled:opacity-50"
                          >
                            {confirming === p.project_path ? "同步中..." : "立即同步"}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDelete(p.project_path)}
                          className="rounded bg-red-50 px-2 py-1 text-xs text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                      {p.findings.length > 0 && (
                        <div className="mt-1 space-y-0.5">
                          {p.findings.map((f, i) => (
                            <div key={i} className="text-[10px] text-amber-600 dark:text-amber-400">
                              ⚠ {f.message}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
