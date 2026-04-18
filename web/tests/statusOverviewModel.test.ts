import assert from "node:assert/strict";
import test from "node:test";

import {
  buildStatusOverviewModel,
  filterWorkingCatCards,
  pickFocusCatId,
} from "../src/components/right-panel/statusOverviewModel.ts";

test("buildStatusOverviewModel aggregates sessions, tasks, and queue into headline metrics", () => {
  const model = buildStatusOverviewModel({
    threadId: "thread-alpha-123456",
    cats: [
      {
        id: "gemini",
        name: "gemini",
        displayName: "烁烁",
        isAvailable: true,
        colorPrimary: "#f97316",
      },
      {
        id: "sonnet",
        name: "sonnet",
        displayName: "Sonnet",
        isAvailable: true,
        colorPrimary: "#14b8a6",
      },
    ],
    sessions: [
      {
        session_id: "019d957a-c20a-7f3e-bca8-11f25ed44c2a",
        cat_id: "gemini",
        cat_name: "烁烁",
        status: "active",
        created_at: 1713259200,
        consecutive_restore_failures: 0,
        message_count: 8,
        tokens_used: 158772,
        latency_ms: 1420,
        turn_count: 4,
        cli_command: "codex",
        default_model: "gpt-5.4",
        prompt_tokens: 33100,
        completion_tokens: 4600000,
        cache_read_tokens: 120000,
        cache_creation_tokens: 5000,
        budget_max_prompt: 64000,
        budget_max_context: 258000,
      },
    ],
    tasks: [
      { id: "t-1", title: "重构状态栏", status: "doing", ownerCat: "gemini" },
      { id: "t-5", title: "落地总览卡片", status: "done", ownerCat: "gemini" },
      { id: "t-2", title: "补会话删除按钮", status: "done", ownerCat: "sonnet" },
      { id: "t-3", title: "整理缓存展示", status: "todo", ownerCat: "gemini" },
      { id: "t-4", title: "修复被遮挡弹窗", status: "blocked", ownerCat: "sonnet" },
    ],
    messages: [],
    queueEntries: [
      { id: "q-1", status: "processing", content: "@gemini 重构状态栏", targetCats: ["gemini"] },
      { id: "q-2", status: "queued", content: "@sonnet 看下样式", targetCats: ["sonnet"] },
    ],
    usage: {
      promptTokens: 33100,
      completionTokens: 4600000,
      cacheHitRate: 0.93,
      totalCost: 2.16,
    },
    streaming: {
      wsConnected: true,
      isStreaming: true,
      targetCats: ["gemini"],
      statuses: new Map([["gemini", "正在重构状态台"]]),
      thinking: new Map(),
      responses: new Map(),
    },
  });

  assert.equal(model.header.threadLabel, "thread-a…3456");
  assert.equal(model.header.compactLine, "在线 2猫 · 1活跃 · Context 61% · 队列 2");
  assert.equal(model.header.executionLine, "任务 1 进行中 · 1 阻塞 · 队列 2 条");
  assert.deepEqual(
    model.overviewFacts.map((fact) => fact.label),
    ["任务", "队列", "Context", "I/O"]
  );
  assert.equal(model.overviewFacts[0]?.value, "进行 1 · 阻塞 1");
  assert.equal(model.overviewFacts[1]?.value, "处理中 1");
  assert.equal(model.sessionSummary.activeCount, 1);
  assert.equal(model.taskSummary.blocked, 1);
  assert.equal(model.queueSummary.processing, 1);
  assert.equal(model.metrics.context.value, "61%");
  assert.equal(model.metrics.cache.value, "93%");
  assert.equal(model.metrics.tasks.value, "40%");
  assert.equal(model.catCards[0]?.id, "gemini");
  assert.equal(model.catCards[0]?.status, "正在重构状态台");
  assert.equal(model.catCards[0]?.sessionId, "019d957a-c20a-7f3e-bca8-11f25ed44c2a");
  assert.equal(model.catCards[0]?.sessionShort, "019d957a…4c2a");
  assert.equal(model.catCards[0]?.taskLabel, "重构状态栏");
  assert.equal(model.catCards[0]?.taskStatusLine, "落地总览卡片");
  assert.equal(model.catCards[0]?.promptTokens, 33100);
  assert.equal(model.catCards[0]?.completionTokens, 4600000);
  assert.equal(model.catCards[0]?.cacheTokens, 125000);
});

