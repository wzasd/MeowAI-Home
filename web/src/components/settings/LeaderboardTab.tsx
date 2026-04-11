import { useState, useEffect } from "react";
import { Trophy } from "lucide-react";
import { useCatStore } from "../../stores/catStore";

interface LeaderboardEntry {
  catId: string;
  rank: number;
  score: number;
  totalInvocations: number;
  successRate: number;
  avgLatencyMs: number;
  badge?: "gold" | "silver" | "bronze";
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const BADGE_COLORS = {
  gold: "text-amber-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

export function LeaderboardTab() {
  const cats = useCatStore((s) => s.cats);
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/metrics/leaderboard`);
        if (res.ok) {
          const data = await res.json();
          setEntries(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
  }, []);

  if (loading) {
    return <div className="p-4 text-gray-400">加载中...</div>;
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        猫咪表现排行榜 — 综合评分基于成功率、响应速度和任务完成度。
      </p>

      <div className="flex items-end justify-center gap-3 py-4">
        {[1, 0, 2].map((idx) => {
          const entry = entries[idx];
          if (!entry) return null;
          const cat = cats.find((c) => c.id === entry.catId);
          const heights = ["h-24", "h-32", "h-20"];
          const colors = ["bg-amber-100 dark:bg-amber-900/30", "bg-amber-50 dark:bg-amber-900/20", "bg-gray-100 dark:bg-gray-700"];

          return (
            <div key={entry.catId} className="flex flex-col items-center">
              <span className="text-2xl">{cat?.displayName?.charAt(0) || "?"}</span>
              <span className="mt-1 text-xs font-bold text-gray-800 dark:text-gray-200">{cat?.displayName || entry.catId}</span>
              <span className="text-xs text-gray-500">{entry.score.toFixed(1)}分</span>
              <div className={`mt-2 flex w-20 items-end justify-center rounded-t-lg ${colors[idx]} ${heights[idx]}`}>
                <span className="text-lg font-bold text-gray-600 dark:text-gray-300">#{entry.rank}</span>
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
              <th className="px-3 py-2 text-right">评分</th>
              <th className="px-3 py-2 text-right">调用</th>
              <th className="px-3 py-2 text-right">成功率</th>
              <th className="px-3 py-2 text-right">延迟</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const cat = cats.find((c) => c.id === entry.catId);
              return (
                <tr key={entry.catId} className="border-b border-gray-100 last:border-0 dark:border-gray-700/50">
                  <td className="px-3 py-2">
                    {entry.badge ? (
                      <Trophy size={14} className={BADGE_COLORS[entry.badge]} />
                    ) : (
                      <span className="text-xs text-gray-500">#{entry.rank}</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200">{cat?.displayName || entry.catId}</td>
                  <td className="px-3 py-2 text-right text-sm font-bold text-gray-800 dark:text-gray-200">{entry.score.toFixed(1)}</td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">{entry.totalInvocations}</td>
                  <td className="px-3 py-2 text-right text-xs">
                    <span className={entry.successRate > 0.95 ? "text-green-600" : "text-amber-600"}>{(entry.successRate * 100).toFixed(0)}%</span>
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">{entry.avgLatencyMs}ms</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
