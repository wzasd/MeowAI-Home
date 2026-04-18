export interface StatusOverviewCat {
  id: string;
  name: string;
  displayName?: string;
  isAvailable: boolean;
  colorPrimary?: string;
  defaultModel?: string;
  cliCommand?: string;
}

export interface StatusOverviewSession {
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
  cli_command: string;
  default_model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  budget_max_prompt: number;
  budget_max_context: number;
}

export interface StatusOverviewTask {
  id: string;
  title: string;
  status: "backlog" | "todo" | "doing" | "blocked" | "done";
  ownerCat?: string;
  createdAt?: string;
}

export interface StatusOverviewQueueEntry {
  id: string;
  status: "queued" | "processing" | "paused";
  content: string;
  targetCats: string[];
}

export interface StatusOverviewUsage {
  promptTokens: number;
  completionTokens: number;
  cacheHitRate: number;
  totalCost: number;
}

export interface StatusOverviewMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  cat_id: string | null;
  timestamp: string;
  is_internal?: boolean;
  is_deleted?: boolean;
}

export interface StatusStreamingSnapshot {
  wsConnected: boolean;
  isStreaming: boolean;
  targetCats: string[] | null;
  statuses: Map<string, string>;
  thinking: Map<string, string>;
  responses: Map<string, { content: string }>;
}

export interface StatusOverviewInput {
  threadId: string | null;
  cats: StatusOverviewCat[];
  sessions: StatusOverviewSession[];
  tasks: StatusOverviewTask[];
  messages: StatusOverviewMessage[];
  queueEntries: StatusOverviewQueueEntry[];
  usage: StatusOverviewUsage | null;
  streaming: StatusStreamingSnapshot;
}

type MetricTone = "accent" | "moss" | "warning" | "neutral";
type AlertTone = "info" | "warn" | "danger";
type CatTone = "active" | "focus" | "blocked" | "warming" | "ready" | "idle" | "completed";

export interface StatusMetric {
  label: string;
  value: string;
  note: string;
  tone: MetricTone;
}

export interface StatusAlert {
  label: string;
  value: string;
  tone: AlertTone;
}

export interface OverviewFactItem {
  label: string;
  value: string;
  detail?: string;
}

export interface StatusCatCard {
  id: string;
  name: string;
  color: string;
  tone: CatTone;
  status: string;
  taskLabel: string;
  taskStatusLine: string | null;
  modelLabel: string | null;
  cliLabel: string | null;
  sessionId: string | null;
  sessionShort: string | null;
  latencyLabel: string | null;
  contextPct: number | null;
  contextLabel: string | null;
  taskCount: number;
  messageCount: number;
  turnCount: number;
  restoreFailures: number;
  promptTokens: number;
  completionTokens: number;
  cacheTokens: number;
}

export interface StatusOverviewModel {
  header: {
    threadLabel: string;
    statusLabel: string;
    compactLine: string;
    executionLine: string;
  };
  overviewFacts: OverviewFactItem[];
  metrics: {
    upload: StatusMetric;
    download: StatusMetric;
    cache: StatusMetric;
    context: StatusMetric;
    sessions: StatusMetric;
    tasks: StatusMetric;
  };
  alerts: StatusAlert[];
  taskSummary: {
    total: number;
    doing: number;
    blocked: number;
    done: number;
    completionPct: number;
  };
  queueSummary: {
    queued: number;
    processing: number;
    paused: number;
  };
  sessionSummary: {
    activeCount: number;
    sealedCount: number;
    latestSessionShort: string | null;
  };
  catCards: StatusCatCard[];
  recentlyCompletedCards: StatusCatCard[];
}

const STARTUP_QUOTES = [
  "正在伸懒腰...",
  "正在找猫罐头...",
  "正在梳毛准备中...",
  "正在踩奶热身...",
  "正在观察窗外...",
] as const;

function normalizeOwner(value?: string) {
  return value?.trim().replace(/^@/, "").toLowerCase() ?? "";
}