test("buildStatusOverviewModel separates current work from last completed work", () => {
  const model = buildStatusOverviewModel({
    threadId: "thread-work",
    cats: [{ id: "gemini", name: "gemini", displayName: "烁烁", isAvailable: true }],
    sessions: [
      {
        session_id: "session-gemini",
        cat_id: "gemini",
        cat_name: "烁烁",
        status: "active",
        created_at: 1713312000,
        consecutive_restore_failures: 0,
        message_count: 2,
        tokens_used: 12000,
        latency_ms: 950,
        turn_count: 1,
        cli_command: "codex",
        default_model: "gpt-5.4",
        prompt_tokens: 8000,
        completion_tokens: 4000,
        cache_read_tokens: 0,
        cache_creation_tokens: 0,
        budget_max_prompt: 64000,
        budget_max_context: 64000,
      },
    ],
    tasks: [
      {
        id: "t-done-older",
        title: "补色板",
        status: "done",
        ownerCat: "gemini",
        createdAt: "2026-04-17T08:10:00+08:00",
      },
      {
        id: "t-doing",
        title: "重构右侧状态栏",
        status: "doing",
        ownerCat: "gemini",
        createdAt: "2026-04-17T08:20:00+08:00",
      },
      {
        id: "t-done-latest",
        title: "压缩总览标签",
        status: "done",
        ownerCat: "gemini",
        createdAt: "2026-04-17T08:30:00+08:00",
      },
    ],
    messages: [],
    queueEntries: [],
    usage: null,
    streaming: {
      wsConnected: true,
      isStreaming: true,
      targetCats: ["gemini"],
      statuses: new Map([["gemini", "正在重构状态栏"]]),
      thinking: new Map(),
      responses: new Map(),
    },
  });

  assert.equal(model.catCards[0]?.taskLabel, "重构右侧状态栏");
  assert.equal(model.catCards[0]?.taskStatusLine, "压缩总览标签");
});

test("buildStatusOverviewModel keeps the latest done task visible even before session is sealed", () => {
  const model = buildStatusOverviewModel({
    threadId: "thread-completed",
    cats: [{ id: "gemini", name: "gemini", displayName: "烁烁", isAvailable: true }],
    sessions: [
      {
        session_id: "session-still-open",
        cat_id: "gemini",
        cat_name: "烁烁",
        status: "active",
        created_at: 1713312600,
        consecutive_restore_failures: 0,
        message_count: 3,
        tokens_used: 8000,
        latency_ms: 640,
        turn_count: 2,
        cli_command: "codex",
        default_model: "gpt-5.4",
        prompt_tokens: 3000,
        completion_tokens: 5000,
        cache_read_tokens: 0,
        cache_creation_tokens: 0,
        budget_max_prompt: 64000,
        budget_max_context: 64000,
      },
    ],
    tasks: [
      {
        id: "t-done",
        title: "把状态栏压平",
        status: "done",
        ownerCat: "gemini",
        createdAt: "2026-04-17T08:40:00+08:00",
      },
    ],
    messages: [],
    queueEntries: [],
    usage: null,
    streaming: {
      wsConnected: true,
      isStreaming: false,
      targetCats: [],
      statuses: new Map(),
      thinking: new Map(),
      responses: new Map(),
    },
  });

  assert.equal(model.recentlyCompletedCards.length, 1);
  assert.equal(model.recentlyCompletedCards[0]?.id, "gemini");
  assert.equal(model.recentlyCompletedCards[0]?.taskStatusLine, "把状态栏压平");
  assert.equal(filterWorkingCatCards(model.catCards).length, 0);
});

test("buildStatusOverviewModel derives visible cats from sessions and tasks when cat store is empty", () => {
  const model = buildStatusOverviewModel({
    threadId: "thread-fallback",
    cats: [],
    sessions: [
      {
        session_id: "session-fallback",
        cat_id: "gemini",
        cat_name: "烁烁",
        status: "active",
        created_at: 1713312600,
        consecutive_restore_failures: 0,
        message_count: 1,
        tokens_used: 6000,
        latency_ms: 720,
        turn_count: 1,
        cli_command: "codex",
        default_model: "gpt-5.4",
        prompt_tokens: 2000,
        completion_tokens: 4000,
        cache_read_tokens: 0,
        cache_creation_tokens: 0,
        budget_max_prompt: 64000,
        budget_max_context: 64000,
      },
    ],
    tasks: [
      {
        id: "done-fallback",
        title: "补上完成态展示",
        status: "done",
        ownerCat: "@gemini",
        createdAt: "2026-04-17T09:20:00+08:00",
      },
    ],
    messages: [],
    queueEntries: [],
    usage: null,
    streaming: {
      wsConnected: true,
      isStreaming: false,
      targetCats: [],
      statuses: new Map(),
      thinking: new Map(),
      responses: new Map(),
    },
  });

  assert.equal(model.catCards.length, 1);
  assert.equal(model.catCards[0]?.name, "烁烁");
  assert.equal(model.recentlyCompletedCards.length, 1);
  assert.equal(model.recentlyCompletedCards[0]?.id, "gemini");
});

