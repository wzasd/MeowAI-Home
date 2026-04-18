import { useCallback, useEffect, useState } from "react";
import { GripVertical, X, Play, Pause } from "lucide-react";
import { buildApiUrl } from "../../api/runtimeConfig";

interface QueueEntry {
  id: string;
  content: string;
  targetCats: string[];
  status: "queued" | "processing" | "paused";
  createdAt: string;
}

export function QueuePanel({
  threadId,
  compact = false,
}: {
  threadId: string | null;
  compact?: boolean;
}) {
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const url = threadId
        ? buildApiUrl(`/api/queue/entries?threadId=${threadId}`)
        : buildApiUrl("/api/queue/entries");
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      }
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 3000);
    return () => clearInterval(interval);
  }, [fetchEntries]);

  const remove = async (id: string) => {
    await fetch(buildApiUrl(`/api/queue/entries/${id}`), { method: "DELETE" });
    fetchEntries();
  };

  const togglePause = async (id: string, currentStatus: string) => {
    const action = currentStatus === "paused" ? "resume" : "pause";
    await fetch(buildApiUrl(`/api/queue/entries/${id}/${action}`), { method: "POST" });
    fetchEntries();
  };

  if (loading && entries.length === 0) {
    return <p className="text-sm text-[var(--text-faint)]">加载中...</p>;
  }

  if (entries.length === 0) {
    return <p className="text-sm text-[var(--text-faint)]">队列为空</p>;
  }

  return (
    <div className="space-y-3">
      {!compact && (
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--text-faint)]">
            调用队列
          </h4>
          <span className="nest-chip px-2 py-1 text-[10px] text-[var(--accent)]">
            {entries.length} 条
          </span>
        </div>
      )}

      <div className="space-y-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`nest-card nest-r-md p-2 ${
              entry.status === "processing"
                ? "border-[var(--accent)]/30 bg-[var(--accent-soft)]"
                : ""
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 cursor-grab text-[var(--text-faint)] hover:text-[var(--text-soft)]">
                <GripVertical size={12} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs text-[var(--text-strong)]">{entry.content}</p>
                <div className="mt-1 flex items-center gap-1">
                  {entry.targetCats.map((cat) => (
                    <span
                      key={cat}
                      className="rounded-full border border-[var(--border)] bg-white/50 px-2 py-0.5 text-[10px] text-[var(--moss)] dark:bg-white/5"
                    >
                      @{cat}
                    </span>
                  ))}
                  <span className="text-[10px] text-[var(--text-faint)]">
                    {entry.createdAt.slice(11, 16)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => togglePause(entry.id, entry.status)}
                  className="nest-button-ghost h-7 w-7 rounded-full p-0.5 text-[var(--text-faint)] hover:text-amber-500"
                  title={entry.status === "paused" ? "继续" : "暂停"}
                >
                  {entry.status === "paused" ? <Play size={12} /> : <Pause size={12} />}
                </button>
                <button
                  onClick={() => remove(entry.id)}
                  className="nest-button-ghost h-7 w-7 rounded-full p-0.5 text-[var(--text-faint)] hover:text-red-500"
                  title="移除"
                >
                  <X size={12} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
