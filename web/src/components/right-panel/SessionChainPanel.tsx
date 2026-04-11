import { useState, useEffect } from "react";
import { api } from "../../api/client";
import { formatDateTime } from "../../types";

interface SessionInfo {
  session_id: string;
  cat_id: string;
  cat_name: string;
  status: "active" | "sealing" | "sealed";
  created_at: number;
  seal_started_at?: number;
}

export function SessionChainPanel({ threadId }: { threadId: string | null }) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!threadId) return;
    setLoading(true);
    api.threads.sessions(threadId)
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }, [threadId]);

  if (!threadId) {
    return <p className="text-sm text-gray-400">选择一个线程查看 Session 链</p>;
  }

  if (loading) {
    return <p className="text-sm text-gray-400">加载中...</p>;
  }

  if (sessions.length === 0) {
    return <p className="text-sm text-gray-400">暂无 Session 记录</p>;
  }

  return (
    <div className="space-y-2">
      {sessions.map((session, i) => (
        <div
          key={session.session_id}
          className="flex items-center gap-2 rounded-lg border border-gray-200 p-2 dark:border-gray-700"
        >
          <div className="flex flex-col items-center">
            <div
              className={`h-3 w-3 rounded-full ${
                session.status === "active"
                  ? "bg-green-500"
                  : session.status === "sealing"
                    ? "bg-amber-500"
                    : "bg-gray-400"
              }`}
            />
            {i < sessions.length - 1 && <div className="h-4 w-px bg-gray-300 dark:bg-gray-600" />}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1">
              <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
                {session.cat_name || session.cat_id}
              </span>
              <span
                className={`rounded px-1 py-0.5 text-[10px] ${
                  session.status === "active"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : session.status === "sealing"
                      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                }`}
              >
                {session.status}
              </span>
            </div>
            <p className="text-[10px] text-gray-400">
              {formatDateTime(new Date(session.created_at * 1000).toISOString())}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