test("buildStatusOverviewModel emits risk alerts for disconnect, restore failures, context pressure, and queue backlog", () => {
  const model = buildStatusOverviewModel({
    threadId: "thread-beta",
    cats: [{ id: "gemini", name: "gemini", displayName: "烁烁", isAvailable: true }],
    sessions: [
      {
        session_id: "session-very-long-id-0001",
        cat_id: "gemini",
        cat_name: "烁烁",
        status: "active",
        created_at: 1713259200,
        consecutive_restore_failures: 2,
        message_count: 3,
        tokens_used: 92000,
        latency_ms: 800,
        turn_count: 2,
        cli_command: "codex",
        default_model: "gpt-5.4",
        prompt_tokens: 12000,
        completion_tokens: 45000,
        cache_read_tokens: 1000,
        cache_creation_tokens: 0,
        budget_max_prompt: 64000,
        budget_max_context: 100000,
      },
    ],
    tasks: [{ id: "t-1", title: "修复卡片层级", status: "blocked", ownerCat: "gemini" }],
    messages: [],
    queueEntries: [
      { id: "q-1", status: "queued", content: "a", targetCats: ["gemini"] },
      { id: "q-2", status: "queued", content: "b", targetCats: ["gemini"] },
      { id: "q-3", status: "processing", content: "c", targetCats: ["gemini"] },
      { id: "q-4", status: "queued", content: "d", targetCats: ["gemini"] },
    ],
    usage: {
      promptTokens: 12000,
      completionTokens: 45000,
      cacheHitRate: 0.42,
      totalCost: 0.32,
    },
    streaming: {
      wsConnected: false,
      isStreaming: false,
      targetCats: [],
      statuses: new Map(),
      thinking: new Map(),
      responses: new Map(),
    },
  });

  assert.deepEqual(
    model.alerts.map((alert) => alert.label),
    ["连接中断", "任务阻塞", "恢复异常", "上下文紧张", "队列积压"]
  );
  assert.equal(model.header.compactLine, "离线 1猫 · 1活跃 · Context 92% · 队列 4");
  assert.equal(model.header.executionLine, "任务 0 进行中 · 1 阻塞 · 队列 4 条");
  assert.equal(model.alerts[0]?.tone, "danger");
  assert.equal(model.alerts[1]?.tone, "danger");
  assert.equal(model.alerts[2]?.tone, "warn");
  assert.equal(model.alerts[3]?.tone, "danger");
  assert.equal(model.alerts[4]?.tone, "warn");
});

test("pickFocusCatId prefers the first non-idle cat for auto expansion", () => {
  assert.equal(
    pickFocusCatId([
      {
        id: "idle",
        name: "待机猫",
        color: "#999",
        tone: "idle",
        status: "待机",
        taskLabel: "暂无任务",
        modelLabel: null,
        cliLabel: null,
        sessionId: null,
        sessionShort: null,
        latencyLabel: null,
        contextPct: null,
        contextLabel: null,
        taskCount: 0,
        messageCount: 0,
        turnCount: 0,
        restoreFailures: 0,
        promptTokens: 0,
        completionTokens: 0,
        cacheTokens: 0,
      },
      {
        id: "active",
        name: "工作猫",
        color: "#333",
        tone: "active",
        status: "输出中",
        taskLabel: "处理状态台",
        modelLabel: "gpt-5.4",
        cliLabel: "codex",
        sessionId: "session-active",
        sessionShort: "sess-1",
        latencyLabel: "1.2s",
        contextPct: 42,
        contextLabel: "42%",
        taskCount: 1,
        messageCount: 2,
        turnCount: 1,
        restoreFailures: 0,
        promptTokens: 10,
        completionTokens: 20,
        cacheTokens: 0,
      },
    ]),
    "active"
  );
});

test("filterWorkingCatCards removes idle and ready cats from overview roster", () => {
  assert.deepEqual(
    filterWorkingCatCards([
      {
        id: "idle",
        name: "待机猫",
        color: "#999",
        tone: "idle",
        status: "待机",
        taskLabel: "暂无任务",
        modelLabel: null,
        cliLabel: null,
        sessionId: null,
        sessionShort: null,
        latencyLabel: null,
        contextPct: null,
        contextLabel: null,
        taskCount: 0,
        messageCount: 0,
        turnCount: 0,
        restoreFailures: 0,
        promptTokens: 0,
        completionTokens: 0,
        cacheTokens: 0,
      },
      {
        id: "ready",
        name: "就绪猫",
        color: "#999",
        tone: "ready",
        status: "待命",
        taskLabel: "暂无任务",
        modelLabel: null,
        cliLabel: null,
        sessionId: "session-ready",
        sessionShort: "sess-r",
        latencyLabel: null,
        contextPct: null,
        contextLabel: null,
        taskCount: 0,
        messageCount: 0,
        turnCount: 0,
        restoreFailures: 0,
        promptTokens: 0,
        completionTokens: 0,
        cacheTokens: 0,
      },
      {
        id: "active",
        name: "工作猫",
        color: "#333",
        tone: "active",
        status: "输出中",
        taskLabel: "处理状态台",
        modelLabel: "gpt-5.4",
        cliLabel: "codex",
        sessionId: "session-active",
        sessionShort: "sess-1",
        latencyLabel: "1.2s",
        contextPct: 42,
        contextLabel: "42%",
        taskCount: 1,
        messageCount: 2,
        turnCount: 1,
        restoreFailures: 0,
        promptTokens: 10,
        completionTokens: 20,
        cacheTokens: 0,
      },
    ]).map((card) => card.id),
    ["active"]
  );
});
