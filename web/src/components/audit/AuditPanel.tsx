/** Audit log panel for tracking agent actions */

import { useState, useEffect } from "react";
import { Shield, AlertTriangle, FileText, Terminal, Filter, Loader2 } from "lucide-react";

interface AuditEntry {
  id: string;
  timestamp: string;
  level: "info" | "warning" | "error" | "critical";
  category: "file" | "command" | "network" | "auth" | "system";
  actor: string;
  action: string;
  details: string;
  threadId?: string;
}

const LEVEL_COLORS = {
  info: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  critical: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 animate-pulse",
};

const CATEGORY_ICONS = {
  file: FileText,
  command: Terminal,
  network: Shield,
  auth: Shield,
  system: AlertTriangle,
};

export function AuditPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | AuditEntry["category"]>("all");
  const [levelFilter, setLevelFilter] = useState<"all" | AuditEntry["level"]>("all");

  const fetchEntries = async () => {
    try {
      const params = new URLSearchParams();
      if (filter !== "all") params.append("category", filter);
      if (levelFilter !== "all") params.append("level", levelFilter);
      params.append("limit", "100");

      const response = await fetch(`/api/audit/entries?${params.toString()}`);
      if (response.ok) {
        const data = await response.json();
        setEntries(data);
      }
    } catch (error) {
      console.error("Failed to fetch audit entries:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEntries();
  }, [filter, levelFilter]);

  useEffect(() => {
    const interval = setInterval(fetchEntries, 10000);
    return () => clearInterval(interval);
  }, [filter, levelFilter]);

  const filtered = entries.filter((e) => {
    if (filter !== "all" && e.category !== filter) return false;
    if (levelFilter !== "all" && e.level !== levelFilter) return false;
    return true;
  });

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--line)] px-3 py-3">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-[var(--text-faint)]" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="nest-field nest-r-sm px-2 py-1.5 text-xs"
          >
            <option value="all">全部类别</option>
            <option value="file">文件</option>
            <option value="command">命令</option>
            <option value="network">网络</option>
            <option value="auth">认证</option>
            <option value="system">系统</option>
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value as any)}
            className="nest-field nest-r-sm px-2 py-1.5 text-xs"
          >
            <option value="all">全部级别</option>
            <option value="info">信息</option>
            <option value="warning">警告</option>
            <option value="error">错误</option>
            <option value="critical">严重</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 size={24} className="animate-spin text-[var(--text-faint)]" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-[var(--text-faint)]">
            暂无审计日志
          </div>
        ) : (
          filtered.map((entry) => {
            const Icon = CATEGORY_ICONS[entry.category];
            return (
              <div
                key={entry.id}
                className="nest-card nest-r-md mb-2 p-3"
              >
                <div className="flex items-start gap-2">
                  <Icon size={14} className="mt-0.5 text-[var(--text-faint)]" />
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${LEVEL_COLORS[entry.level]}`}>
                        {entry.level.toUpperCase()}
                      </span>
                      <span className="text-[10px] text-[var(--text-faint)]">{entry.timestamp}</span>
                      <span className="rounded-full border border-[var(--border)] px-2 py-0.5 text-[10px] text-[var(--text-soft)]">
                        @{entry.actor}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-[var(--text-strong)]">
                      <span className="font-mono text-[var(--text-faint)]">{entry.action}</span>
                      <span className="mx-1 text-[var(--line)]">·</span>
                      {entry.details}
                    </p>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
