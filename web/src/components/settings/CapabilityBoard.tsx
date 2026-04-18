import { useCallback, useEffect, useState, type ElementType } from "react";
import { useCatStore } from "../../stores/catStore";
import { useThreadStore } from "../../stores/threadStore";
import { api } from "../../api/client";
import {
  Activity,
  Loader2,
  RefreshCw,
  Server,
  ToggleLeft,
  ToggleRight,
  Wrench,
} from "lucide-react";
import type { CapabilityBoardItem } from "../../types";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import { buildCapabilitySummaryCards } from "./settingsSummaryModels";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function CapabilityBoard() {
  const cats = useCatStore((s) => s.cats);
  const currentThread = useThreadStore((s) => s.currentThread);
  const [projectPath, setProjectPath] = useState("");
  const [items, setItems] = useState<CapabilityBoardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [probing, setProbing] = useState(false);

  // Default project path from current thread
  useEffect(() => {
    if (currentThread?.project_path) {
      setProjectPath(currentThread.project_path);
    }
  }, [currentThread?.project_path]);

  const fetchBoard = useCallback(
    async (probe = false) => {
      if (!projectPath.trim()) {
        setItems([]);
        setError(null);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await api.capabilities.get(projectPath.trim(), probe);
        setItems(data.items || []);
      } catch (error) {
        setError(getErrorMessage(error, "加载能力看板失败"));
        setItems([]);
      } finally {
        setLoading(false);
      }
    },
    [projectPath]
  );

  useEffect(() => {
    fetchBoard(false);
  }, [fetchBoard]);

  const handleToggle = async (
    item: CapabilityBoardItem,
    scope: "global" | "cat",
    enabled: boolean,
    catId?: string
  ) => {
    const key = `${item.id}:${scope}:${catId || "global"}`;
    setToggling(key);
    setError(null);
    try {
      await api.capabilities.patch({
        capabilityId: item.id,
        capabilityType: item.type,
        scope,
        enabled,
        catId,
        projectPath: projectPath.trim(),
      });
      await fetchBoard();
    } catch (error) {
      setError(getErrorMessage(error, "更新失败"));
    } finally {
      setToggling(null);
    }
  };

  const mcpItems = items.filter((i) => i.type === "mcp");
  const skillItems = items.filter((i) => i.type === "skill");
  const summaryCards = buildCapabilitySummaryCards(items);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Capability Routing"
        title="项目级能力编排"
        description="先看全局启用状态、覆盖分支和异常项，再决定是改默认策略，还是给单只猫做覆盖。这里仍保持即时生效契约。"
        actions={
          <button
            type="button"
            onClick={() => fetchBoard(false)}
            disabled={loading || !projectPath.trim()}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] disabled:opacity-50 dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新看板
          </button>
        }
      >
        <div className="space-y-4">
          <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]">
            <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
              目标项目
            </div>
            <div className="flex flex-col gap-2 lg:flex-row">
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder="输入项目路径"
                className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
              />
              <button
                type="button"
                onClick={() => fetchBoard(false)}
                disabled={loading || !projectPath.trim()}
                className="inline-flex items-center justify-center gap-1 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                加载
              </button>
              <button
                type="button"
                onClick={async () => {
                  setProbing(true);
                  await fetchBoard(true);
                  setProbing(false);
                }}
                disabled={loading || probing || !projectPath.trim()}
                className="inline-flex items-center justify-center gap-1 rounded-xl border border-[rgba(47,116,103,0.2)] bg-[rgba(47,116,103,0.08)] px-4 py-2 text-sm font-medium text-[var(--moss)] transition-colors hover:bg-[rgba(47,116,103,0.12)] disabled:opacity-50 dark:bg-[rgba(121,192,173,0.12)]"
              >
                {probing ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
                探测
              </button>
            </div>
            <p className="mt-3 text-sm leading-7 text-[var(--text-soft)]">
              `加载` 读取当前 capability board，`探测` 会额外尝试 MCP 连通性和 Skill 审计状态。
            </p>
          </div>

          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          {!projectPath.trim() && !loading ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">先输入项目路径</p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                能力编排是项目级配置。先锁定目标项目，再决定默认策略和单猫覆盖。
              </p>
            </div>
          ) : items.length === 0 && !loading ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">暂无能力配置</p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                该项目尚未生成 `capabilities.json`，或者当前配置还没有任何 MCP / Skill 条目。
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {mcpItems.length > 0 && (
                <CapabilitySection
                  title="MCP 服务器"
                  icon={Server}
                  items={mcpItems}
                  cats={cats}
                  toggling={toggling}
                  onToggle={handleToggle}
                  showProbe
                />
              )}

              {skillItems.length > 0 && (
                <CapabilitySection
                  title="Skills"
                  icon={Wrench}
                  items={skillItems}
                  cats={cats}
                  toggling={toggling}
                  onToggle={handleToggle}
                />
              )}
            </div>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}

interface CapabilitySectionProps {
  title: string;
  icon: ElementType;
  items: CapabilityBoardItem[];
  cats: { id: string; displayName?: string; name: string }[];
  toggling: string | null;
  onToggle: (
    item: CapabilityBoardItem,
    scope: "global" | "cat",
    enabled: boolean,
    catId?: string
  ) => Promise<void>;
  showProbe?: boolean;
}

