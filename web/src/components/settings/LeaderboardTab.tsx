import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw, Trophy } from "lucide-react";
import { useCatStore } from "../../stores/catStore";
import { api } from "../../api/client";
import type { MetricsLeaderboardEntry } from "../../types";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import { buildLeaderboardSummaryCards, rankLeaderboardEntries } from "./settingsSummaryModels";

const BADGE_COLORS = {
  gold: "text-amber-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

const PODIUM_ORDER = [1, 0, 2] as const;
const PODIUM_HEIGHTS = ["h-24", "h-32", "h-20"];
const PODIUM_BACKGROUNDS = [
  "bg-gray-100 dark:bg-gray-700",
  "bg-amber-50 dark:bg-amber-900/20",
  "bg-amber-100 dark:bg-amber-900/30",
];
const RANK_BADGES = ["gold", "silver", "bronze"] as const;

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function LeaderboardTab() {
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
    } catch (error) {
      setEntries([]);
      setError(getErrorMessage(error, "加载排行榜失败"));
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    fetchLeaderboard();
  }, [fetchLeaderboard]);

  if (loading && entries.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500">加载排行榜中...</span>
      </div>
    );
  }

  const ranked = rankLeaderboardEntries(entries);
  const summaryCards = buildLeaderboardSummaryCards(ranked);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Observation Lens"
        title="猫咪表现排行榜"
        description="这是只读排名视图。综合分仍基于成功率和平均响应速度，后续如果迁出设置页，可以直接复用这套排序和摘要逻辑。"
        actions={
          <div className="flex flex-wrap gap-2">
            {[7, 30, 0].map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setDays(value)}
                className={`rounded-full px-3 py-2 text-xs font-medium transition-colors ${
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
              onClick={fetchLeaderboard}
              className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-xs font-medium text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
            >
              <RefreshCw size={12} />
              刷新
            </button>
          </div>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 px-4 py-3 text-sm leading-7 text-[var(--text-soft)] dark:bg-white/[0.03]">
            时间窗口只影响样本范围，不改评分公式。当前分数 = 成功率 × 100 - 平均延迟秒数。
          </div>

          {ranked.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">
                当前时间窗口还没有排行数据
              </p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                先让猫咪在选定窗口内实际跑任务，再回来比较成功率、延迟和 token 体量。
              </p>
            </div>
          ) : (
            <>
              <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
                  领奖台
                </h4>
                <div className="flex items-end justify-center gap-3 py-4">
                  {PODIUM_ORDER.map((entryIndex, slotIndex) => {
                    const entry = ranked[entryIndex];
                    if (!entry) return null;
                    const cat = cats.find((candidate) => candidate.id === entry.cat_id);
                    const badgeKey = RANK_BADGES[entry.rank - 1] as keyof typeof BADGE_COLORS;

                    return (
                      <div key={entry.cat_id} className="flex flex-col items-center">
                        <span className="text-2xl">{cat?.displayName?.charAt(0) || "?"}</span>
                        <span className="mt-1 text-xs font-bold text-gray-800 dark:text-gray-200">
                          {cat?.displayName || entry.cat_id}
                        </span>
                        <span className="text-xs text-gray-500">{entry.score.toFixed(1)} 分</span>
                        <div
                          className={`mt-2 flex w-20 items-end justify-center rounded-t-[1rem] ${PODIUM_BACKGROUNDS[slotIndex]} ${PODIUM_HEIGHTS[slotIndex]}`}
                        >
                          <Trophy size={16} className={BADGE_COLORS[badgeKey]} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="overflow-hidden rounded-[1.2rem] border border-[var(--border)]">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-800">
                      <th className="px-3 py-2">排名</th>
                      <th className="px-3 py-2">猫咪</th>
                      <th className="px-3 py-2 text-right">调用</th>
                      <th className="px-3 py-2 text-right">Token</th>
                      <th className="px-3 py-2 text-right">成功率</th>
                      <th className="px-3 py-2 text-right">延迟</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ranked.map((entry) => {
                      const cat = cats.find((candidate) => candidate.id === entry.cat_id);
                      const badge =
                        entry.rank <= 3
                          ? (["gold", "silver", "bronze"] as const)[entry.rank - 1]
                          : null;
                      return (
                        <tr
                          key={entry.cat_id}
                          className="border-b border-gray-100 last:border-0 dark:border-gray-700/50"
                        >
                          <td className="px-3 py-2">
                            {badge ? (
                              <Trophy size={14} className={BADGE_COLORS[badge]} />
                            ) : (
                              <span className="text-xs text-gray-500">#{entry.rank}</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200">
                            {cat?.displayName || entry.cat_id}
                          </td>
                          <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">
                            {entry.total_calls}
                          </td>
                          <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">
                            {entry.totalTokens.toLocaleString()}
                          </td>
                          <td className="px-3 py-2 text-right text-xs">
                            <span
                              className={
                                entry.success_rate >= 0.95
                                  ? "text-green-600 dark:text-green-400"
                                  : entry.success_rate >= 0.9
                                    ? "text-amber-600 dark:text-amber-400"
                                    : "text-red-600 dark:text-red-400"
                              }
                            >
                              {(entry.success_rate * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">
                            {Math.round(entry.avg_duration_ms)}ms
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
