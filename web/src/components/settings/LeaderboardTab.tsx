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

const MOCK_LEADERBOARD: LeaderboardEntry[] = [
  { catId: "orange", rank: 1, score: 96.4, totalInvocations: 142, successRate: 0.97, avgLatencyMs: 2300, badge: "gold" },
  { catId: "tabby", rank: 2, score: 94.8, totalInvocations: 45, successRate: 0.98, avgLatencyMs: 1500, badge: "silver" },
  { catId: "inky", rank: 3, score: 92.1, totalInvocations: 98, successRate: 0.95, avgLatencyMs: 1800, badge: "bronze" },
  { catId: "siamese", rank: 4, score: 88.5, totalInvocations: 33, successRate: 0.94, avgLatencyMs: 2800 },
  { catId: "patch", rank: 5, score: 85.3, totalInvocations: 67, successRate: 0.92, avgLatencyMs: 3100 },
];

const BADGE_COLORS = {
  gold: "text-amber-500",
  silver: "text-gray-400",
  bronze: "text-amber-700",
};

export function LeaderboardTab() {
  const cats = useCatStore((s) => s.cats);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        猫咪表现排行榜 — 综合评分基于成功率、响应速度和任务完成度。
      </p>

      {/* Podium */}
      <div className="flex items-end justify-center gap-3 py-4">
        {[1, 0, 2].map((idx) => {
          const entry = MOCK_LEADERBOARD[idx];
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

      {/* Full table */}
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
            {MOCK_LEADERBOARD.map((entry) => {
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
                  <td className="px-3 py-2 text-sm font-medium text-gray-800 dark:text-gray-200">
                    {cat?.displayName || entry.catId}
                  </td>
                  <td className="px-3 py-2 text-right text-sm font-bold text-gray-800 dark:text-gray-200">
                    {entry.score.toFixed(1)}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">
                    {entry.totalInvocations}
                  </td>
                  <td className="px-3 py-2 text-right text-xs">
                    <span className={entry.successRate > 0.95 ? "text-green-600" : "text-amber-600"}>
                      {(entry.successRate * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-gray-600 dark:text-gray-400">
                    {entry.avgLatencyMs}ms
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
