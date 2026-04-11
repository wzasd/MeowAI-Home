import { useState, useEffect } from "react";
import { useCatStore } from "../../stores/catStore";
import { TrendingUp, TrendingDown, Minus, Zap, Clock, MessageSquare, CheckCircle2 } from "lucide-react";

interface CatMetrics {
  catId: string;
  totalInvocations: number;
  successRate: number;
  avgLatencyMs: number;
  totalTokens: number;
  trend: "up" | "down" | "stable";
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp size={14} className="text-green-500" />;
  if (trend === "down") return <TrendingDown size={14} className="text-red-500" />;
  return <Minus size={14} className="text-gray-400" />;
};

export function QuotaBoard() {
  const cats = useCatStore((s) => s.cats);
  const [metrics, setMetrics] = useState<CatMetrics[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/metrics/cats`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return <div className="p-4 text-gray-400">加载中...</div>;
  }

  const totalTokens = metrics.reduce((sum, m) => sum + m.totalTokens, 0);
  const totalInvocations = metrics.reduce((sum, m) => sum + m.totalInvocations, 0);
  const avgSuccessRate = metrics.length > 0
    ? metrics.reduce((sum, m) => sum + m.successRate, 0) / metrics.length
    : 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <Zap size={18} className="text-blue-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{(totalTokens / 1000000).toFixed(1)}M</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">总 Token 消耗</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <MessageSquare size={18} className="text-green-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{totalInvocations}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">总调用次数</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <CheckCircle2 size={18} className="text-purple-500" />
          <p className="mt-1 text-2xl font-bold text-gray-800 dark:text-gray-200">{(avgSuccessRate * 100).toFixed(1)}%</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">平均成功率</p>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">按猫咪分布</h4>
        <div className="space-y-2">
          {metrics.map((metric) => {
            const cat = cats.find((c) => c.id === metric.catId);
            return (
              <div key={metric.catId} className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                <span className="w-20 text-sm font-medium text-gray-800 dark:text-gray-200">{cat?.displayName || metric.catId}</span>
                <div className="flex flex-1 items-center gap-4 text-xs">
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <Zap size={10} /> {(metric.totalTokens / 1000).toFixed(0)}k tokens
                  </span>
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <MessageSquare size={10} /> {metric.totalInvocations} 次
                  </span>
                  <span className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
                    <Clock size={10} /> {metric.avgLatencyMs}ms
                  </span>
                  <span className={`font-medium ${metric.successRate > 0.95 ? "text-green-600" : "text-amber-600"}`}>
                    {(metric.successRate * 100).toFixed(0)}%
                  </span>
                  <TrendIcon trend={metric.trend} />
                </div>
                <div className="w-24">
                  <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${(metric.totalTokens / totalTokens) * 100}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