function CapabilitySection({
  title,
  icon: Icon,
  items,
  cats,
  toggling,
  onToggle,
  showProbe,
}: CapabilitySectionProps) {
  return (
    <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]">
      <h4 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
        <Icon size={14} />
        {title}
      </h4>
      <div className="overflow-hidden rounded-[1rem] border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">名称</th>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">来源</th>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">全局</th>
              {cats.map((cat) => (
                <th
                  key={cat.id}
                  className="px-2 py-2 text-center font-medium text-gray-500 dark:text-gray-400"
                >
                  {cat.displayName || cat.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {items.map((item) => {
              const globalKey = `${item.id}:global:global`;
              return (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-800 dark:text-gray-200">{item.id}</div>
                    {item.description && (
                      <div className="max-w-xs truncate text-[10px] text-gray-500 dark:text-gray-400">
                        {item.description}
                      </div>
                    )}
                    {showProbe && item.connectionStatus && (
                      <div className="mt-1 flex items-center gap-1.5 text-[10px]">
                        <span
                          className={[
                            "inline-block h-1.5 w-1.5 rounded-full",
                            item.connectionStatus === "connected" ? "bg-green-500" : "",
                            item.connectionStatus === "timeout" ? "bg-amber-500" : "",
                            item.connectionStatus === "error" ? "bg-red-500" : "",
                            item.connectionStatus === "unsupported" ? "bg-gray-400" : "",
                          ].join(" ")}
                        />
                        <span
                          className={[
                            item.connectionStatus === "connected"
                              ? "text-green-600 dark:text-green-400"
                              : "",
                            item.connectionStatus === "timeout"
                              ? "text-amber-600 dark:text-amber-400"
                              : "",
                            item.connectionStatus === "error"
                              ? "text-red-600 dark:text-red-400"
                              : "",
                            item.connectionStatus === "unsupported"
                              ? "text-gray-500 dark:text-gray-400"
                              : "",
                          ].join(" ")}
                        >
                          {item.connectionStatus === "connected" &&
                            `已连接 · ${(item.tools || []).length} 工具`}
                          {item.connectionStatus === "timeout" && "探测超时"}
                          {item.connectionStatus === "error" && (item.probeError || "连接错误")}
                          {item.connectionStatus === "unsupported" && "不支持探测"}
                        </span>
                      </div>
                    )}
                    {item.type === "skill" && item.auditStatus && (
                      <div className="mt-1 flex items-center gap-1.5 text-[10px]">
                        <span
                          className={[
                            "inline-block h-1.5 w-1.5 rounded-full",
                            item.auditStatus === "passed" ? "bg-green-500" : "",
                            item.auditStatus === "failed" ? "bg-red-500" : "",
                            item.auditStatus === "error" ? "bg-amber-500" : "",
                            item.auditStatus === "missing" ? "bg-gray-400" : "",
                          ].join(" ")}
                        />
                        <span
                          className={[
                            item.auditStatus === "passed"
                              ? "text-green-600 dark:text-green-400"
                              : "",
                            item.auditStatus === "failed" ? "text-red-600 dark:text-red-400" : "",
                            item.auditStatus === "error"
                              ? "text-amber-600 dark:text-amber-400"
                              : "",
                            item.auditStatus === "missing"
                              ? "text-gray-500 dark:text-gray-400"
                              : "",
                          ].join(" ")}
                        >
                          {item.auditStatus === "passed" && "安全审计通过"}
                          {item.auditStatus === "failed" && "安全审计未通过"}
                          {item.auditStatus === "error" && "审计异常"}
                          {item.auditStatus === "missing" && "技能目录缺失"}
                        </span>
                        {item.auditIssues && item.auditIssues.length > 0 && (
                          <span className="text-gray-400" title={item.auditIssues.join("\n")}>
                            · {item.auditIssues.length} 项
                          </span>
                        )}
                      </div>
                    )}
                    {item.type === "skill" && item.triggers && item.triggers.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {item.triggers.map((t) => (
                          <span
                            key={t}
                            className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-600 dark:bg-amber-900/20 dark:text-amber-400"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {item.source}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => onToggle(item, "global", !item.enabled)}
                      disabled={toggling === globalKey}
                      className="disabled:opacity-50"
                    >
                      {item.enabled ? (
                        <ToggleRight size={20} className="text-green-500" />
                      ) : (
                        <ToggleLeft size={20} className="text-gray-400" />
                      )}
                    </button>
                  </td>
                  {cats.map((cat) => {
                    const enabled = item.cats[cat.id] ?? false;
                    const key = `${item.id}:cat:${cat.id}`;
                    return (
                      <td key={cat.id} className="px-2 py-2 text-center">
                        <button
                          type="button"
                          onClick={() => onToggle(item, "cat", !enabled, cat.id)}
                          disabled={toggling === key}
                          className="disabled:opacity-50"
                        >
                          {enabled ? (
                            <ToggleRight size={18} className="text-blue-500" />
                          ) : (
                            <ToggleLeft size={18} className="text-gray-300 dark:text-gray-600" />
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
