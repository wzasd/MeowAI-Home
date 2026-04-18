import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  MessageSquare,
  Minus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Zap,
  Trophy,
} from "lucide-react";
import { useCatStore } from "../../stores/catStore";
import { api } from "../../api/client";
import type { MetricsLeaderboardEntry } from "../../types";
import {
  buildQuotaMetricSnapshot,
  buildQuotaSummaryCards,
  buildLeaderboardSummaryCards,
  rankLeaderboardEntries,
  type QuotaMetricSnapshot,
} from "../settings/settingsSummaryModels";
import { buildQuotaSectionState } from "./metricsPanelModel";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp size={12} className="text-green-500" />;
  if (trend === "down") return <TrendingDown size={12} className="text-red-500" />;
  return <Minus size={12} className="text-gray-400" />;
};

function CompactSummaryCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "neutral" | "accent" | "success" | "attention";
}) {
  const toneClass =
    tone === "accent"
      ? "text-[var(--accent-deep)] dark:text-[var(--accent)]"
      : tone === "success"
        ? "text-green-600 dark:text-green-400"
        : tone === "attention"
          ? "text-amber-600 dark:text-amber-400"
          : "text-[var(--text-strong)]";

  return (
    <div className="nest-card nest-r-md px-2.5 py-2">
      <div className="text-[9px] uppercase tracking-[0.08em] text-[var(--text-faint)]">{label}</div>
      <div className={`mt-0.5 text-sm font-semibold ${toneClass}`}>{value}</div>
      <div className="mt-0.5 truncate text-[10px] text-[var(--text-soft)]">{detail}</div>
    </div>
  );
}

