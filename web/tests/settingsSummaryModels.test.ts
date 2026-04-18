import assert from "node:assert/strict";
import test from "node:test";

import type {
  AccountResponse,
  CatMetricsRow,
  CapabilityBoardItem,
  ConnectorBindingStatus,
  ConnectorResponse,
  EnvVarResponse,
  MetricsLeaderboardEntry,
} from "../src/types/index.ts";
import type { Cat } from "../src/stores/catStore.ts";
import {
  buildAccountSummaryCards,
  buildCapabilitySummaryCards,
  buildConnectorSummaryCards,
  buildEnvVarSummaryCards,
  buildGovernanceSummaryCards,
  buildLeaderboardSummaryCards,
  buildPermissionSummaryCards,
  buildQuotaMetricSnapshot,
  buildQuotaSummaryCards,
  rankLeaderboardEntries,
  type GovernanceProjectSnapshot,
  type PermissionSummaryDefinition,
  type QuotaMetricSnapshot,
} from "../src/components/settings/settingsSummaryModels.ts";

test("account summary cards capture auth mix and cat binding coverage", () => {
  const accounts: AccountResponse[] = [
    {
      id: "builtin-openai",
      displayName: "OpenAI Builtin",
      protocol: "openai",
      authType: "subscription",
      baseUrl: null,
      models: null,
      isBuiltin: true,
      hasApiKey: false,
    },
    {
      id: "anthropic-prod",
      displayName: "Anthropic Prod",
      protocol: "anthropic",
      authType: "api_key",
      baseUrl: null,
      models: null,
      isBuiltin: false,
      hasApiKey: true,
    },
    {
      id: "google-dev",
      displayName: "Google Dev",
      protocol: "google",
      authType: "api_key",
      baseUrl: null,
      models: null,
      isBuiltin: false,
      hasApiKey: true,
    },
  ];

  const cats: Cat[] = [
    {
      id: "orange",
      name: "Orange",
      displayName: "阿橘",
      provider: "openai",
      isAvailable: true,
      accountRef: "builtin-openai",
    },
    {
      id: "inky",
      name: "Inky",
      displayName: "墨点",
      provider: "anthropic",
      isAvailable: true,
      accountRef: "anthropic-prod",
    },
    {
      id: "patch",
      name: "Patch",
      displayName: "花花",
      provider: "google",
      isAvailable: false,
    },
    {
      id: "tabby",
      name: "Tabby",
      displayName: "狸花",
      provider: "openai",
      isAvailable: true,
      accountRef: "missing-account",
    },
  ];

  const cards = buildAccountSummaryCards(accounts, cats);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "accounts",
        value: "3",
        tone: "neutral",
        detail: "1 个内建 · 2 个自定义",
      },
      {
        id: "api-key",
        value: "2",
        tone: "accent",
        detail: "2 个密钥账号可独立配额",
      },
      {
        id: "subscription",
        value: "1",
        tone: "success",
        detail: "1 个订阅账号走 CLI OAuth",
      },
      {
        id: "binding",
        value: "2/4",
        tone: "attention",
        detail: "2 只未绑定或绑定失效 · 3 只当前可用",
      },
    ]
  );
});

test("governance summary cards capture healthy, risky, and pending activation states", () => {
  const projects: GovernanceProjectSnapshot[] = [
    {
      project_path: "/workspace/alpha",
      status: "healthy",
      pack_version: "1.3.0",
      last_synced_at: "2026-04-17T10:00:00Z",
      findings: [],
      confirmed: true,
    },
    {
      project_path: "/workspace/beta",
      status: "stale",
      pack_version: "1.2.0",
      last_synced_at: "2026-04-14T10:00:00Z",
      findings: [{ rule: "sync", severity: "warning", message: "needs sync" }],
      confirmed: true,
    },
    {
      project_path: "/workspace/gamma",
      status: "never-synced",
      pack_version: null,
      last_synced_at: null,
      findings: [],
      confirmed: false,
    },
    {
      project_path: "/workspace/delta",
      status: "error",
      pack_version: "1.3.0",
      last_synced_at: "2026-04-16T10:00:00Z",
      findings: [
        { rule: "pack", severity: "error", message: "pack missing" },
        { rule: "contract", severity: "error", message: "contract drift" },
      ],
      confirmed: false,
    },
  ];

  const cards = buildGovernanceSummaryCards(projects);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "projects",
        value: "4",
        tone: "neutral",
        detail: "1 正常 · 2 需处理",
      },
      {
        id: "healthy",
        value: "1",
        tone: "success",
        detail: "25% 当前健康",
      },
      {
        id: "attention",
        value: "2",
        tone: "attention",
        detail: "3 条发现需要确认",
      },
      {
        id: "activation",
        value: "2",
        tone: "attention",
        detail: "1 个未同步 · 2 个待激活",
      },
    ]
  );
});

