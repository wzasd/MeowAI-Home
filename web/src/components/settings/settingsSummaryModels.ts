import type { Cat } from "../../stores/catStore";
import type {
  AccountResponse,
  CatMetricsRow,
  CapabilityBoardItem,
  ConnectorBindingStatus,
  ConnectorResponse,
  EnvVarResponse,
  MetricsLeaderboardEntry,
} from "../../types";

export type SettingsSummaryTone = "neutral" | "accent" | "success" | "attention";

export interface SettingsSummaryCardModel {
  id: string;
  label: string;
  value: string;
  detail: string;
  tone: SettingsSummaryTone;
}

export interface PermissionSummaryDefinition {
  id: string;
  riskLevel: "low" | "medium" | "high";
}

export interface GovernanceProjectSnapshot {
  project_path: string;
  status: "healthy" | "stale" | "missing" | "never-synced" | "error";
  pack_version: string | null;
  last_synced_at: string | null;
  findings: Array<{
    rule: string;
    severity: string;
    message: string;
  }>;
  confirmed: boolean;
}

export interface QuotaMetricSnapshot {
  catId: string;
  totalInvocations: number;
  successRate: number;
  avgLatencyMs: number;
  totalTokens: number;
  trend: "up" | "down" | "stable";
}

export interface RankedLeaderboardEntry extends MetricsLeaderboardEntry {
  totalTokens: number;
  score: number;
  rank: number;
}

function trimTrailingZero(value: string): string {
  return value.replace(/\.0$/, "");
}

function formatCompactValue(value: number): string {
  const absoluteValue = Math.abs(value);
  if (absoluteValue >= 1_000_000) {
    return `${trimTrailingZero((value / 1_000_000).toFixed(1))}M`;
  }
  if (absoluteValue >= 1_000) {
    return `${trimTrailingZero((value / 1_000).toFixed(1))}k`;
  }
  return trimTrailingZero(value.toFixed(1));
}

export function buildAccountSummaryCards(
  accounts: AccountResponse[],
  cats: Cat[]
): SettingsSummaryCardModel[] {
  const accountIds = new Set(accounts.map((account) => account.id));
  const builtinCount = accounts.filter((account) => account.isBuiltin).length;
  const apiKeyCount = accounts.filter((account) => account.authType === "api_key").length;
  const subscriptionCount = accounts.filter(
    (account) => account.authType === "subscription"
  ).length;

  const boundCats = cats.filter((cat) => cat.accountRef && accountIds.has(cat.accountRef)).length;
  const unboundOrDetachedCats = cats.length - boundCats;
  const availableCats = cats.filter((cat) => cat.isAvailable).length;

  return [
    {
      id: "accounts",
      label: "Provider 账号",
      value: String(accounts.length),
      detail: `${builtinCount} 个内建 · ${Math.max(accounts.length - builtinCount, 0)} 个自定义`,
      tone: "neutral",
    },
    {
      id: "api-key",
      label: "API Key",
      value: String(apiKeyCount),
      detail: apiKeyCount > 0 ? `${apiKeyCount} 个密钥账号可独立配额` : "当前没有 API Key 账号",
      tone: apiKeyCount > 0 ? "accent" : "neutral",
    },
    {
      id: "subscription",
      label: "CLI 订阅",
      value: String(subscriptionCount),
      detail:
        subscriptionCount > 0 ? `${subscriptionCount} 个订阅账号走 CLI OAuth` : "当前没有订阅账号",
      tone: subscriptionCount > 0 ? "success" : "neutral",
    },
    {
      id: "binding",
      label: "猫咪绑定",
      value: `${boundCats}/${cats.length}`,
      detail: `${unboundOrDetachedCats} 只未绑定或绑定失效 · ${availableCats} 只当前可用`,
      tone: unboundOrDetachedCats > 0 ? "attention" : "success",
    },
  ];
}

