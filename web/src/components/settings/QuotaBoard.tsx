import { useCallback, useEffect, useState } from "react";
import { useCatStore } from "../../stores/catStore";
import { api } from "../../api/client";
import {
  CheckCircle2,
  Clock,
  Loader2,
  MessageSquare,
  Minus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import {
  buildQuotaMetricSnapshot,
  buildQuotaSummaryCards,
  type QuotaMetricSnapshot,
} from "./settingsSummaryModels";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp size={14} className="text-green-500" />;
  if (trend === "down") return <TrendingDown size={14} className="text-red-500" />;
  return <Minus size={14} className="text-gray-400" />;
};

export function QuotaBoard() {
  const cats = useCatStore((s) => s.cats);
  const [metrics, setMetrics] = useState<QuotaMetricSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await Promise.all(
        cats.map(async (cat) => {
          try {
            const data = await api.metrics.cat(cat.id, 7);
            return buildQuotaMetricSnapshot(cat.id, data.data || []);
          } catch {
            return buildQuotaMetricSnapshot(cat.id, []);
          }
        })
      );
      setMetrics(results);
    } catch (error) {
      setError(getErrorMessage(error, "加载配额观测数据失败"));
    } finally {
      setLoading(false);
    }
  }, [cats]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  if (loading && metrics.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">加载配额观测中...</span>
      </div>
    );
  }

  const summaryCards = buildQuotaSummaryCards(metrics, cats.length);
  const totalTokens = metrics.reduce((sum, metric) => sum + metric.totalTokens, 0);
  const activeMetrics = metrics.filter((metric) => metric.totalInvocations > 0);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Observation Lens"
        title="猫咪资源与配额观测"
        description="这页是只读观测，不做任何配置写入。先看过去 7 天的资源消耗、成功率和响应延迟，再决定是否需要把能力或权限迁回设置主流程。"
        actions={
          <button
            type="button"
            onClick={fetchMetrics}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新观测
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 px-4 py-3 text-sm leading-7 text-[var(--text-soft)] dark:bg-white/[0.03]">
            当前窗口固定为最近 7
            天。后续如果把这块正式迁出设置页，再考虑和右侧观察面板共用时间范围控制。
          </div>

          {activeMetrics.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">
                最近 7 天还没有调用记录
              </p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                这页适合观察资源压力和异常趋势。当前没有可用样本，先去对话流里跑实际任务再回来判断。
              </p>
            </div>
          ) : (
            <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
                按猫咪分布
              </h4>
              <div className="space-y-3">
                {metrics.map((metric) => {
                  const cat = cats.find((candidate) => candidate.id === metric.catId);
                  return (
                    <div
                      key={metric.catId}
                      className="rounded-[1rem] border border-[var(--border)] bg-white/80 p-4 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)] dark:bg-white/[0.04]"
                    >
                      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
                        <div className="xl:w-32">
                          <div className="text-sm font-medium text-[var(--text-strong)]">
                            {cat?.displayName || metric.catId}
                          </div>
                          <div className="mt-1 flex items-center gap-1 text-xs text-[var(--text-faint)]">
                            <TrendIcon trend={metric.trend} />
                            <span>
                              {metric.trend === "up" && "稳定"}
                              {metric.trend === "stable" && "平稳"}
                              {metric.trend === "down" && "需关注"}
                            </span>
                          </div>
                        </div>

                        <div className="grid flex-1 gap-3 text-xs text-[var(--text-soft)] md:grid-cols-4">
                          <span className="inline-flex items-center gap-1">
                            <Zap size={10} />
                            {Math.round(metric.totalTokens / 1000)}k tokens
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <MessageSquare size={10} />
                            {metric.totalInvocations} 次调用
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <Clock size={10} />
                            {metric.avgLatencyMs}ms
                          </span>
                          <span
                            className={`inline-flex items-center gap-1 font-medium ${
                              metric.successRate > 0.95
                                ? "text-green-600 dark:text-green-400"
                                : metric.successRate >= 0.9
                                  ? "text-amber-600 dark:text-amber-400"
                                  : "text-red-600 dark:text-red-400"
                            }`}
                          >
                            <CheckCircle2 size={10} />
                            {(metric.successRate * 100).toFixed(0)}%
                          </span>
                        </div>

                        <div className="xl:w-32">
                          <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                            <div
                              className="h-full rounded-full bg-[var(--accent)]"
                              style={{
                                width: `${totalTokens > 0 ? (metric.totalTokens / totalTokens) * 100 : 0}%`,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