test("connector summary cards capture channel coverage, binding baseline, and pending actions", () => {
  const connectors: ConnectorResponse[] = [
    {
      name: "feishu",
      displayName: "飞书",
      enabled: true,
      status: "ok",
      features: ["chat", "mention", "notification"],
      configFields: ["app_id", "app_secret"],
    },
    {
      name: "telegram",
      displayName: "Telegram",
      enabled: true,
      status: "ok",
      features: ["chat", "notification"],
      configFields: ["bot_token"],
    },
    {
      name: "wecom_bot",
      displayName: "企业微信机器人",
      enabled: false,
      status: "disabled",
      features: ["notification"],
      configFields: ["webhook"],
    },
    {
      name: "dingtalk",
      displayName: "钉钉",
      enabled: false,
      status: "disabled",
      features: ["chat", "workflow"],
      configFields: [],
    },
  ];

  const bindingStatus: Record<string, ConnectorBindingStatus> = {
    feishu: {
      name: "feishu",
      bound: true,
      bound_at: "2026-04-17T10:00:00Z",
      bound_user: "阿橘",
    },
    telegram: {
      name: "telegram",
      bound: false,
      bound_at: null,
      bound_user: null,
    },
  };

  const cards = buildConnectorSummaryCards(connectors, bindingStatus);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "channels",
        value: "4",
        tone: "neutral",
        detail: "2 已启用 · 2 未启用",
      },
      {
        id: "coverage",
        value: "4",
        tone: "accent",
        detail: "来自 4 个连接器声明的能力面",
      },
      {
        id: "bound",
        value: "1",
        tone: "success",
        detail: "1 个启用通道待绑定",
      },
      {
        id: "pending",
        value: "3",
        tone: "attention",
        detail: "2 个未启用 · 1 个待绑定",
      },
    ]
  );
});

test("permission summary cards capture configured cats, high-risk grants, and review queue", () => {
  const permissions: PermissionSummaryDefinition[] = [
    { id: "read_all_threads", riskLevel: "low" },
    { id: "write_file", riskLevel: "medium" },
    { id: "execute_command", riskLevel: "high" },
    { id: "manage_cats", riskLevel: "high" },
  ];

  const cats: Cat[] = [
    {
      id: "gemini",
      name: "gemini",
      displayName: "烁烁",
      provider: "google",
      isAvailable: true,
      permissions: ["read_all_threads"],
    },
    {
      id: "opus",
      name: "opus",
      displayName: "宪宪",
      provider: "anthropic",
      isAvailable: true,
      permissions: ["execute_command", "write_file"],
    },
    {
      id: "codex",
      name: "codex",
      displayName: "砚砚",
      provider: "openai",
      isAvailable: true,
      permissions: ["read_all_threads", "write_file", "execute_command", "manage_cats"],
    },
    {
      id: "sonnet",
      name: "sonnet",
      displayName: "Sonnet",
      provider: "anthropic",
      isAvailable: false,
      permissions: [],
    },
  ];

  const cards = buildPermissionSummaryCards(cats, permissions);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "permission-types",
        value: "4",
        tone: "neutral",
        detail: "2 项高风险 · 1 项中风险",
      },
      {
        id: "configured-cats",
        value: "3/4",
        tone: "attention",
        detail: "1 只尚未配置任何权限",
      },
      {
        id: "high-risk-grants",
        value: "3",
        tone: "attention",
        detail: "2 只猫拥有高风险权限",
      },
      {
        id: "review",
        value: "2",
        tone: "attention",
        detail: "1 只空权限 · 1 只全权限",
      },
    ]
  );
});