function ownsTask(cat: StatusOverviewCat, task: StatusOverviewTask) {
  const owner = normalizeOwner(task.ownerCat);
  if (!owner) return false;
  const candidates = [cat.id, cat.name, cat.displayName].map((value) => normalizeOwner(value));
  return candidates.includes(owner);
}

function getStartupQuote(catId: string) {
  const idx =
    catId.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) % STARTUP_QUOTES.length;
  return STARTUP_QUOTES[idx] ?? "准备中...";
}

function shortId(value: string | null | undefined, head = 8, tail = 4) {
  if (!value) return "—";
  if (value.length <= head + tail + 1) return value;
  return `${value.slice(0, head)}…${value.slice(-tail)}`;
}

export function formatCompactNumber(value: number) {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
  return `${Math.round(value)}`;
}

export function pickFocusCatId(cards: StatusCatCard[]) {
  return (
    cards.find((card) => ["active", "focus", "warming", "blocked"].includes(card.tone))?.id ?? null
  );
}

export function filterWorkingCatCards(cards: StatusCatCard[]) {
  return cards.filter((card) => ["active", "focus", "warming", "blocked"].includes(card.tone));
}

function formatLatency(value: number) {
  if (!value) return null;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`;
  return `${Math.round(value)}ms`;
}

function formatPercent(value: number | null) {
  if (value === null || !Number.isFinite(value)) return "—";
  return `${Math.max(0, Math.min(100, Math.floor(value)))}%`;
}

function compactCliLabel(value: string) {
  if (!value) return null;
  const parts = value.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? value;
}

function getCatStatus(
  cat: StatusOverviewCat,
  session: StatusOverviewSession | undefined,
  tasks: StatusOverviewTask[],
  streaming: StatusStreamingSnapshot
): string {
  const statusText = streaming.statuses.get(cat.id);
  if (statusText) return statusText;

  if (streaming.thinking.get(cat.id)) return "思考中...";
  if (streaming.responses.get(cat.id)?.content) return "输出中...";

  const blockedTask = tasks.find((task) => task.status === "blocked");
  if (blockedTask) return `阻塞 · ${blockedTask.title}`;

  const doingTask = tasks.find((task) => task.status === "doing");
  if (doingTask) return `推进 · ${doingTask.title}`;

  const completedTask = getLatestTaskByStatus(tasks, "done");
  if (completedTask) return `已完成 · ${completedTask.title}`;

  if (streaming.isStreaming && streaming.targetCats?.includes(cat.id)) {
    return getStartupQuote(cat.id);
  }

  if (session) {
    return `待命 · ${shortId(session.session_id, 6, 3)}`;
  }

  return "待机";
}

function getCatTone(
  cat: StatusOverviewCat,
  session: StatusOverviewSession | undefined,
  tasks: StatusOverviewTask[],
  streaming: StatusStreamingSnapshot
): CatTone {
  if (
    streaming.statuses.has(cat.id) ||
    streaming.thinking.has(cat.id) ||
    streaming.responses.has(cat.id)
  ) {
    return "active";
  }
  if (tasks.some((task) => task.status === "blocked")) return "blocked";
  if (tasks.some((task) => task.status === "doing")) return "focus";
  if (streaming.isStreaming && streaming.targetCats?.includes(cat.id)) return "warming";
  if (tasks.some((task) => task.status === "done")) return "completed";
  if (session?.status === "sealed") return "completed";
  // Active session with messages but not streaming = recently completed work
  if (session && (session.message_count > 0 || session.turn_count > 0)) return "completed";
  if (session) return "ready";
  return "idle";
}

function toneRank(tone: CatTone) {
  switch (tone) {
    case "active":
      return 7;
    case "focus":
      return 6;
    case "blocked":
      return 5;
    case "warming":
      return 4;
    case "completed":
      return 3;
    case "ready":
      return 2;
    case "idle":
      return 1;
  }
}

function getLatestTaskByStatus(tasks: StatusOverviewTask[], status: StatusOverviewTask["status"]) {
  return tasks
    .filter((task) => task.status === status)
    .sort((left, right) => Date.parse(right.createdAt ?? "") - Date.parse(left.createdAt ?? ""))[0];
}

function buildCurrentWorkLabel(
  catId: string,
  tasks: StatusOverviewTask[],
  session: StatusOverviewSession | null | undefined,
  streaming: StatusStreamingSnapshot
) {
  const blockedTask = getLatestTaskByStatus(tasks, "blocked");
  if (blockedTask) return blockedTask.title;

  const doingTask = getLatestTaskByStatus(tasks, "doing");
  if (doingTask) return doingTask.title;

  if (streaming.statuses.has(catId) || streaming.thinking.has(catId) || streaming.responses.has(catId)) {
    return "处理中";
  }

  if (streaming.isStreaming && streaming.targetCats?.includes(catId)) {
    return "响应当前请求";
  }

  if (session) return "保持热态待命";
  return "暂无工作";
}

function mergeStatusCats(input: StatusOverviewInput): StatusOverviewCat[] {
  const byId = new Map<string, StatusOverviewCat>();

  for (const cat of input.cats.filter((entry) => entry.isAvailable)) {
    byId.set(cat.id, cat);
  }

  for (const session of input.sessions) {
    const existing = byId.get(session.cat_id);
    if (existing) {
      byId.set(session.cat_id, {
        ...existing,
        defaultModel: existing.defaultModel || session.default_model,
        cliCommand: existing.cliCommand || session.cli_command,
        displayName: existing.displayName || session.cat_name,
      });
      continue;
    }

    byId.set(session.cat_id, {
      id: session.cat_id,
      name: session.cat_name || session.cat_id,
      displayName: session.cat_name || undefined,
      isAvailable: true,
      defaultModel: session.default_model || undefined,
      cliCommand: session.cli_command || undefined,
    });
  }

  for (const task of input.tasks) {
    const normalizedOwner = normalizeOwner(task.ownerCat);
    if (!normalizedOwner || byId.has(normalizedOwner)) continue;

    const rawOwner = task.ownerCat?.trim().replace(/^@/, "") || normalizedOwner;
    byId.set(normalizedOwner, {
      id: normalizedOwner,
      name: rawOwner,
      displayName: rawOwner,
      isAvailable: true,
    });
  }

  for (const catId of input.streaming.targetCats ?? []) {
    if (byId.has(catId)) continue;
    byId.set(catId, {
      id: catId,
      name: catId,
      displayName: catId,
      isAvailable: true,
    });
  }

  for (const catId of input.streaming.statuses.keys()) {
    if (byId.has(catId)) continue;
    byId.set(catId, {
      id: catId,
      name: catId,
      displayName: catId,
      isAvailable: true,
    });
  }

  return [...byId.values()];
}

export function buildStatusOverviewModel(input: StatusOverviewInput): StatusOverviewModel {
  const availableCats = mergeStatusCats(input);
  const sortedSessions = [...input.sessions].sort(
    (left, right) => right.created_at - left.created_at
  );
  const activeSessions = sortedSessions.filter((session) => session.status === "active");
  const latestSession = activeSessions[0] ?? sortedSessions[0] ?? null;

  const taskSummary = {
    total: input.tasks.length,
    doing: input.tasks.filter((task) => task.status === "doing").length,
    blocked: input.tasks.filter((task) => task.status === "blocked").length,
    done: input.tasks.filter((task) => task.status === "done").length,
    completionPct:
      input.tasks.length > 0
        ? (input.tasks.filter((task) => task.status === "done").length / input.tasks.length) * 100
        : 0,
  };

  const queueSummary = {
    queued: input.queueEntries.filter((entry) => entry.status === "queued").length,
    processing: input.queueEntries.filter((entry) => entry.status === "processing").length,
    paused: input.queueEntries.filter((entry) => entry.status === "paused").length,
  };

  const promptTokens =
    input.usage?.promptTokens ??
    activeSessions.reduce((sum, session) => sum + session.prompt_tokens, 0);
  const completionTokens =
    input.usage?.completionTokens ??
    activeSessions.reduce((sum, session) => sum + session.completion_tokens, 0);
  const cacheReadTokens = activeSessions.reduce(
    (sum, session) => sum + session.cache_read_tokens,
    0
  );
  const cacheWriteTokens = activeSessions.reduce(
    (sum, session) => sum + session.cache_creation_tokens,
    0
  );
  const cacheHitRate = input.usage?.cacheHitRate ?? null;

  const activeContextUsed = activeSessions.reduce((sum, session) => sum + session.tokens_used, 0);
  const activeContextBudget = activeSessions.reduce(
    (sum, session) => sum + session.budget_max_context,
    0
  );
  const contextPct =
    activeContextBudget > 0 ? (activeContextUsed / activeContextBudget) * 100 : null;
  const restoreFailures = activeSessions.reduce(
    (sum, session) => sum + session.consecutive_restore_failures,
    0
  );

  const alerts: StatusAlert[] = [];
  if (!input.streaming.wsConnected) {
    alerts.push({ label: "连接中断", value: "WebSocket 已断开", tone: "danger" });
  }
  if (taskSummary.blocked > 0) {
    alerts.push({
      label: "任务阻塞",
      value: `${taskSummary.blocked} 个任务卡住`,
      tone: "danger",
    });
  }
  if (restoreFailures > 0) {
    alerts.push({
      label: "恢复异常",
      value: `${restoreFailures} 次恢复失败`,
      tone: "warn",
    });
  }
  if ((contextPct ?? 0) >= 75) {
    alerts.push({
      label: "上下文紧张",
      value: `占用 ${formatPercent(contextPct)}`,
      tone: (contextPct ?? 0) >= 90 ? "danger" : "warn",
    });
  }
  if (queueSummary.queued + queueSummary.processing >= 4) {
    alerts.push({
      label: "队列积压",
      value: `${queueSummary.queued + queueSummary.processing} 条待处理`,
      tone: "warn",
    });
  }

  const catCards = availableCats
    .map((cat) => {
      const activeSession = activeSessions.find((entry) => entry.cat_id === cat.id);
      const catSealedSessions = sortedSessions.filter(
        (entry) => entry.status === "sealed" && entry.cat_id === cat.id
      );
      const latestSealedSession = catSealedSessions[0] ?? undefined;
      const session = activeSession ?? latestSealedSession;
      const catTasks = input.tasks.filter((task) => ownsTask(cat, task));
      const tone = getCatTone(cat, session, catTasks, input.streaming);
      const contextRatio =
        session && session.budget_max_context > 0
          ? (session.tokens_used / session.budget_max_context) * 100
          : null;
      const completedTask = getLatestTaskByStatus(catTasks, "done");
      const taskLabel =
        tone === "completed"
          ? "暂无工作"
          : buildCurrentWorkLabel(cat.id, catTasks, session, input.streaming);

      return {
        id: cat.id,
        name: cat.displayName || cat.name,
        color: cat.colorPrimary || "#b76725",
        tone,
        status: getCatStatus(cat, session, catTasks, input.streaming),
        taskLabel,
        taskStatusLine: completedTask?.title ?? null,
        modelLabel: session?.default_model || cat.defaultModel || null,
        cliLabel: compactCliLabel(session?.cli_command || cat.cliCommand || ""),
        sessionId: session?.session_id ?? null,
        sessionShort: session ? shortId(session.session_id) : null,
        latencyLabel: session ? formatLatency(session.latency_ms) : null,
        contextPct: contextRatio,
        contextLabel:
          session && contextRatio !== null
            ? `${formatPercent(contextRatio)} · ${formatCompactNumber(session.tokens_used)} / ${formatCompactNumber(session.budget_max_context)}`
            : null,
        taskCount: catTasks.length,
        messageCount: session?.message_count ?? 0,
        turnCount: session?.turn_count ?? 0,
        restoreFailures: session?.consecutive_restore_failures ?? 0,
        promptTokens: session?.prompt_tokens ?? 0,
        completionTokens: session?.completion_tokens ?? 0,
        cacheTokens: (session?.cache_read_tokens ?? 0) + (session?.cache_creation_tokens ?? 0),
      } satisfies StatusCatCard;
    })
    .sort((left, right) => {
      const diff = toneRank(right.tone) - toneRank(left.tone);
      if (diff !== 0) return diff;
      return right.taskCount - left.taskCount;
    });

  const queueDetail = [`排队 ${queueSummary.queued}`];
  if (queueSummary.paused > 0) {
    queueDetail.push(`暂停 ${queueSummary.paused}`);
  }

  const overviewFacts: OverviewFactItem[] = [
    {
      label: "任务",
      value: `进行 ${taskSummary.doing} · 阻塞 ${taskSummary.blocked}`,
      detail: taskSummary.total > 0 ? `完成 ${taskSummary.done}/${taskSummary.total}` : "暂无任务",
    },
    {
      label: "队列",
      value: `处理中 ${queueSummary.processing}`,
      detail: queueDetail.join(" · "),
    },
    {
      label: "Context",
      value: formatPercent(contextPct),
      detail:
        contextPct === null
          ? "暂无预算"
          : `${formatCompactNumber(activeContextUsed)} / ${formatCompactNumber(activeContextBudget)}`,
    },
    {
      label: "I/O",
      value: `↑${formatCompactNumber(promptTokens)} ↓${formatCompactNumber(completionTokens)}`,
      detail:
        cacheHitRate === null
          ? `缓存 ${formatCompactNumber(cacheReadTokens + cacheWriteTokens)}`
          : `缓存 ${Math.round(cacheHitRate * 100)}%`,
    },
  ];

  return {
    header: {
      threadLabel: input.threadId ? shortId(input.threadId, 8, 4) : "未选线程",
      statusLabel: input.streaming.wsConnected ? "在线" : "离线",
      compactLine: `${input.streaming.wsConnected ? "在线" : "离线"} ${availableCats.length}猫 · ${
        activeSessions.length
      }活跃 · Context ${formatPercent(contextPct)} · 队列 ${
        queueSummary.processing + queueSummary.queued
      }`,
      executionLine: `任务 ${taskSummary.doing} 进行中 · ${taskSummary.blocked} 阻塞 · 队列 ${
        queueSummary.processing + queueSummary.queued
      } 条`,
    },
    overviewFacts,
    metrics: {
      upload: {
        label: "上行",
        value: formatCompactNumber(promptTokens),
        note: "Prompt",
        tone: "warning",
      },
      download: {
        label: "下行",
        value: formatCompactNumber(completionTokens),
        note: "Completion",
        tone: "accent",
      },
      cache: {
        label: "缓存命中",
        value: cacheHitRate === null ? "—" : `${Math.round(cacheHitRate * 100)}%`,
        note:
          cacheHitRate === null
            ? "暂无采样"
            : `${formatCompactNumber(cacheReadTokens + cacheWriteTokens)} 缓存流量`,
        tone: "moss",
      },
      context: {
        label: "上下文占用",
        value: formatPercent(contextPct),
        note:
          contextPct === null
            ? "暂无预算"
            : `${formatCompactNumber(activeContextUsed)} / ${formatCompactNumber(activeContextBudget)}`,
        tone: (contextPct ?? 0) >= 75 ? "warning" : "neutral",
      },
      sessions: {
        label: "当前会话",
        value: `${activeSessions.length}`,
        note: latestSession ? shortId(latestSession.session_id) : "暂无会话",
        tone: "neutral",
      },
      tasks: {
        label: "任务完成",
        value: formatPercent(taskSummary.completionPct),
        note: `${taskSummary.doing} 进行中 · ${taskSummary.blocked} 阻塞`,
        tone: taskSummary.blocked > 0 ? "warning" : "neutral",
      },
    },
    alerts,
    taskSummary,
    queueSummary,
    sessionSummary: {
      activeCount: activeSessions.length,
      sealedCount: sortedSessions.length - activeSessions.length,
      latestSessionShort: latestSession ? shortId(latestSession.session_id) : null,
    },
    catCards,
    recentlyCompletedCards: catCards.filter((card) => card.tone === "completed"),
  };
}
