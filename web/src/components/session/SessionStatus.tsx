import { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Loader2, Circle, CheckCircle2, Lock, Clock } from "lucide-react";

interface Session {
  session_id: string;
  cat_id: string;
  cat_name: string;
  status: "active" | "sealing" | "sealed";
  created_at: number;
  seal_started_at?: number;
}

interface SessionStatusProps {
  threadId: string;
}

export function SessionStatus({ threadId }: SessionStatusProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    fetchSessions();
    // Poll every 5 seconds for active sessions
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, [threadId]);

  const fetchSessions = async () => {
    try {
      const data = await api.threads.sessions(threadId);
      setSessions(data);
      setError(null);
    } catch (err) {
      setError("获取 Session 状态失败");
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <Circle size={12} className="fill-green-500 text-green-500" />;
      case "sealing":
        return <Loader2 size={12} className="animate-spin text-amber-500" />;
      case "sealed":
        return <Lock size={12} className="text-gray-400" />;
      default:
        return <Circle size={12} className="text-gray-400" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "active":
        return "活跃";
      case "sealing":
        return "归档中";
      case "sealed":
        return "已归档";
      default:
        return status;
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case "active":
        return "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400";
      case "sealing":
        return "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400";
      case "sealed":
        return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
      default:
        return "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
    }
  };

  const formatDuration = (createdAt: number) => {
    const duration = Date.now() / 1000 - createdAt;
    if (duration < 60) return "刚刚";
    if (duration < 3600) return `${Math.floor(duration / 60)} 分钟`;
    if (duration < 86400) return `${Math.floor(duration / 3600)} 小时`;
    return `${Math.floor(duration / 86400)} 天`;
  };

  const activeSessions = sessions.filter((s) => s.status === "active");
  const hasActiveSession = activeSessions.length > 0;

  if (loading && sessions.length === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <Loader2 size={12} className="animate-spin" />
        <span>加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-xs text-red-500" title={error}>
        Session 错误
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex items-center gap-1 text-xs text-gray-400">
        <CheckCircle2 size={12} />
        <span>无活跃 Session</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 rounded-full px-2 py-1 text-xs transition-colors hover:bg-gray-100 dark:hover:bg-gray-700"
      >
        {hasActiveSession ? (
          <>
            <Circle size={10} className="fill-green-500 text-green-500" />
            <span className="text-green-700 dark:text-green-400">
              {activeSessions.length} 个活跃 Session
            </span>
          </>
        ) : (
          <>
            <Lock size={10} className="text-gray-400" />
            <span className="text-gray-500">{sessions.length} 个 Session</span>
          </>
        )}
      </button>

      {expanded && (
        <div className="absolute right-0 top-8 z-20 w-64 rounded-lg border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-600 dark:bg-gray-800">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Session 状态
            </span>
            <button
              onClick={() => setExpanded(false)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              ×
            </button>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto">
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className="flex items-center justify-between rounded border border-gray-100 p-2 dark:border-gray-700"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-xs font-medium text-gray-700 dark:text-gray-300">
                      {session.cat_name}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1 text-[10px] text-gray-400">
                    <Clock size={10} />
                    <span>{formatDuration(session.created_at)}</span>
                  </div>
                </div>
                <span
                  className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${getStatusClass(
                    session.status
                  )}`}
                >
                  {getStatusIcon(session.status)}
                  {getStatusLabel(session.status)}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-2 border-t border-gray-100 pt-2 text-[10px] text-gray-400 dark:border-gray-700">
            自动刷新 · 5秒
          </div>
        </div>
      )}
    </div>
  );
}