function QuotaSection() {
  const cats = useCatStore((s) => s.cats);
  const [metrics, setMetrics] = useState<QuotaMetricSnapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [partialFailure, setPartialFailure] = useState(false);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPartialFailure(false);
    try {
      let failedCount = 0;
      const results = await Promise.all(
        cats.map(async (cat) => {
          try {
            const data = await api.metrics.cat(cat.id, 7);
            return buildQuotaMetricSnapshot(cat.id, data.data || []);
          } catch {
            failedCount++;
            return buildQuotaMetricSnapshot(cat.id, []);
          }
        })
      );
      if (failedCount === cats.length && cats.length > 0) {
        setError("所有猫咪的配额数据拉取失败，请稍后刷新重试");
      } else if (failedCount > 0) {
        setPartialFailure(true);
      }
      setMetrics(results);
    } catch (err) {
      setError(getErrorMessage(err, "加载配额失败"));
    } finally {
      setLoading(false);
    }
  }, [cats]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const summaryCards = buildQuotaSummaryCards(metrics, cats.length);
  const quotaState = buildQuotaSectionState({
    metrics,
    error,
    partialFailure,
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[11px] font-medium text-[var(--text-strong)]">配额观测（7天）</div>
        <button
          type="button"
          onClick={() => void fetchMetrics()}
          disabled={loading}
          className="inline-flex items-center gap-1 rounded-full border border-[var(--line)] bg-white/65 px-2 py-1 text-[10px] text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] disabled:opacity-60 dark:bg-white/[0.05]"
        >
          <RefreshCw size={10} className={loading ? "animate-spin" : ""} />
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-[1rem] border border-red-200 bg-red-50 px-2.5 py-2 text-[10px] text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {!error && partialFailure && quotaState.kind === "data" && quotaState.warning && (
        <div className="rounded-[1rem] border border-amber-200 bg-amber-50 px-2.5 py-2 text-[10px] text-amber-700 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-300">
          {quotaState.warning}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {summaryCards.map((card) => (
          <CompactSummaryCard
            key={card.id}
            label={card.label}
            value={card.value}
            detail={card.detail}
            tone={card.tone}
          />
        ))}
      </div>

      {quotaState.kind === "error" ? (
        <div className="nest-card nest-r-md border border-red-200 bg-red-50/70 px-3 py-3 text-[10px] text-red-600 dark:border-red-900/40 dark:bg-red-900/10 dark:text-red-300">
          这不是“无数据”，而是配额观测请求失败。请先刷新，必要时检查后端 metrics 接口。
        </div>
      ) : quotaState.kind === "empty" ? (
        <div className="nest-card nest-r-md px-3 py-3 text-[10px] text-[var(--text-faint)]">
          最近 7 天还没有调用记录
        </div>
      ) : (
        <div className="space-y-1.5">
          {quotaState.activeMetrics.map((metric) => {
            const cat = cats.find((c) => c.id === metric.catId);
            return (
              <div
                key={metric.catId}
                className="nest-card nest-r-md border border-[var(--border)] px-2.5 py-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: cat?.colorPrimary || "#999" }}
                    />
                    <span className="truncate text-[11px] font-medium text-[var(--text-strong)]">
                      {cat?.displayName || metric.catId}
                    </span>
                  </div>
                  <TrendIcon trend={metric.trend} />
                </div>
                <div className="mt-1.5 grid grid-cols-3 gap-1 text-[10px] text-[var(--text-soft)]">
                  <span className="inline-flex items-center gap-1">
                    <Zap size={10} />
                    {Math.round(metric.totalTokens / 1000)}k
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <MessageSquare size={10} />
                    {metric.totalInvocations}
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
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const BADGE_COLORS = {
  gold: "text-amber-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

function LeaderboardSection() {
  const cats = useCatStore((s) => s.cats);
  const [entries, setEntries] = useState<MetricsLeaderboardEntry[]>([]);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.metrics.leaderboard(days);
      setEntries(data.leaderboard || []);
    } catch (err) {
      setEntries([]);
      setError(getErrorMessage(err, "加载排行榜失败"));
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  const ranked = rankLeaderboardEntries(entries);
  const summaryCards = buildLeaderboardSummaryCards(ranked);
  const top3 = ranked.slice(0, 3);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[11px] font-medium text-[var(--text-strong)]">排行榜</div>
        <div className="flex items-center gap-1">
          {[7, 30, 0].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDays(value)}
              disabled={loading}
              className={`rounded-full px-2 py-1 text-[10px] font-medium transition-colors disabled:opacity-60 ${
                days === value
                  ? "bg-[var(--accent)] text-[var(--accent-contrast)]"
                  : "border border-[var(--border)] bg-white/65 text-[var(--text-soft)] hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
              }`}
            >
              {value === 0 ? "全部" : `${value} 天`}
            </button>
          ))}
          <button
            type="button"
            onClick={() => void fetchLeaderboard()}
            disabled={loading}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-2 py-1 text-[10px] font-medium text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] disabled:opacity-60 dark:bg-white/[0.05]"
          >
            <RefreshCw size={10} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-[1rem] border border-red-200 bg-red-50 px-2.5 py-2 text-[10px] text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {summaryCards.map((card) => (
          <CompactSummaryCard
            key={card.id}
            label={card.label}
            value={card.value}
            detail={card.detail}
            tone={card.tone}
          />
        ))}
      </div>

      {ranked.length === 0 ? (
        <div className="nest-card nest-r-md px-3 py-3 text-[10px] text-[var(--text-faint)]">
          当前时间窗口还没有排行数据
        </div>
      ) : (
        <div className="space-y-2">
          {top3.length > 0 && (
            <div className="nest-card nest-r-md border border-[var(--border)] px-2.5 py-2">
              <div className="mb-1.5 text-[10px] font-medium text-[var(--text-faint)]">Top 3</div>
              <div className="space-y-1.5">
                {top3.map((entry) => {
                  const cat = cats.find((c) => c.id === entry.cat_id);
                  const badgeKey =
                    entry.rank <= 3
                      ? (["gold", "silver", "bronze"] as const)[entry.rank - 1]
                      : null;
                  return (
                    <div key={entry.cat_id} className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-1.5">
                        {badgeKey && <Trophy size={12} className={BADGE_COLORS[badgeKey]} />}
                        <span className="truncate text-[11px] font-medium text-[var(--text-strong)]">
                          {cat?.displayName || entry.cat_id}
                        </span>
                      </div>
                      <span className="shrink-0 text-[10px] text-[var(--text-soft)]">
                        {entry.score.toFixed(1)} 分
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="overflow-hidden rounded-[1rem] border border-[var(--border)]">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-[9px] text-gray-500 dark:border-gray-700 dark:bg-gray-800">
                  <th className="px-2 py-1.5">#</th>
                  <th className="px-2 py-1.5">猫</th>
                  <th className="px-2 py-1.5 text-right">成功率</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((entry) => {
                  const cat = cats.find((c) => c.id === entry.cat_id);
                  return (
                    <tr
                      key={entry.cat_id}
                      className="border-b border-gray-100 last:border-0 dark:border-gray-700/50"
                    >
                      <td className="px-2 py-1.5 text-[10px] text-gray-500">{entry.rank}</td>
                      <td className="px-2 py-1.5 text-[11px] font-medium text-[var(--text-strong)]">
                        {cat?.displayName || entry.cat_id}
                      </td>
                      <td
                        className={`px-2 py-1.5 text-right text-[10px] ${
                          entry.success_rate >= 0.95
                            ? "text-green-600 dark:text-green-400"
                            : entry.success_rate >= 0.9
                              ? "text-amber-600 dark:text-amber-400"
                              : "text-red-600 dark:text-red-400"
                        }`}
                      >
                        {(entry.success_rate * 100).toFixed(0)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export function MetricsPanel() {
  return (
    <div className="space-y-4">
      <div className="rounded-[1rem] border border-[var(--line)] bg-white/55 px-3 py-2 text-[10px] leading-6 text-[var(--text-faint)] dark:bg-white/[0.04]">
        指标页展示的是全局运行数据，不按当前线程过滤。
      </div>
      <QuotaSection />
      <LeaderboardSection />
    </div>
  );
}