test("env var summary cards capture coverage, required gaps, and sensitive footprint", () => {
  const vars: EnvVarResponse[] = [
    {
      name: "OPENAI_API_KEY",
      category: "ai",
      description: "OpenAI key",
      default: null,
      current: "sk-live",
      isSet: true,
      required: true,
      sensitive: true,
      allowedValues: null,
    },
    {
      name: "ANTHROPIC_API_KEY",
      category: "ai",
      description: "Anthropic key",
      default: null,
      current: "",
      isSet: false,
      required: true,
      sensitive: true,
      allowedValues: null,
    },
    {
      name: "APP_ENV",
      category: "core",
      description: "Environment",
      default: "dev",
      current: "dev",
      isSet: true,
      required: false,
      sensitive: false,
      allowedValues: ["dev", "prod"],
    },
    {
      name: "TELEGRAM_ENABLED",
      category: "connector",
      description: "Connector toggle",
      default: "false",
      current: "false",
      isSet: true,
      required: false,
      sensitive: false,
      allowedValues: ["true", "false"],
    },
  ];

  const cards = buildEnvVarSummaryCards(vars);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "variables",
        value: "4",
        tone: "neutral",
        detail: "覆盖 3 个配置分类",
      },
      {
        id: "configured",
        value: "3/4",
        tone: "attention",
        detail: "1 个变量尚未设置",
      },
      {
        id: "required",
        value: "1/2",
        tone: "attention",
        detail: "1 个必需项缺失",
      },
      {
        id: "sensitive",
        value: "2",
        tone: "accent",
        detail: "2 个敏感项 · 2 个枚举项",
      },
    ]
  );
});

test("capability summary cards capture global state, overrides, and attention load", () => {
  const items: CapabilityBoardItem[] = [
    {
      id: "browser",
      type: "mcp",
      source: "builtin",
      enabled: true,
      cats: { gemini: true, opus: false },
      connectionStatus: "connected",
      tools: [{ name: "open" }, { name: "click" }],
    },
    {
      id: "search",
      type: "mcp",
      source: "external",
      enabled: false,
      cats: { gemini: true, opus: false },
      connectionStatus: "error",
      probeError: "socket hang up",
    },
    {
      id: "rich-messaging",
      type: "skill",
      source: "skill-pack",
      enabled: true,
      cats: { gemini: true, opus: true },
      auditStatus: "passed",
      triggers: ["rich", "audio"],
    },
    {
      id: "browser-preview",
      type: "skill",
      source: "skill-pack",
      enabled: true,
      cats: { gemini: false, opus: true },
      auditStatus: "failed",
      auditIssues: ["missing check"],
    },
  ];

  const cards = buildCapabilitySummaryCards(items);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "capabilities",
        value: "4",
        tone: "neutral",
        detail: "2 个 MCP · 2 个 Skill",
      },
      {
        id: "global",
        value: "3/4",
        tone: "accent",
        detail: "1 项当前全局关闭",
      },
      {
        id: "overrides",
        value: "3",
        tone: "attention",
        detail: "3 个单猫覆盖分支 · 3 项能力受影响",
      },
      {
        id: "attention",
        value: "2",
        tone: "attention",
        detail: "1 个探测异常 · 1 个审计异常",
      },
    ]
  );
});

test("quota metric snapshot aggregates token, success, and latency data", () => {
  const rows: CatMetricsRow[] = [
    { prompt_tokens: 1000, completion_tokens: 200, duration_ms: 1200, success: true },
    { prompt_tokens: 500, completion_tokens: 300, duration_ms: 1800, success: false },
    { prompt_tokens: 700, completion_tokens: 100, duration_ms: 900, success: true },
  ];

  const snapshot = buildQuotaMetricSnapshot("gemini", rows);

  assert.deepEqual(snapshot, {
    catId: "gemini",
    totalInvocations: 3,
    successRate: 2 / 3,
    avgLatencyMs: 1300,
    totalTokens: 2800,
    trend: "down",
  });
});