export function buildGovernanceSummaryCards(
  projects: GovernanceProjectSnapshot[]
): SettingsSummaryCardModel[] {
  const totalProjects = projects.length;
  const healthyCount = projects.filter((project) => project.status === "healthy").length;
  const attentionCount = projects.filter((project) =>
    ["stale", "missing", "error"].includes(project.status)
  ).length;
  const findingsCount = projects.reduce((sum, project) => sum + project.findings.length, 0);
  const unconfirmedCount = projects.filter((project) => !project.confirmed).length;
  const neverSyncedCount = projects.filter((project) => project.status === "never-synced").length;
  const healthyPercent = totalProjects > 0 ? Math.round((healthyCount / totalProjects) * 100) : 0;

  return [
    {
      id: "projects",
      label: "治理项目",
      value: String(totalProjects),
      detail: `${healthyCount} 正常 · ${attentionCount} 需处理`,
      tone: "neutral",
    },
    {
      id: "healthy",
      label: "健康项目",
      value: String(healthyCount),
      detail: totalProjects > 0 ? `${healthyPercent}% 当前健康` : "尚未接入治理项目",
      tone: "success",
    },
    {
      id: "attention",
      label: "待处理",
      value: String(attentionCount),
      detail: findingsCount > 0 ? `${findingsCount} 条发现需要确认` : "当前没有异常发现",
      tone: attentionCount > 0 || findingsCount > 0 ? "attention" : "neutral",
    },
    {
      id: "activation",
      label: "激活队列",
      value: String(unconfirmedCount),
      detail: `${neverSyncedCount} 个未同步 · ${unconfirmedCount} 个待激活`,
      tone: unconfirmedCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildConnectorSummaryCards(
  connectors: ConnectorResponse[],
  bindingStatus: Record<string, ConnectorBindingStatus | undefined>
): SettingsSummaryCardModel[] {
  const enabledCount = connectors.filter((connector) => connector.enabled).length;
  const disabledCount = Math.max(connectors.length - enabledCount, 0);
  const featureCount = new Set(connectors.flatMap((connector) => connector.features)).size;
  const boundCount = connectors.filter((connector) => bindingStatus[connector.name]?.bound).length;
  const enabledUnboundCount = connectors.filter(
    (connector) => connector.enabled && !bindingStatus[connector.name]?.bound
  ).length;
  const pendingCount = disabledCount + enabledUnboundCount;

  return [
    {
      id: "channels",
      label: "通道类型",
      value: String(connectors.length),
      detail: `${enabledCount} 已启用 · ${disabledCount} 未启用`,
      tone: "neutral",
    },
    {
      id: "coverage",
      label: "能力覆盖",
      value: String(featureCount),
      detail: `来自 ${connectors.length} 个连接器声明的能力面`,
      tone: featureCount > 0 ? "accent" : "neutral",
    },
    {
      id: "bound",
      label: "已绑定",
      value: String(boundCount),
      detail: `${enabledUnboundCount} 个启用通道待绑定`,
      tone: boundCount > 0 ? "success" : "neutral",
    },
    {
      id: "pending",
      label: "待处理",
      value: String(pendingCount),
      detail: `${disabledCount} 个未启用 · ${enabledUnboundCount} 个待绑定`,
      tone: pendingCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildPermissionSummaryCards(
  cats: Cat[],
  definitions: PermissionSummaryDefinition[]
): SettingsSummaryCardModel[] {
  const totalCats = cats.length;
  const highRiskDefinitions = definitions.filter(
    (definition) => definition.riskLevel === "high"
  ).length;
  const mediumRiskDefinitions = definitions.filter(
    (definition) => definition.riskLevel === "medium"
  ).length;
  const highRiskIds = new Set(
    definitions
      .filter((definition) => definition.riskLevel === "high")
      .map((definition) => definition.id)
  );
  const definitionIds = new Set(definitions.map((definition) => definition.id));

  const configuredCats = cats.filter((cat) => (cat.permissions?.length ?? 0) > 0).length;
  const emptyCats = Math.max(totalCats - configuredCats, 0);
  const highRiskGrants = cats.reduce(
    (sum, cat) =>
      sum + (cat.permissions?.filter((permissionId) => highRiskIds.has(permissionId)).length ?? 0),
    0
  );
  const catsWithHighRisk = cats.filter((cat) =>
    cat.permissions?.some((permissionId) => highRiskIds.has(permissionId))
  ).length;
  const fullyPrivilegedCats = cats.filter((cat) => {
    const permissions = cat.permissions ?? [];
    if (permissions.length !== definitionIds.size || definitionIds.size === 0) {
      return false;
    }
    return permissions.every((permissionId) => definitionIds.has(permissionId));
  }).length;
  const reviewCount = emptyCats + fullyPrivilegedCats;

  return [
    {
      id: "permission-types",
      label: "权限项",
      value: String(definitions.length),
      detail: `${highRiskDefinitions} 项高风险 · ${mediumRiskDefinitions} 项中风险`,
      tone: "neutral",
    },
    {
      id: "configured-cats",
      label: "已配置猫咪",
      value: `${configuredCats}/${totalCats}`,
      detail: `${emptyCats} 只尚未配置任何权限`,
      tone: emptyCats > 0 ? "attention" : "success",
    },
    {
      id: "high-risk-grants",
      label: "高风险授权",
      value: String(highRiskGrants),
      detail: `${catsWithHighRisk} 只猫拥有高风险权限`,
      tone: highRiskGrants > 0 ? "attention" : "success",
    },
    {
      id: "review",
      label: "需复核",
      value: String(reviewCount),
      detail: `${emptyCats} 只空权限 · ${fullyPrivilegedCats} 只全权限`,
      tone: reviewCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildQuotaMetricSnapshot(
  catId: string,
  rows: CatMetricsRow[]
): QuotaMetricSnapshot {
  const totalInvocations = rows.length;
  const totalTokens = rows.reduce(
    (sum, row) => sum + (row.prompt_tokens || 0) + (row.completion_tokens || 0),
    0
  );
  const successRate =
    totalInvocations > 0 ? rows.filter((row) => row.success).length / totalInvocations : 1;
  const avgLatencyMs =
    totalInvocations > 0
      ? Math.round(rows.reduce((sum, row) => sum + (row.duration_ms || 0), 0) / totalInvocations)
      : 0;
  const trend: QuotaMetricSnapshot["trend"] =
    successRate > 0.95 ? "up" : successRate > 0.8 ? "stable" : "down";

  return {
    catId,
    totalInvocations,
    successRate,
    avgLatencyMs,
    totalTokens,
    trend,
  };
}

export function buildQuotaSummaryCards(
  metrics: QuotaMetricSnapshot[],
  totalCats: number
): SettingsSummaryCardModel[] {
  const activeCats = metrics.filter((metric) => metric.totalInvocations > 0).length;
  const totalInvocations = metrics.reduce((sum, metric) => sum + metric.totalInvocations, 0);
  const totalTokens = metrics.reduce((sum, metric) => sum + metric.totalTokens, 0);
  const averageTokensPerInvocation = totalInvocations > 0 ? totalTokens / totalInvocations : 0;
  const weightedSuccessRate =
    totalInvocations > 0
      ? metrics.reduce((sum, metric) => sum + metric.successRate * metric.totalInvocations, 0) /
        totalInvocations
      : 1;
  const lowSuccessCats = metrics.filter(
    (metric) => metric.totalInvocations > 0 && metric.successRate < 0.9
  ).length;
  const slowCats = metrics.filter(
    (metric) => metric.totalInvocations > 0 && metric.avgLatencyMs > 3000
  ).length;
  const downTrendCats = metrics.filter(
    (metric) => metric.totalInvocations > 0 && metric.trend === "down"
  ).length;
  const attentionCount = slowCats + downTrendCats;

  return [
    {
      id: "tokens",
      label: "Token 体量",
      value: formatCompactValue(totalTokens),
      detail: `${activeCats} 只猫有调用记录 · 单次平均 ${formatCompactValue(averageTokensPerInvocation)}`,
      tone: "neutral",
    },
    {
      id: "invocations",
      label: "调用总量",
      value: String(totalInvocations),
      detail: `${totalCats} 只猫中有 ${activeCats} 只在 7 天内活跃`,
      tone: activeCats > 0 ? "accent" : "neutral",
    },
    {
      id: "success",
      label: "整体成功率",
      value: `${(weightedSuccessRate * 100).toFixed(1)}%`,
      detail: `${lowSuccessCats} 只猫成功率低于 90%`,
      tone: lowSuccessCats > 0 ? "attention" : "success",
    },
    {
      id: "attention",
      label: "需复核",
      value: String(attentionCount),
      detail: `${slowCats} 只平均延迟高于 3s · ${downTrendCats} 只趋势下滑`,
      tone: attentionCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildEnvVarSummaryCards(vars: EnvVarResponse[]): SettingsSummaryCardModel[] {
  const totalVars = vars.length;
  const categoryCount = new Set(vars.map((envVar) => envVar.category)).size;
  const configuredCount = vars.filter((envVar) => envVar.isSet).length;
  const unsetCount = Math.max(totalVars - configuredCount, 0);
  const requiredVars = vars.filter((envVar) => envVar.required);
  const requiredCount = requiredVars.length;
  const requiredSetCount = requiredVars.filter((envVar) => envVar.isSet).length;
  const missingRequiredCount = Math.max(requiredCount - requiredSetCount, 0);
  const sensitiveCount = vars.filter((envVar) => envVar.sensitive).length;
  const enumeratedCount = vars.filter(
    (envVar) => envVar.allowedValues && envVar.allowedValues.length > 0
  ).length;

  return [
    {
      id: "variables",
      label: "环境变量",
      value: String(totalVars),
      detail: `覆盖 ${categoryCount} 个配置分类`,
      tone: "neutral",
    },
    {
      id: "configured",
      label: "已设置",
      value: `${configuredCount}/${totalVars}`,
      detail: `${unsetCount} 个变量尚未设置`,
      tone: unsetCount > 0 ? "attention" : "success",
    },
    {
      id: "required",
      label: "必需项",
      value: `${requiredSetCount}/${requiredCount}`,
      detail: `${missingRequiredCount} 个必需项缺失`,
      tone: missingRequiredCount > 0 ? "attention" : "success",
    },
    {
      id: "sensitive",
      label: "敏感与枚举",
      value: String(sensitiveCount),
      detail: `${sensitiveCount} 个敏感项 · ${enumeratedCount} 个枚举项`,
      tone: sensitiveCount > 0 || enumeratedCount > 0 ? "accent" : "neutral",
    },
  ];
}

export function rankLeaderboardEntries(
  entries: MetricsLeaderboardEntry[]
): RankedLeaderboardEntry[] {
  return entries
    .map((entry) => ({
      ...entry,
      totalTokens: entry.prompt_tokens + entry.completion_tokens,
      score: Math.round((entry.success_rate * 100 - entry.avg_duration_ms / 1000) * 10) / 10,
    }))
    .sort((left, right) => right.score - left.score)
    .map((entry, index) => ({
      ...entry,
      rank: index + 1,
    }));
}

export function buildLeaderboardSummaryCards(
  rankedEntries: RankedLeaderboardEntry[]
): SettingsSummaryCardModel[] {
  const totalCalls = rankedEntries.reduce((sum, entry) => sum + entry.total_calls, 0);
  const podiumCount = Math.min(rankedEntries.length, 3);
  const topEntry = rankedEntries[0];
  const averageSuccessRate =
    rankedEntries.length > 0
      ? rankedEntries.reduce((sum, entry) => sum + entry.success_rate, 0) / rankedEntries.length
      : 0;
  const excellentCats = rankedEntries.filter((entry) => entry.success_rate >= 0.95).length;
  const slowCats = rankedEntries.filter((entry) => entry.avg_duration_ms > 3000).length;
  const riskyCats = rankedEntries.filter((entry) => entry.success_rate < 0.9).length;
  const attentionCount = slowCats + riskyCats;

  return [
    {
      id: "participants",
      label: "参赛猫咪",
      value: String(rankedEntries.length),
      detail: `总调用 ${totalCalls} 次 · ${podiumCount} 只进入领奖台`,
      tone: "neutral",
    },
    {
      id: "champion",
      label: "当前冠军",
      value: topEntry ? topEntry.score.toFixed(1) : "0.0",
      detail: topEntry ? `${topEntry.cat_id} 当前排名第一` : "暂无排行数据",
      tone: topEntry ? "accent" : "neutral",
    },
    {
      id: "success",
      label: "平均成功率",
      value: `${(averageSuccessRate * 100).toFixed(1)}%`,
      detail: `${excellentCats} 只成功率达到 95%`,
      tone: riskyCats > 0 ? "attention" : "success",
    },
    {
      id: "attention",
      label: "待关注",
      value: String(attentionCount),
      detail: `${slowCats} 只平均延迟高于 3s · ${riskyCats} 只成功率低于 90%`,
      tone: attentionCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildCapabilitySummaryCards(
  items: CapabilityBoardItem[]
): SettingsSummaryCardModel[] {
  const totalItems = items.length;
  const mcpCount = items.filter((item) => item.type === "mcp").length;
  const skillCount = items.filter((item) => item.type === "skill").length;
  const globalEnabledCount = items.filter((item) => item.enabled).length;
  const globalDisabledCount = Math.max(totalItems - globalEnabledCount, 0);

  const overrideBranches = items.reduce((sum, item) => {
    return (
      sum +
      Object.values(item.cats).filter((enabledForCat) => enabledForCat !== item.enabled).length
    );
  }, 0);
  const itemsWithOverrides = items.filter((item) =>
    Object.values(item.cats).some((enabledForCat) => enabledForCat !== item.enabled)
  ).length;

  const probeAttentionCount = items.filter(
    (item) => item.type === "mcp" && ["error", "timeout"].includes(item.connectionStatus || "")
  ).length;
  const auditAttentionCount = items.filter(
    (item) =>
      item.type === "skill" && ["failed", "error", "missing"].includes(item.auditStatus || "")
  ).length;
  const attentionCount = probeAttentionCount + auditAttentionCount;

  return [
    {
      id: "capabilities",
      label: "能力条目",
      value: String(totalItems),
      detail: `${mcpCount} 个 MCP · ${skillCount} 个 Skill`,
      tone: "neutral",
    },
    {
      id: "global",
      label: "全局启用",
      value: `${globalEnabledCount}/${totalItems}`,
      detail: `${globalDisabledCount} 项当前全局关闭`,
      tone: globalEnabledCount > 0 ? "accent" : "neutral",
    },
    {
      id: "overrides",
      label: "单猫覆盖",
      value: String(overrideBranches),
      detail: `${overrideBranches} 个单猫覆盖分支 · ${itemsWithOverrides} 项能力受影响`,
      tone: overrideBranches > 0 ? "attention" : "success",
    },
    {
      id: "attention",
      label: "待关注",
      value: String(attentionCount),
      detail: `${probeAttentionCount} 个探测异常 · ${auditAttentionCount} 个审计异常`,
      tone: attentionCount > 0 ? "attention" : "success",
    },
  ];
}
