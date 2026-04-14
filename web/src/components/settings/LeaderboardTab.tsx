import { useState, useEffect } from "react";
import { Trophy } from "lucide-react";
import { useCatStore } from "../../stores/catStore";
import { api } from "../../api/client";

interface LeaderboardEntry {
  cat_id: string;
  total_calls: number;
  success_rate: number;
  avg_duration_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
}

const BADGE_COLORS = {
  gold: "text-amber-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

export function LeaderboardTab() {
  const cats = useCatStore((s) => s.cats);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      setLoading(true);
      try {
        const data = await api.metrics.leaderboard(days);
        setEntries(data.leaderboard || []);
      } catch {
        setEntries([]);
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
  }, [days]);

  const ranked = entries
    .map((e) => {
      const score = (e.success_rate * 100) - (e.avg_duration_ms / 1000);
      return { ...e, score };
    })
    .sort((a, b) => b.score - a.score)
    .map((e, i) => ({ ...e, rank: i + 1 }));

  const badges = ranked.slice(0, 3).map((_, i) => (i === 0 ? "gold" : i === 1 ? "silver" : "bronze"));

  if (loading) {
    return <div className="p-4 text-gray-400">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          猫咪表现排行榜 — 综合评分基于成功率、响应速度和任务完成度。
        </p>
        <div className="flex gap-2">
          {[7, 30, 0].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded px-2 py-1 text-xs ${days === d ? "bg-blue-500 text-white" : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"}`}
            >
              {d === 0 ? "全部" : `${d}天`}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-end justify-center gap-3 py-4">
        {[1, 0, 2].map((idx) => {
          const entry = ranked[idx];
          if (!entry) return null;
          const cat = cats.find((c) => c.id === entry.cat_id);
          const heights = ["h-24", "h-32", "h-20"];
          const colors = ["bg-amber-100 dark:bg-amber-900/30", "bg-amber-50 dark:bg-amber-900/20", "bg-gray-100 dark:bg-gray-700"];
          const badgeKey = badges[idx] as keyof typeof BADGE_COLORS;

          return (
            <div key={entry.cat_id} className="flex flex-col items-center">
              <span className="text-2xl">{cat?.displayName?.charAt(0) || "?"}</span>
              <span className="mt-1 text-xs font-bold text-gray-800 dark:text-gray-200">{cat?.displayName || entry.cat_id}</span>
              <span className="text-xs text-gray-500">{entry.score.toFixed(1)}分</span>
              <div className={`mt-2 flex w-20 items-end justify-center rounded-t-lg ${colors[idx]} ${heights[idx]}`}>
                <Trophy size={16} className={BADGE_COLORS[badgeKey]} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-800">
              <th className="px-3 py-2 text-left">排名</th>
              <th className="px-3 py-2 text-left">猫咪</th>
              <th className="px-3 py-2 text-right">调用</th>
              <th className="px-3 py-2 text-right">Token</th>
              <th className="px-3 py-2 text-right">成功率</th>
              <th className="px-3 py-2 text-right">延迟</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map((entry) => {
              const cat = cats.find((c) => c.id === entry.cat_id);
              const badge = entry.rank <= 3 ? (["silver", "gold", "bronze"] as const)[entry.rank - 1] : null;
              return (
                <tr key={entry.cat_id} className="border-b border-gray-100 last:border-0 dark:border-gray-700/50">
                  <td className="px-3 py-2">
                    {badge ? (
                      <Trophy size={14} className={BADGE_COLORS[badge]} />
                    ) : (
                      <span className="text-xs text-gray-500">#{entry.rank}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200">{cat?.displayName || entry.cat_id}</td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">{entry.total_calls}</td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">{(entry.prompt_tokens + entry.completion_tokens).toLocaleString()}</td>
                  <td className="px-3 py-2 text-right text-xs">
                    <span className={entry.success_rate > 0.95 ? "text-green-600" : "text-amber-600"}>{(entry.success_rate * 100).toFixed(0)}%</span>
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">{Math.round(entry.avg_duration_ms)}ms</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
