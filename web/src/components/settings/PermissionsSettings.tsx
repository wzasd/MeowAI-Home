import { useEffect, useState } from "react";
import { Shield, Check, X, Loader2, RefreshCw } from "lucide-react";
import { useCatStore } from "../../stores/catStore";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import {
  buildPermissionSummaryCards,
  type PermissionSummaryDefinition,
} from "./settingsSummaryModels";

interface Permission extends PermissionSummaryDefinition {
  name: string;
  description: string;
}

const PERMISSIONS: Permission[] = [
  {
    id: "write_file",
    name: "写入文件",
    description: "允许创建和修改文件",
    riskLevel: "medium",
  },
  {
    id: "execute_command",
    name: "执行命令",
    description: "允许运行 Shell 命令",
    riskLevel: "high",
  },
  {
    id: "network_access",
    name: "网络访问",
    description: "允许发起 HTTP 请求",
    riskLevel: "medium",
  },
  {
    id: "read_all_threads",
    name: "读取所有线程",
    description: "允许访问其他线程的猫窝内容",
    riskLevel: "low",
  },
  {
    id: "manage_cats",
    name: "管理猫咪",
    description: "允许创建/修改/删除猫咪配置",
    riskLevel: "high",
  },
  {
    id: "send_notification",
    name: "发送通知",
    description: "允许发送推送通知",
    riskLevel: "low",
  },
  {
    id: "access_environment",
    name: "访问环境变量",
    description: "允许读取和修改环境变量",
    riskLevel: "high",
  },
  {
    id: "invoke_other_cats",
    name: "调用其他猫",
    description: "允许通过 A2A 调用其他 Agent",
    riskLevel: "medium",
  },
];

const RISK_COLORS = {
  low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
} as const;

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function PermissionsSettings() {
  const cats = useCatStore((s) => s.cats);
  const updateCat = useCatStore((s) => s.updateCat);
  const fetchCats = useCatStore((s) => s.fetchCats);
  const storeLoading = useCatStore((s) => s.loading);
  const [toggling, setToggling] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cats.length === 0) {
      void fetchCats();
    }
  }, [fetchCats, cats.length]);

  const handleToggle = async (
    catId: string,
    permId: string,
    riskLevel: Permission["riskLevel"]
  ) => {
    const cat = cats.find((entry) => entry.id === catId);
    if (!cat) return;

    const currentPerms = cat.permissions || [];
    const wouldEnable = !currentPerms.includes(permId);

    if (wouldEnable && riskLevel === "high") {
      const catName = cat.displayName || cat.name;
      const perm = PERMISSIONS.find((entry) => entry.id === permId);
      const confirmed = window.confirm(`确定要为「${catName}」启用高风险权限「${perm?.name}」吗？`);
      if (!confirmed) return;
    }

    const newPerms = wouldEnable
      ? [...currentPerms, permId]
      : currentPerms.filter((permissionId) => permissionId !== permId);

    const key = `${catId}:${permId}`;
    setToggling(key);
    setError(null);
    try {
      await updateCat(catId, { permissions: newPerms });
      await fetchCats();
    } catch (error) {
      setError(getErrorMessage(error, "更新权限失败"));
    } finally {
      setToggling(null);
    }
  };

  if (storeLoading && cats.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--accent)]" />
        <span className="ml-2 text-sm text-[var(--text-soft)]">加载猫咪配置中...</span>
      </div>
    );
  }

  const summaryCards = buildPermissionSummaryCards(cats, PERMISSIONS);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Permission Matrix"
        title="权限矩阵"
        description="先看哪些猫咪还没配置权限、哪些拿到了高风险或全权限，再继续逐项调整授权范围。"
        actions={
          <button
            type="button"
            onClick={() => void fetchCats()}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新权限
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          {cats.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">暂无猫咪配置</p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                请先在「猫咪管理」中配置 Agent，再回来调整权限矩阵。
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto rounded-[1.2rem] border border-[var(--border)] bg-white/55 dark:bg-white/[0.03]">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[var(--line)] text-xs text-[var(--text-faint)]">
                      <th className="px-3 py-3 text-left">权限</th>
                      <th className="px-3 py-3 text-left">风险</th>
                      {cats.map((cat) => (
                        <th key={cat.id} className="min-w-[92px] px-3 py-3 text-center">
                          <span className="text-xs font-medium text-[var(--text-soft)]">
                            {cat.displayName || cat.name}
                          </span>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {PERMISSIONS.map((perm) => (
                      <tr
                        key={perm.id}
                        className="border-b border-gray-100 last:border-0 dark:border-gray-700/50"
                      >
                        <td className="px-3 py-3">
                          <div>
                            <span className="text-sm text-[var(--text-strong)]">{perm.name}</span>
                            <p className="text-[10px] text-[var(--text-faint)]">
                              {perm.description}
                            </p>
                          </div>
                        </td>
                        <td className="px-3 py-3">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                              RISK_COLORS[perm.riskLevel]
                            }`}
                          >
                            {perm.riskLevel === "low"
                              ? "低"
                              : perm.riskLevel === "medium"
                                ? "中"
                                : "高"}
                          </span>
                        </td>
                        {cats.map((cat) => {
                          const enabled = cat.permissions?.includes(perm.id) ?? false;
                          const key = `${cat.id}:${perm.id}`;
                          const isToggling = toggling === key;
                          return (
                            <td key={cat.id} className="px-3 py-3 text-center">
                              <button
                                onClick={() => void handleToggle(cat.id, perm.id, perm.riskLevel)}
                                disabled={isToggling}
                                className={`rounded-full p-1.5 transition-colors ${
                                  enabled
                                    ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
                                    : "text-gray-300 hover:bg-gray-100 dark:text-gray-600 dark:hover:bg-gray-700"
                                } ${isToggling ? "opacity-40" : ""}`}
                              >
                                {enabled ? <Check size={16} /> : <X size={16} />}
                              </button>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--text-faint)]">
                <span className="flex items-center gap-1">
                  <Shield size={12} /> 权限说明
                </span>
                <span className={`${RISK_COLORS.low} rounded px-1.5 py-0.5`}>
                  低风险 — 默认允许
                </span>
                <span className={`${RISK_COLORS.medium} rounded px-1.5 py-0.5`}>
                  中风险 — 默认允许
                </span>
                <span className={`${RISK_COLORS.high} rounded px-1.5 py-0.5`}>
                  高风险 — 需要授权
                </span>
              </div>
            </>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
