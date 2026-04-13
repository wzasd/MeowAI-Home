import { useState, useEffect, useCallback } from "react";
import { api } from "../../api/client";
import { formatDateTime } from "../../types";

interface SessionInfo {
  session_id: string;
  cat_id: string;
  cat_name: string;
  status: "active" | "sealed";
  created_at: number;
  consecutive_restore_failures: number;
}

export function SessionChainPanel({ threadId }: { threadId: string | null }) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    if (!threadId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.threads.sessions(threadId);
      setSessions(data);
    } catch (err) {
      setError("加载失败");
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleSeal = async (sessionId: string) => {
    setActionLoading(sessionId);
    try {
      await api.sessions.seal(sessionId);
      await loadSessions();
    } catch (err) {
      setError("密封失败");
    } finally {
      setActionLoading(null);
    }
  };

  const handleUnseal = async (sessionId: string) => {
    setActionLoading(sessionId);
    try {
      await api.sessions.unseal(sessionId);
      await loadSessions();
    } catch (err) {
      setError("解封失败");
    } finally {
      setActionLoading(null);
    }
  };

  if (!threadId) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-gray-400">
        选择一个线程查看 Session 链
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-gray-400">
        <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
        {error}
        <button
          onClick={loadSessions}
          className="ml-2 text-blue-600 hover:underline dark:text-blue-400"
        >
          重试
        </button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-gray-400">
        暂无 Session 记录
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>共 {sessions.length} 个 Session</span>
        <button
          onClick={loadSessions}
          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
        >
          刷新
        </button>
      </div>

      {sessions.map((session, i) => (
        <div
          key={session.session_id}
          className="relative flex gap-3 rounded-lg border border-gray-200 p-3 transition-colors hover:border-gray-300 dark:border-gray-700 dark:hover:border-gray-600"
        >
          {/* Timeline connector */}
          <div className="flex flex-col items-center">
            <div
              className={`h-3 w-3 rounded-full ${
                session.status === "active"
                  ? "bg-green-500 ring-2 ring-green-200 dark:ring-green-900/30"
                  : "bg-gray-400"
              }`}
            />
            {i < sessions.length - 1 && (
              <div className="mt-1 h-full min-h-[2rem] w-px bg-gray-300 dark:bg-gray-600" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                {session.cat_name}
              </span>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  session.status === "active"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                }`}
              >
                {session.status === "active" ? "活跃" : "已密封"}
              </span>
              {session.consecutive_restore_failures > 0 && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  恢复失败 {session.consecutive_restore_failures}/3
                </span>
              )}
            </div>

            <p className="mt-1 text-[11px] text-gray-400">
              {formatDateTime(new Date(session.created_at * 1000).toISOString())}
            </p>

            {/* Actions */}
            <div className="mt-2 flex items-center gap-2">
              {session.status === "active" ? (
                <button
                  onClick={() => handleSeal(session.session_id)}
                  disabled={actionLoading === session.session_id}
                  className="inline-flex items-center rounded-md border border-gray-300 bg-white px-2 py-1 text-[11px] font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                  {actionLoading === session.session_id ? (
                    <>
                      <div className="mr-1 h-3 w-3 animate-spin rounded-full border border-gray-300 border-t-blue-500" />
                      处理中...
                    </>
                  ) : (
                    "密封"
                  )}
                </button>
              ) : (
                <button
                  onClick={() => handleUnseal(session.session_id)}
                  disabled={actionLoading === session.session_id}
                  className="inline-flex items-center rounded-md border border-green-300 bg-green-50 px-2 py-1 text-[11px] font-medium text-green-700 transition-colors hover:bg-green-100 disabled:opacity-50 dark:border-green-700 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/30"
                >
                  {actionLoading === session.session_id ? (
                    <>
                      <div className="mr-1 h-3 w-3 animate-spin rounded-full border border-green-300 border-t-green-500" />
                      处理中...
                    </>
                  ) : (
                    "解封"
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
