import { useState } from "react";
import { X } from "lucide-react";
import { SessionChainPanel } from "./SessionChainPanel";
import { TaskPanel } from "./TaskPanel";
import { TokenUsagePanel } from "./TokenUsagePanel";
import { QueuePanel } from "./QueuePanel";
import { AuditPanel } from "../audit/AuditPanel";
import { BrakeSystem } from "../brake/BrakeSystem";

const TABS = [
  { key: "status", label: "状态" },
  { key: "tokens", label: "用量" },
  { key: "sessions", label: "会话" },
  { key: "tasks", label: "任务" },
  { key: "queue", label: "队列" },
  { key: "audit", label: "审计" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

interface RightStatusPanelProps {
  threadId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function RightStatusPanel({ threadId, isOpen, onClose }: RightStatusPanelProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("status");
  const width = 320;

  if (!isOpen) return null;

  return (
    <div
      className="flex h-full shrink-0 flex-col overflow-hidden border-l border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
      style={{ width }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-gray-200 px-2 py-2 dark:border-gray-700">
        <div className="flex flex-1 gap-0.5">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 rounded px-1 py-1 text-[11px] font-medium transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
        >
          <X size={14} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === "status" && (
          <>
            <StatusOverview threadId={threadId} />
            <div className="mt-4">
              <BrakeSystem />
            </div>
          </>
        )}
        {activeTab === "tokens" && <TokenUsagePanel threadId={threadId} />}
        {activeTab === "sessions" && <SessionChainPanel threadId={threadId} />}
        {activeTab === "tasks" && <TaskPanel threadId={threadId} />}
        {activeTab === "queue" && <QueuePanel threadId={threadId} />}
        {activeTab === "audit" && <AuditPanel />}
      </div>

    </div>
  );
}

function StatusOverview({ threadId }: { threadId: string | null }) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
        <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">线程状态</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">Thread ID</span>
            <span className="font-mono text-xs text-gray-800 dark:text-gray-200">{threadId?.slice(0, 8) || "—"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600 dark:text-gray-400">WebSocket</span>
            <span className="text-xs text-green-600">已连接</span>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
        <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">活跃猫咪</h4>
        <div className="flex flex-wrap gap-1">
          <span className="rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">阿橘</span>
          <span className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">墨点</span>
          <span className="rounded bg-pink-100 px-2 py-0.5 text-xs text-pink-700 dark:bg-pink-900/30 dark:text-pink-400">花花</span>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
        <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">上下文健康</h4>
        <div className="space-y-2">
          <ContextHealthBar label="上下文窗口" used={45000} total={128000} />
          <ContextHealthBar label="消息数" used={12} total={100} />
        </div>
      </div>
    </div>
  );
}

export function ContextHealthBar({ label, used, total }: { label: string; used: number; total: number }) {
  const pct = Math.min(100, (used / total) * 100);
  const color = pct > 90 ? "bg-red-500" : pct > 70 ? "bg-amber-500" : "bg-green-500";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="text-gray-500 dark:text-gray-400">
          {(used / 1000).toFixed(1)}k / {(total / 1000).toFixed(0)}k
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