test("quota summary cards capture fleet load, stability, and attention queue", () => {
  const metrics: QuotaMetricSnapshot[] = [
    {
      catId: "gemini",
      totalInvocations: 12,
      successRate: 1,
      avgLatencyMs: 900,
      totalTokens: 120000,
      trend: "up",
    },
    {
      catId: "opus",
      totalInvocations: 8,
      successRate: 0.875,
      avgLatencyMs: 1800,
      totalTokens: 80000,
      trend: "stable",
    },
    {
      catId: "codex",
      totalInvocations: 5,
      successRate: 0.6,
      avgLatencyMs: 4200,
      totalTokens: 40000,
      trend: "down",
    },
  ];

  const cards = buildQuotaSummaryCards(metrics, 4);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "tokens",
        value: "240k",
        tone: "neutral",
        detail: "3 只猫有调用记录 · 单次平均 9.6k",
      },
      {
        id: "invocations",
        value: "25",
        tone: "accent",
        detail: "4 只猫中有 3 只在 7 天内活跃",
      },
      {
        id: "success",
        value: "88.0%",
        tone: "attention",
        detail: "2 只猫成功率低于 90%",
      },
      {
        id: "attention",
        value: "2",
        tone: "attention",
        detail: "1 只平均延迟高于 3s · 1 只趋势下滑",
      },
    ]
  );
});

test("leaderboard ranking keeps score, tokens, and rank ordering in one place", () => {
  const entries: MetricsLeaderboardEntry[] = [
    {
      cat_id: "gemini",
      total_calls: 20,
      success_rate: 0.98,
      avg_duration_ms: 1200,
      prompt_tokens: 120000,
      completion_tokens: 30000,
    },
    {
      cat_id: "codex",
      total_calls: 18,
      success_rate: 0.95,
      avg_duration_ms: 800,
      prompt_tokens: 90000,
      completion_tokens: 18000,
    },
    {
      cat_id: "opus",
      total_calls: 25,
      success_rate: 0.88,
      avg_duration_ms: 2000,
      prompt_tokens: 110000,
      completion_tokens: 50000,
    },
    {
      cat_id: "sonnet",
      total_calls: 4,
      success_rate: 0.75,
      avg_duration_ms: 500,
      prompt_tokens: 5000,
      completion_tokens: 2000,
    },
  ];

  const ranked = rankLeaderboardEntries(entries);

  assert.deepEqual(
    ranked.map((entry) => ({
      cat_id: entry.cat_id,
      rank: entry.rank,
      score: entry.score,
      totalTokens: entry.totalTokens,
    })),
    [
      { cat_id: "gemini", rank: 1, score: 96.8, totalTokens: 150000 },
      { cat_id: "codex", rank: 2, score: 94.2, totalTokens: 108000 },
      { cat_id: "opus", rank: 3, score: 86, totalTokens: 160000 },
      { cat_id: "sonnet", rank: 4, score: 74.5, totalTokens: 7000 },
    ]
  );
});

test("leaderboard summary cards surface champion, field quality, and review load", () => {
  const ranked = rankLeaderboardEntries([
    {
      cat_id: "gemini",
      total_calls: 20,
      success_rate: 0.98,
      avg_duration_ms: 1200,
      prompt_tokens: 120000,
      completion_tokens: 30000,
    },
    {
      cat_id: "codex",
      total_calls: 18,
      success_rate: 0.95,
      avg_duration_ms: 800,
      prompt_tokens: 90000,
      completion_tokens: 18000,
    },
    {
      cat_id: "opus",
      total_calls: 25,
      success_rate: 0.88,
      avg_duration_ms: 2000,
      prompt_tokens: 110000,
      completion_tokens: 50000,
    },
    {
      cat_id: "sonnet",
      total_calls: 4,
      success_rate: 0.75,
      avg_duration_ms: 500,
      prompt_tokens: 5000,
      completion_tokens: 2000,
    },
  ]);

  const cards = buildLeaderboardSummaryCards(ranked);

  assert.deepEqual(
    cards.map((card) => ({
      id: card.id,
      value: card.value,
      tone: card.tone,
      detail: card.detail,
    })),
    [
      {
        id: "participants",
        value: "4",
        tone: "neutral",
        detail: "总调用 67 次 · 3 只进入领奖台",
      },
      {
        id: "champion",
        value: "96.8",
        tone: "accent",
        detail: "gemini 当前排名第一",
      },
      {
        id: "success",
        value: "89.0%",
        tone: "attention",
        detail: "2 只成功率达到 95%",
      },
      {
        id: "attention",
        value: "2",
        tone: "attention",
        detail: "0 只平均延迟高于 3s · 2 只成功率低于 90%",
      },
    ]
  );
});
