import { useState, useEffect, useCallback } from "react";
import { Copy, Check } from "lucide-react";
import { api } from "../../api/client";
import { formatDateTime } from "../../types";

interface SessionInfo {
  session_id: string;
  cat_id: string;
  cat_name: string;
  status: "active" | "sealed";
  created_at: number;
  consecutive_restore_failures: number;
  message_count: number;
  tokens_used: number;
  latency_ms: number;
  turn_count: number;
  cli_command?: string;
  default_model?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  cache_read_tokens?: number;
  cache_creation_tokens?: number;
  budget_max_prompt?: number;
  budget_max_context?: number;
}

function fmtNum(n: number) {
  if (!n && n !== 0) return "-";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

export function SessionChainPanel({ threadId }: { threadId: string | null }) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = async (id: string) => {
    try {
      await navigator.clipboard.writeText(id);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 1500);
    } catch {
      // ignore
    }
  };

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
    const handleSessionCreated = () => loadSessions();
    window.addEventListener("meowai:session_created", handleSessionCreated);
    return () => {
      window.removeEventListener("meowai:session_created", handleSessionCreated);
    };
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
      <div className="flex h-32 items-center justify-center text-sm text-[var(--text-faint)]">
        选择一个线程查看 Session 链
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-[var(--text-faint)]">
        <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--accent)]" />
        加载中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="nest-card nest-r-md border-red-200 bg-red-50/70 p-3 text-sm text-red-600 dark:border-red-900/40 dark:bg-red-950/30">
        {error}
        <button onClick={loadSessions} className="ml-2 text-[var(--accent)] hover:underline">
          重试
        </button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-[var(--text-faint)]">
        暂无 Session 记录
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-[var(--text-faint)]">
        <span>共 {sessions.length} 个 Session</span>
        <button onClick={loadSessions} className="text-[var(--accent)] hover:underline">
          刷新
        </button>
      </div>

      {sessions.map((session, i) => (
        <div
          key={session.session_id}
          className="nest-card nest-r-md relative flex gap-3 p-3 transition-colors hover:border-[var(--border-strong)]"
        >
          <div className="flex flex-col items-center">
            <div
              className={`h-3 w-3 rounded-full ${
                session.status === "active"
                  ? "bg-green-500 ring-2 ring-green-200/40 dark:ring-green-900/40"
                  : "bg-[var(--text-faint)]"
              }`}
            />
            {i < sessions.length - 1 && (
              <div className="mt-1 h-full min-h-[2rem] w-px bg-[var(--line)]" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-[var(--text-strong)]">
                {session.cat_name}
              </span>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  session.status === "active"
                    ? "border border-green-200 bg-green-50 text-green-700 dark:border-green-900/40 dark:bg-green-950/30 dark:text-green-400"
                    : "border border-[var(--border)] bg-white/50 text-[var(--text-soft)] dark:bg-white/5"
                }`}
              >
                {session.status === "active" ? "活跃" : "已密封"}
              </span>
              {session.consecutive_restore_failures > 0 && (
                <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-400">
                  恢复失败 {session.consecutive_restore_failures}/3
                </span>
              )}
            </div>

            <button
              onClick={() => handleCopy(session.session_id)}
              className="mt-1 inline-flex w-full items-center gap-1.5 rounded-md border border-[var(--border)] bg-white/50 px-2 py-1 text-[10px] text-[var(--text-faint)] transition-colors hover:bg-white/80 hover:text-[var(--text-soft)] dark:bg-white/5 dark:hover:bg-white/10"
              title="点击复制 Session ID"
            >
              <span className="truncate font-mono">{session.session_id}</span>
              {copiedId === session.session_id ? (
                <Check size={10} className="shrink-0 text-green-600" />
              ) : (
                <Copy size={10} className="shrink-0" />
              )}
            </button>

            {(session.default_model || session.cli_command) && (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {session.default_model && (
                  <span className="rounded-full border border-[var(--border)] bg-white/40 px-2 py-0.5 text-[10px] text-[var(--text-soft)] dark:bg-white/5">
                    {session.default_model}
                  </span>
                )}
                {session.cli_command && (
                  <span className="rounded-full border border-[var(--border)] bg-white/40 px-2 py-0.5 text-[10px] text-[var(--text-soft)] dark:bg-white/5">
                    CLI: {session.cli_command}
                  </span>
                )}
              </div>
            )}

            <div className="mt-2 grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5">
                <div className="text-[10px] text-[var(--text-faint)]">消息</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{session.message_count}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5">
                <div className="text-[10px] text-[var(--text-faint)]">轮次</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{session.turn_count}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5">
                <div className="text-[10px] text-[var(--text-faint)]">时延</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{session.latency_ms}ms</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5" title={`上传: ${session.prompt_tokens ?? 0}`}>
                <div className="text-[10px] text-[var(--text-faint)]">上传</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{fmtNum(session.prompt_tokens ?? 0)}</div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5" title={`下载: ${session.completion_tokens ?? 0}`}>
                <div className="text-[10px] text-[var(--text-faint)]">下载</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{fmtNum(session.completion_tokens ?? 0)}</div>
              </div>
              <div
                className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5"
                title={`缓存读: ${session.cache_read_tokens ?? 0} / 缓存写: ${session.cache_creation_tokens ?? 0}`}
              >
                <div className="text-[10px] text-[var(--text-faint)]">缓存</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">
                  {fmtNum((session.cache_read_tokens ?? 0) + (session.cache_creation_tokens ?? 0))}
                </div>
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5">
                <div className="text-[10px] text-[var(--text-faint)]">Token</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">{fmtNum(session.tokens_used)}</div>
              </div>
              <div
                className="rounded-lg border border-[var(--border)] bg-white/40 px-2 py-1.5 dark:bg-white/5"
                title={`预算: ${session.budget_max_prompt ?? 0} / ${session.budget_max_context ?? 0}`}
              >
                <div className="text-[10px] text-[var(--text-faint)]">预算</div>
                <div className="text-xs font-medium text-[var(--text-strong)]">
                  {fmtNum(session.budget_max_prompt ?? 0)} / {fmtNum(session.budget_max_context ?? 0)}
                </div>
              </div>
            </div>

            <p className="mt-2 text-[11px] text-[var(--text-faint)]">
              {formatDateTime(new Date(session.created_at * 1000).toISOString())}
            </p>

            <div className="mt-2 flex items-center gap-2">
              {session.status === "active" ? (
                <button
                  onClick={() => handleSeal(session.session_id)}
                  disabled={actionLoading === session.session_id}
                  className="nest-button-secondary px-2 py-1 text-[11px] disabled:opacity-50"
                >
                  {actionLoading === session.session_id ? (
                    <>
                      <div className="mr-1 h-3 w-3 animate-spin rounded-full border border-[var(--border)] border-t-[var(--accent)]" />
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
                  className="nest-button-primary bg-green-600 px-2 py-1 text-[11px] hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === session.session_id ? (
                    <>
                      <div className="mr-1 h-3 w-3 animate-spin rounded-full border border-green-200 border-t-green-500" />
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
