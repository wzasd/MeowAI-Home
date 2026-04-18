/** GovernanceSettings — external project governance health panel with SQLite-backed CRUD. */

import { useState, useEffect, useCallback } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Loader2,
  Plus,
  Trash2,
  RefreshCw,
  Zap,
} from "lucide-react";
import { api } from "../../api/client";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import {
  buildGovernanceSummaryCards,
  type GovernanceProjectSnapshot,
} from "./settingsSummaryModels";

interface GovernanceFinding {
  rule: string;
  severity: string;
  message: string;
}

interface GovernanceProject extends GovernanceProjectSnapshot {
  project_path: string;
  status: "healthy" | "stale" | "missing" | "never-synced" | "error";
  pack_version: string | null;
  last_synced_at: string | null;
  findings: GovernanceFinding[];
  confirmed: boolean;
}

const STATUS_STYLES: Record<
  string,
  { icon: typeof CheckCircle2; bg: string; text: string; label: string }
> = {
  healthy: {
    icon: CheckCircle2,
    bg: "bg-green-50 dark:bg-green-900/20",
    text: "text-green-700 dark:text-green-400",
    label: "正常",
  },
  stale: {
    icon: AlertTriangle,
    bg: "bg-yellow-50 dark:bg-yellow-900/20",
    text: "text-yellow-700 dark:text-yellow-400",
    label: "过期",
  },
  missing: {
    icon: XCircle,
    bg: "bg-red-50 dark:bg-red-900/20",
    text: "text-red-700 dark:text-red-400",
    label: "缺失",
  },
  error: {
    icon: XCircle,
    bg: "bg-red-50 dark:bg-red-900/20",
    text: "text-red-700 dark:text-red-400",
    label: "错误",
  },
  "never-synced": {
    icon: HelpCircle,
    bg: "bg-gray-50 dark:bg-gray-700/50",
    text: "text-gray-600 dark:text-gray-400",
    label: "未同步",
  },
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function GovernanceSettings() {
  const [projects, setProjects] = useState<GovernanceProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newPath, setNewPath] = useState("");

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.governance.listProjects();
      setProjects(data.projects ?? []);
    } catch (error) {
      setError(getErrorMessage(error, "加载治理状态失败"));
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
    } catch (error) {
      setError(getErrorMessage(error, "激活失败"));
    } finally {
      setConfirming(null);
    }
  };

  const handleSync = async (projectPath: string) => {
    setSyncing(projectPath);
    try {
      await api.governance.syncProject(projectPath);
      await fetchProjects();
    } catch (error) {
      setError(getErrorMessage(error, "同步失败"));
    } finally {
      setSyncing(null);
    }
  };

  const handleAdd = async () => {
    if (!newPath.trim()) return;
    setAdding(true);
    try {
      await api.governance.addProject({
        project_path: newPath.trim(),
        status: "never-synced",
        findings: [],
        confirmed: false,
      });
      setNewPath("");
      await fetchProjects();
    } catch (error) {
      setError(getErrorMessage(error, "添加失败"));
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (projectPath: string) => {
    if (!confirm(`确定删除项目 ${projectPath} 的治理记录？`)) return;
    try {
      await api.governance.deleteProject(projectPath);
      await fetchProjects();
    } catch (error) {
      setError(getErrorMessage(error, "删除失败"));
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

  const summaryCards = buildGovernanceSummaryCards(projects);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Governance Track"
        title="治理项目状态"
        description="先看治理基线，再决定当前要激活、同步还是处理异常。Phase 1 先把项目清单和风险显式摆在一个 section 里。"
        actions={
          <button
            type="button"
            onClick={fetchProjects}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新项目
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]">
            <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
              新增治理项目
            </div>
            <div className="flex flex-col gap-2 lg:flex-row">
              <input
                type="text"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                placeholder="输入项目路径，如 /Users/name/projects/demo"
                className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
              <button
                type="button"
                onClick={handleAdd}
                disabled={adding || !newPath.trim()}
                className="inline-flex items-center justify-center gap-1 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                <Plus size={14} />
                新增记录
              </button>
            </div>
          </div>

          {projects.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">暂无外部项目治理记录</p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                先把需要跟踪的项目接进来，再决定哪些要激活、哪些要同步、哪些异常需要优先处理。
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-[1.2rem] border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left dark:bg-gray-800">
                  <tr>
                    <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                      项目路径
                    </th>
                    <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">状态</th>
                    <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">
                      上次同步
                    </th>
                    <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {projects.map((p) => {
                    const style = STATUS_STYLES[p.status] || STATUS_STYLES["never-synced"]!;
                    const StatusIcon = style.icon;
                    const shortPath = p.project_path.split(/[/\\]/).slice(-2).join("/");
                    const syncDate = p.last_synced_at
                      ? new Date(p.last_synced_at).toLocaleDateString("zh-CN")
                      : "—";
                    const isConfirming = confirming === p.project_path;
                    const isSyncing = syncing === p.project_path;

                    return (
                      <tr key={p.project_path} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-3 py-2 align-top">
                          <div
                            className="font-mono text-xs text-gray-700 dark:text-gray-300"
                            title={p.project_path}
                          >
                            {shortPath}
                          </div>
                          {!p.confirmed && (
                            <div className="mt-1 inline-flex items-center gap-1 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-300">
                              未激活
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <span
                            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}
                          >
                            <StatusIcon size={12} />
                            {style.label}
                          </span>
                          {p.findings.length > 0 && (
                            <div className="mt-1 max-w-xs space-y-0.5">
                              {p.findings.map((f, i) => (
                                <div
                                  key={i}
                                  className={[
                                    "text-[10px]",
                                    f.severity === "error" ? "text-red-600 dark:text-red-400" : "",
                                    f.severity === "warning"
                                      ? "text-amber-600 dark:text-amber-400"
                                      : "",
                                    f.severity === "info" ? "text-gray-500 dark:text-gray-400" : "",
                                  ].join(" ")}
                                >
                                  {f.severity === "error"
                                    ? "●"
                                    : f.severity === "warning"
                                      ? "●"
                                      : "○"}{" "}
                                  {f.message}
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top text-xs text-gray-500 dark:text-gray-400">
                          {syncDate}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <div className="flex items-center gap-2">
                            {!p.confirmed ? (
                              <button
                                type="button"
                                onClick={() => handleConfirm(p.project_path)}
                                disabled={isConfirming}
                                className="flex items-center gap-1 rounded bg-emerald-500 px-2 py-1 text-xs text-white hover:bg-emerald-600 disabled:opacity-50"
                              >
                                {isConfirming ? (
                                  <Loader2 size={12} className="animate-spin" />
                                ) : (
                                  <Zap size={12} />
                                )}
                                {isConfirming ? "激活中..." : "激活"}
                              </button>
                            ) : (
                              <button
                                type="button"
                                onClick={() => handleSync(p.project_path)}
                                disabled={isSyncing}
                                className="flex items-center gap-1 rounded bg-blue-500 px-2 py-1 text-xs text-white hover:bg-blue-600 disabled:opacity-50"
                              >
                                {isSyncing ? (
                                  <Loader2 size={12} className="animate-spin" />
                                ) : (
                                  <RefreshCw size={12} />
                                )}
                                {isSyncing ? "同步中..." : "同步"}
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
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
