import { useState, useEffect } from "react";
import { Zap, Database, Clock } from "lucide-react";
import { buildApiUrl } from "../../api/runtimeConfig";

interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  cacheHitRate: number;
  totalCost: number;
}

export function TokenUsagePanel({ threadId }: { threadId: string | null }) {
  const [usage, setUsage] = useState<TokenUsage | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchUsage = async () => {
      setLoading(true);
      try {
        const url = threadId
          ? buildApiUrl(`/api/metrics/token-usage?threadId=${threadId}`)
          : buildApiUrl("/api/metrics/token-usage");
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          setUsage(data);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchUsage();
  }, [threadId]);

  if (loading || !usage) {
    return <div className="text-sm text-[var(--text-faint)]">加载中...</div>;
  }

  const total = usage.promptTokens + usage.completionTokens;
  const promptPct = total > 0 ? (usage.promptTokens / total) * 100 : 0;
  const completionPct = 100 - promptPct;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={<Zap size={14} className="text-[var(--accent)]" />}
          label="Prompt"
          value={`${(usage.promptTokens / 1000).toFixed(1)}k`}
        />
        <StatCard
          icon={<Zap size={14} className="text-green-500" />}
          label="Completion"
          value={`${(usage.completionTokens / 1000).toFixed(1)}k`}
        />
        <StatCard
          icon={<Database size={14} className="text-[var(--moss)]" />}
          label="缓存命中率"
          value={`${(usage.cacheHitRate * 100).toFixed(0)}%`}
        />
        <StatCard
          icon={<Clock size={14} className="text-amber-500" />}
          label="总费用"
          value={`$${usage.totalCost.toFixed(2)}`}
        />
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold tracking-[0.08em] text-[var(--text-faint)] uppercase">Token 分布</h4>
        <div className="h-3 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
          <div className="flex h-full">
            <div className="bg-[var(--accent)]" style={{ width: `${promptPct}%` }} title="Prompt" />
            <div className="bg-green-500" style={{ width: `${completionPct}%` }} title="Completion" />
          </div>
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-[var(--text-faint)]">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-[var(--accent)]" />
            Prompt
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
            Completion
          </span>
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold tracking-[0.08em] text-[var(--text-faint)] uppercase">缓存命中率</h4>
        <div className="h-3 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
          <div
            className="h-full rounded-full bg-[var(--moss)] transition-all"
            style={{ width: `${usage.cacheHitRate * 100}%` }}
          />
        </div>
        <p className="mt-1 text-[10px] text-[var(--text-faint)]">
          {usage.cacheHitRate > 0.7 ? "缓存效率良好" : "缓存命中率偏低"}
        </p>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="nest-card nest-r-md p-3">
      <div className="flex items-center gap-1.5">
        {icon}
        <span className="text-[10px] text-[var(--text-faint)]">{label}</span>
      </div>
      <p className="mt-1 text-sm font-semibold text-[var(--text-strong)]">{value}</p>
    </div>
  );
}
