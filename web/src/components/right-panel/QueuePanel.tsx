import { useState, useEffect } from "react";
import { GripVertical, X, Play, Pause } from "lucide-react";

interface QueueEntry {
  id: string;
  content: string;
  targetCats: string[];
  status: "queued" | "processing" | "paused";
  createdAt: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function QueuePanel({ threadId }: { threadId: string | null }) {
  const [entries, setEntries] = useState<QueueEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchEntries = async () => {
    setLoading(true);
    try {
      const url = threadId
        ? `${API_BASE}/api/queue/entries?threadId=${threadId}`
        : `${API_BASE}/api/queue/entries`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
    const interval = setInterval(fetchEntries, 3000);
    return () => clearInterval(interval);
  }, [threadId]);

  const remove = async (id: string) => {
    await fetch(`${API_BASE}/api/queue/entries/${id}`, { method: "DELETE" });
    fetchEntries();
  };

  const togglePause = async (id: string, currentStatus: string) => {
    const action = currentStatus === "paused" ? "resume" : "pause";
    await fetch(`${API_BASE}/api/queue/entries/${id}/${action}`, { method: "POST" });
    fetchEntries();
  };

  if (loading && entries.length === 0) {
    return <p className="text-sm text-gray-400">加载中...</p>;
  }

  if (entries.length === 0) {
    return <p className="text-sm text-gray-400">队列为空</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">调用队列</h4>
        <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
          {entries.length} 条
        </span>
      </div>

      <div className="space-y-2">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`rounded-lg border p-2 ${
              entry.status === "processing"
                ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
                : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
            }`}
          >
            <div className="flex items-start gap-2">
              <div className="mt-0.5 cursor-grab text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <GripVertical size={12} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs text-gray-800 dark:text-gray-200">{entry.content}</p>
                <div className="mt-1 flex items-center gap-1">
                  {entry.targetCats.map((cat) => (
                    <span
                      key={cat}
                      className="rounded bg-purple-50 px-1 py-0.5 text-[10px] text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
                    >
                      @{cat}
                    </span>
                  ))}
                  <span className="text-[10px] text-gray-400">{entry.createdAt.slice(11, 16)}</span>
                </div>
              </div>
              <div className="flex items-center gap-0.5">
                <button
                  onClick={() => togglePause(entry.id, entry.status)}
                  className="rounded p-0.5 text-gray-400 hover:text-amber-500"
                  title={entry.status === "paused" ? "继续" : "暂停"}
                >
                  {entry.status === "paused" ? <Play size={12} /> : <Pause size={12} />}
                </button>
                <button
                  onClick={() => remove(entry.id)}
                  className="rounded p-0.5 text-gray-400 hover:text-red-500"
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
