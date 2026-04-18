import { useEffect, useState } from "react";
import {
  Activity,
  Archive,
  ChevronDown,
  ChevronRight,
  LoaderCircle,
  RefreshCcw,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { api, type QueueEntry, type TokenUsageSnapshot } from "../../api/client";
import { useCatStore } from "../../stores/catStore";
import { useChatStore } from "../../stores/chatStore";
import { AuditPanel } from "../audit/AuditPanel";
import { BrakeSystem } from "../brake/BrakeSystem";
import { RIGHT_PANEL_TABS, type RightPanelTabKey } from "./panelLayout";
import { getRightPanelSubtitle } from "./rightPanelModel";
import {
  buildStatusOverviewModel,
  filterWorkingCatCards,
  formatCompactNumber,
  pickFocusCatId,
  type StatusCatCard,
  type StatusOverviewTask,
} from "./statusOverviewModel";
import { TaskPanel } from "./TaskPanel";
import { MetricsPanel } from "./MetricsPanel";
import { SlidingNav } from "../ui/SlidingNav";

interface RightStatusPanelProps {
  threadId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

interface OverviewRemoteData {
  sessions: Awaited<ReturnType<typeof api.threads.sessions>>;
  tasks: StatusOverviewTask[];
  queueEntries: QueueEntry[];
  usage: TokenUsageSnapshot | null;
}

const EMPTY_REMOTE_DATA: OverviewRemoteData = {
  sessions: [],
  tasks: [],
  queueEntries: [],
  usage: null,
};

export function RightStatusPanel({ threadId, isOpen, onClose }: RightStatusPanelProps) {
  const [activeTab, setActiveTab] = useState<RightPanelTabKey>("status");
  const width = 280;

  if (!isOpen) return null;

  return (
    <div
      className="nest-panel-strong nest-r-xl flex h-full shrink-0 flex-col overflow-hidden"
      style={{ width }}
    >
      <div className="border-b border-[var(--line)] px-3 py-3">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <Activity size={13} className="shrink-0 text-[var(--accent)]" />
              <span className="truncate text-sm font-semibold text-[var(--text-strong)]">
                状态台
              </span>
            </div>
            <p className="mt-1 truncate text-[10px] text-[var(--text-faint)]">
              {getRightPanelSubtitle(activeTab, threadId)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="nest-button-ghost flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          >
            <X size={14} />
          </button>
        </div>

        <SlidingNav
          items={RIGHT_PANEL_TABS.map((tab) => ({ key: tab.key, label: tab.label }))}
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as RightPanelTabKey)}
          className="nest-nav-strip-compact"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {activeTab === "status" && <StatusOverview threadId={threadId} />}
        {activeTab === "tasks" && <TaskPanel threadId={threadId} />}
        {activeTab === "metrics" && <MetricsPanel />}
        {activeTab === "audit" && (
          <>
            <BrakeSystem />
            <div className="mt-3">
              <AuditPanel />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatusOverview({ threadId }: { threadId: string | null }) {
  const cats = useCatStore((state) => state.cats);
  const fetchCats = useCatStore((state) => state.fetchCats);
  const wsConnected = useChatStore((state) => state.wsConnected);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const streamingStatuses = useChatStore((state) => state.streamingStatuses);
  const streamingResponses = useChatStore((state) => state.streamingResponses);
  const streamingThinking = useChatStore((state) => state.streamingThinking);
  const targetCats = useChatStore((state) => state.targetCats);

  const [remote, setRemote] = useState<OverviewRemoteData>(EMPTY_REMOTE_DATA);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualExpandedCatId, setManualExpandedCatId] = useState<string | null>(null);
  const [dismissedAutoCatId, setDismissedAutoCatId] = useState<string | null>(null);
  const [showRuntimeDetails, setShowRuntimeDetails] = useState(false);

  useEffect(() => {
    setManualExpandedCatId(null);
    setDismissedAutoCatId(null);
    setShowRuntimeDetails(false);
  }, [threadId]);

  useEffect(() => {
    if (cats.length === 0) {
      void fetchCats();
    }
  }, [cats.length, fetchCats]);

  useEffect(() => {
    if (!threadId) {
      setRemote(EMPTY_REMOTE_DATA);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadOverview = async (showSpinner: boolean) => {
      if (showSpinner) setLoading(true);
      try {
        const [sessions, threadTasks, allMissionTasks, queueEntries, usage] = await Promise.all([
          api.threads.sessions(threadId),
          api.tasks.entries(threadId),
          api.missions.listTasks(),
          api.queue.entries(threadId),
          api.metrics.tokenUsage(threadId),
        ]);

        const missionTasks = allMissionTasks.tasks.filter((task) =>
          task.thread_ids?.includes(threadId)
        );

        // Merge tasks from both thread_tasks and missions sources
        const taskMap = new Map<string, StatusOverviewTask>();
        for (const task of threadTasks) {
          taskMap.set(task.id, {
            id: task.id,
            title: task.title,
            status: task.status,
            ownerCat: task.ownerCat,
            createdAt: task.createdAt,
          });
        }
        for (const task of missionTasks) {
          taskMap.set(task.id, {
            id: task.id,
            title: task.title,
            status: task.status,
            ownerCat: task.ownerCat,
            createdAt: task.createdAt,
          });
        }
        const tasks = Array.from(taskMap.values());

        if (cancelled) return;
        setRemote({ sessions, tasks, queueEntries, usage });
        setError(null);
      } catch {
        if (cancelled) return;
        setError("状态数据刷新失败，当前先展示本地运行态。");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void loadOverview(true);

    const intervalId = window.setInterval(() => {
      void loadOverview(false);
    }, 5000);

    const refreshNow = () => {
      void loadOverview(false);
    };

    window.addEventListener("meowai:session_created", refreshNow);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
      window.removeEventListener("meowai:session_created", refreshNow);
    };
  }, [threadId]);

  const model = buildStatusOverviewModel({
    threadId,
    cats,
    sessions: remote.sessions,
    tasks: remote.tasks,
    messages: [],
    queueEntries: remote.queueEntries,
    usage: remote.usage,
    streaming: {
      wsConnected,
      isStreaming,
      targetCats,
      statuses: streamingStatuses,
      thinking: streamingThinking,
      responses: streamingResponses,
    },
  });

  const workingCatCards = filterWorkingCatCards(model.catCards);
  const alertLine = model.alerts.map((alert) => alert.label).join(" · ");
  const autoExpandedCatId = pickFocusCatId(workingCatCards);
  const expandedCatId =
    manualExpandedCatId ?? (dismissedAutoCatId === autoExpandedCatId ? null : autoExpandedCatId);

  return (
    <div className="space-y-2.5">
      <div className="nest-card nest-r-lg px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                wsConnected ? "bg-emerald-500" : "bg-red-500"
              }`}
            />
            <span className="truncate text-[11px] font-medium text-[var(--text-strong)]">
              {model.header.compactLine}
            </span>
          </div>

          <div className="shrink-0 text-[var(--text-faint)]">
            {loading ? (
              <RefreshCcw size={12} className="animate-spin" />
            ) : wsConnected ? (
              <Wifi size={12} />
            ) : (
              <WifiOff size={12} />
            )}
          </div>
        </div>

        <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-2">
          {model.overviewFacts.map((fact) => (
            <OverviewFact
              key={fact.label}
              label={fact.label}
              value={fact.value}
              detail={fact.detail}
            />
          ))}
        </div>

        <p className="mt-1.5 text-[10px] text-[var(--text-soft)]">{model.header.executionLine}</p>

        {alertLine && <p className="mt-1.5 text-[10px] text-[var(--danger)]">告警 · {alertLine}</p>}

        {error && <p className="mt-1.5 text-[10px] text-amber-700 dark:text-amber-300">{error}</p>}
      </div>

      <div className="space-y-1.5">
        {workingCatCards.length > 0 ? (
          workingCatCards.map((card) => (
            <RosterCard
              key={card.id}
              card={card}
              expanded={expandedCatId === card.id}
              onToggle={() => {
                if (expandedCatId === card.id) {
                  setManualExpandedCatId(null);
                  if (autoExpandedCatId === card.id) {
                    setDismissedAutoCatId(card.id);
                  }
                  return;
                }

                setManualExpandedCatId(card.id);
                setDismissedAutoCatId(null);
              }}
            />
          ))
        ) : (
          <div className="nest-card nest-r-md px-3 py-4 text-sm text-[var(--text-faint)]">
            当前没有正在工作的猫咪。
          </div>
        )}
      </div>

      {model.recentlyCompletedCards.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] font-medium text-[var(--text-faint)]">最近完成</div>
          {model.recentlyCompletedCards.map((card) => (
            <RosterCard
              key={card.id}
              card={card}
              expanded={expandedCatId === card.id}
              onToggle={() => {
                if (expandedCatId === card.id) {
                  setManualExpandedCatId(null);
                  if (autoExpandedCatId === card.id) {
                    setDismissedAutoCatId(card.id);
                  }
                  return;
                }
                setManualExpandedCatId(card.id);
                setDismissedAutoCatId(null);
              }}
            />
          ))}
        </div>
      )}

      <div className="nest-card nest-r-lg px-3 py-2.5">
        <button
          type="button"
          onClick={() => setShowRuntimeDetails((current) => !current)}
          className="flex w-full items-center justify-between gap-3 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-[var(--text-strong)]">运行细节</div>
            <div className="text-[10px] text-[var(--text-faint)]">
              当前工作卡 / 队列节拍 / 上下文压力
            </div>
          </div>
          {showRuntimeDetails ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>

        {showRuntimeDetails && (
          <div className="mt-3 border-t border-[var(--line)] pt-3">
            <RuntimePanel
              threadId={threadId}
              cards={workingCatCards}
              queueEntries={remote.queueEntries}
              queueSummary={model.queueSummary}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function RuntimePanel({
  threadId,
  cards,
  queueEntries,
  queueSummary,
}: {
  threadId: string | null;
  cards: StatusCatCard[];
  queueEntries: QueueEntry[];
  queueSummary: {
    queued: number;
    processing: number;
    paused: number;
  };
}) {
  const spotlightEntries = [...queueEntries]
    .sort((left, right) => {
      const rank = (value: QueueEntry["status"]) => {
        switch (value) {
          case "processing":
            return 3;
          case "queued":
            return 2;
          case "paused":
            return 1;
        }
      };

      return rank(right.status) - rank(left.status);
    })
    .slice(0, 3);

  if (cards.length === 0 && spotlightEntries.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-[var(--line)] px-3 py-4 text-[11px] text-[var(--text-faint)]">
        {threadId
          ? "当前 thread 暂时没有执行中的猫咪，也没有排队请求。开始工作后，这里会显示任务优先的运行卡。"
          : "未选 thread 时只在这里展示正在工作的猫咪和活跃队列。"}
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {cards.length > 0 && (
        <div className="space-y-2">
          {cards.map((card) => (
            <RuntimeFocusCard key={card.id} card={card} />
          ))}
        </div>
      )}

      <div className="nest-card nest-r-lg border-[var(--border-strong)]/35 border px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] font-medium text-[var(--text-strong)]">队列节拍</div>
            <div className="text-[10px] text-[var(--text-faint)]">
              把请求堆积收成一张卡，不再单独占一个面板。
            </div>
          </div>

          <div className="shrink-0 text-right text-[10px] text-[var(--text-faint)]">
            {queueSummary.processing + queueSummary.queued + queueSummary.paused} 条
          </div>
        </div>

        <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
          <RuntimeCell label="进行中" value={`${queueSummary.processing}`} />
          <RuntimeCell label="排队" value={`${queueSummary.queued}`} />
          <RuntimeCell label="暂停" value={`${queueSummary.paused}`} />
        </div>

        {spotlightEntries.length > 0 ? (
          <div className="mt-3 space-y-2 border-t border-[var(--line)] pt-3">
            {spotlightEntries.map((entry) => (
              <div key={entry.id} className="rounded-2xl bg-white/45 px-2.5 py-2 dark:bg-white/5">
                <div className="flex items-center justify-between gap-2 text-[10px]">
                  <span className="font-medium text-[var(--text-strong)]">
                    {entry.status === "processing"
                      ? "处理中"
                      : entry.status === "queued"
                        ? "等待中"
                        : "已暂停"}
                  </span>
                  <span className="truncate text-[var(--text-faint)]">
                    {entry.targetCats.length > 0 ? entry.targetCats.join(" · ") : "未指定对象"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-[11px] text-[var(--text-soft)]">
                  {entry.content}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 border-t border-[var(--line)] pt-3 text-[11px] text-[var(--text-faint)]">
            当前没有额外排队请求。
          </p>
        )}
      </div>
    </div>
  );
}

function RuntimeFocusCard({ card }: { card: StatusCatCard }) {
  const [archiving, setArchiving] = useState(false);
  const [archiveNote, setArchiveNote] = useState<string | null>(null);

  const toneClass =
    card.tone === "active"
      ? "border-[var(--accent)]/35 bg-[linear-gradient(145deg,rgba(183,103,37,0.14),rgba(255,255,255,0.5))] dark:bg-[linear-gradient(145deg,rgba(230,162,93,0.14),rgba(255,255,255,0.04))]"
      : card.tone === "focus"
        ? "border-amber-200/80 bg-amber-50/70 dark:border-amber-900/45 dark:bg-amber-950/16"
        : card.tone === "blocked"
          ? "border-red-200/80 bg-red-50/70 dark:border-red-900/45 dark:bg-red-950/16"
          : "border-sky-200/80 bg-sky-50/70 dark:border-sky-900/45 dark:bg-sky-950/16";

  const toneLabel =
    card.tone === "active"
      ? "执行中"
      : card.tone === "focus"
        ? "推进中"
        : card.tone === "blocked"
          ? "阻塞"
          : "预热中";

  const handleArchive = async () => {
    if (!card.sessionId || archiving) return;

    setArchiving(true);
    setArchiveNote(null);
    try {
      await api.sessions.seal(card.sessionId);
      setArchiveNote("会话已归档，下一轮刷新后会从当前工作区退场。");
      window.dispatchEvent(new CustomEvent("meowai:session_created"));
    } catch {
      setArchiveNote("归档失败，请稍后重试。");
    } finally {
      setArchiving(false);
    }
  };

  return (
    <div className={`nest-card nest-r-lg border px-3 py-3 ${toneClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: card.color }}
            />
            <span className="truncate text-sm font-semibold text-[var(--text-strong)]">
              {card.name}
            </span>
            <span className="text-[10px] font-medium text-[var(--text-faint)]">{toneLabel}</span>
          </div>

          <p className="mt-1 text-[13px] font-medium leading-5 text-[var(--text-strong)]">
            {card.status}
          </p>

          <div className="mt-2 space-y-1.5 rounded-2xl bg-white/45 px-2.5 py-2.5 text-[11px] dark:bg-black/10">
            <WorkStateLine label="工作中" value={card.taskLabel} />
            <WorkStateLine label="已完成" value={card.taskStatusLine ?? "暂无完成记录"} subtle />
          </div>
        </div>

        {card.sessionId && (
          <button
            type="button"
            onClick={() => void handleArchive()}
            disabled={archiving}
            className="hover:border-[var(--accent)]/35 inline-flex shrink-0 items-center gap-1 rounded-full border border-[var(--line)] bg-white/65 px-2 py-1 text-[10px] font-medium text-[var(--text-soft)] transition hover:text-[var(--text-strong)] disabled:cursor-wait disabled:opacity-70 dark:bg-white/5"
          >
            {archiving ? (
              <LoaderCircle size={11} className="animate-spin" />
            ) : (
              <Archive size={11} />
            )}
            {archiving ? "归档中" : "归档"}
          </button>
        )}
      </div>

      <div className="mt-2 rounded-2xl bg-white/45 px-2.5 py-2 text-[10px] text-[var(--text-faint)] dark:bg-black/10">
        <span className="font-medium text-[var(--text-soft)]">
          {card.sessionShort ? `会话 ${card.sessionShort}` : "会话待建立"}
        </span>
        {card.modelLabel ? ` · ${card.modelLabel}` : ""}
        {card.cliLabel ? ` · ${card.cliLabel}` : ""}
      </div>

      {card.contextLabel && (
        <div className="mt-3">
          <div className="flex items-center justify-between gap-2 text-[10px] text-[var(--text-faint)]">
            <span>上下文压力</span>
            <span>{card.contextLabel}</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
            <div
              className={`h-full rounded-full ${
                (card.contextPct ?? 0) >= 80 ? "bg-amber-500" : "bg-[var(--accent)]"
              }`}
              style={{ width: `${Math.max(0, Math.min(100, card.contextPct ?? 0))}%` }}
            />
          </div>
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-[var(--text-faint)]">
        <RuntimeInlineMetric label="上行" value={formatCompactNumber(card.promptTokens)} />
        <RuntimeInlineMetric label="下行" value={formatCompactNumber(card.completionTokens)} />
        <RuntimeInlineMetric label="缓存" value={formatCompactNumber(card.cacheTokens)} />
        {card.latencyLabel && <RuntimeInlineMetric label="时延" value={card.latencyLabel} />}
      </div>

      {archiveNote && <p className="mt-2 text-[10px] text-[var(--text-faint)]">{archiveNote}</p>}
    </div>
  );
}

function RosterCard({
  card,
  expanded,
  onToggle,
}: {
  card: StatusCatCard;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasRuntime =
    !!card.contextLabel ||
    card.promptTokens > 0 ||
    card.completionTokens > 0 ||
    card.cacheTokens > 0 ||
    !!card.latencyLabel;

  const toneClass =
    card.tone === "active"
      ? "border-[var(--accent)]/30 bg-[linear-gradient(135deg,rgba(183,103,37,0.12),rgba(255,255,255,0.35))] dark:bg-[linear-gradient(135deg,rgba(230,162,93,0.12),rgba(255,255,255,0.04))]"
      : card.tone === "focus"
        ? "border-amber-200/70 bg-amber-50/55 dark:border-amber-900/40 dark:bg-amber-950/18"
        : card.tone === "blocked"
          ? "border-red-200/70 bg-red-50/55 dark:border-red-900/40 dark:bg-red-950/18"
          : card.tone === "warming"
            ? "border-sky-200/70 bg-sky-50/55 dark:border-sky-900/40 dark:bg-sky-950/18"
            : card.tone === "completed"
              ? "border-emerald-200/70 bg-emerald-50/55 dark:border-emerald-900/40 dark:bg-emerald-950/18"
              : "border-[var(--border)] bg-white/30 dark:bg-white/5";

  const pillClass =
    card.tone === "active"
      ? "bg-[var(--accent-soft)] text-[var(--accent-deep)]"
      : card.tone === "focus"
        ? "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"
        : card.tone === "blocked"
          ? "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300"
          : card.tone === "warming"
            ? "bg-sky-100 text-sky-700 dark:bg-sky-950/30 dark:text-sky-300"
            : card.tone === "completed"
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
              : "bg-white/60 text-[var(--text-faint)] dark:bg-white/10";

  const toneLabel =
    card.tone === "active"
      ? "执行中"
      : card.tone === "focus"
        ? "推进中"
        : card.tone === "blocked"
          ? "阻塞"
          : card.tone === "warming"
            ? "预热"
            : card.tone === "completed"
              ? "已完成"
              : card.tone === "ready"
                ? "就绪"
                : "待机";

  return (
    <div
      className={`nest-card nest-r-md border-[var(--border-strong)]/45 min-h-[96px] border p-2.5 shadow-[0_10px_24px_rgba(38,24,8,0.04)] ${toneClass}`}
    >
      <div className="flex items-start gap-2">
        <button
          type="button"
          onClick={onToggle}
          disabled={!hasRuntime}
          className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[var(--text-faint)] disabled:cursor-default disabled:opacity-35"
        >
          {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </button>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: card.color }}
            />
            <span className="truncate text-sm font-semibold text-[var(--text-strong)]">
              {card.name}
            </span>
            <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${pillClass}`}>
              {toneLabel}
            </span>
          </div>

          <p className="mt-1 truncate text-[11px] text-[var(--text-soft)]">{card.status}</p>

          <p className="mt-1 truncate text-[10px] text-[var(--text-faint)]">
            <span className="font-mono">{card.sessionShort ?? "无活跃 session"}</span>
            {card.modelLabel ? ` · ${card.modelLabel}` : ""}
          </p>

          <div className="mt-2 space-y-1">
            <WorkStateLine label="工作中" value={card.taskLabel} compact />
            <WorkStateLine
              label="已完成"
              value={card.taskStatusLine ?? "暂无完成记录"}
              compact
              subtle
            />
          </div>
        </div>
      </div>

      {expanded && hasRuntime && (
        <div className="mt-2 border-t border-[var(--line)] pt-2">
          {card.contextLabel && (
            <>
              <div className="h-1.5 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
                <div
                  className={`h-full rounded-full ${
                    (card.contextPct ?? 0) >= 80 ? "bg-amber-500" : "bg-[var(--accent)]"
                  }`}
                  style={{ width: `${Math.max(0, Math.min(100, card.contextPct ?? 0))}%` }}
                />
              </div>
              <p className="mt-1 text-[10px] text-[var(--text-faint)]">{card.contextLabel}</p>
            </>
          )}

          <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-[var(--text-faint)]">
            <RuntimeInlineMetric label="↑" value={formatCompactNumber(card.promptTokens)} />
            <RuntimeInlineMetric label="↓" value={formatCompactNumber(card.completionTokens)} />
            <RuntimeInlineMetric label="缓存" value={formatCompactNumber(card.cacheTokens)} />
            {card.latencyLabel && <RuntimeInlineMetric label="时延" value={card.latencyLabel} />}
            {card.cliLabel && <RuntimeInlineMetric label="CLI" value={card.cliLabel} />}
          </div>
        </div>
      )}
    </div>
  );
}

function WorkStateLine({
  label,
  value,
  compact = false,
  subtle = false,
}: {
  label: string;
  value: string;
  compact?: boolean;
  subtle?: boolean;
}) {
  return (
    <div
      className={`grid items-start gap-2 ${
        compact ? "grid-cols-[40px,minmax(0,1fr)] text-[10px]" : "grid-cols-[46px,minmax(0,1fr)]"
      }`}
    >
      <span className="text-[var(--text-faint)]">{label}</span>
      <span
        className={`truncate ${subtle ? "text-[var(--text-faint)]" : "text-[var(--text-soft)]"}`}
      >
        {value}
      </span>
    </div>
  );
}

function OverviewFact({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[9px] uppercase tracking-[0.08em] text-[var(--text-faint)]">{label}</div>
      <div className="mt-0.5 truncate text-[11px] font-medium text-[var(--text-strong)]">
        {value}
      </div>
      {detail && <div className="truncate text-[10px] text-[var(--text-faint)]">{detail}</div>}
    </div>
  );
}

function RuntimeCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/45 px-2.5 py-2 dark:bg-white/5">
      <div className="text-[9px] uppercase tracking-[0.08em] text-[var(--text-faint)]">{label}</div>
      <div className="mt-1 text-sm font-semibold text-[var(--text-strong)]">{value}</div>
    </div>
  );
}

function RuntimeInlineMetric({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-[var(--text-soft)]">{label}</span>
      <span>{value}</span>
    </span>
  );
}
