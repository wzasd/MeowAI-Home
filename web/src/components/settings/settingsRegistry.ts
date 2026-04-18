export type SettingsPageId =
  | "overview"
  | "cats"
  | "accounts"
  | "connectors"
  | "capabilities"
  | "permissions"
  | "env"
  | "appearance"
  | "scheduler"
  | "review"
  | "limbs"
  | "governance";

export type SettingsGroupId = "identity" | "runtime" | "automation" | "observability";

export type SettingsSaveMode = "navigate" | "auto" | "manual" | "mixed" | "readonly";

export type SettingsPageStatus = "active" | "migrating";

export interface SettingsGroupMeta {
  id: SettingsGroupId;
  label: string;
  description: string;
}

export interface SettingsPageMeta {
  id: SettingsPageId;
  label: string;
  eyebrow: string;
  description: string;
  group: SettingsGroupId | null;
  saveMode: SettingsSaveMode;
  status: SettingsPageStatus;
  keywords: string[];
}

export interface SettingsOverviewCard {
  groupId: SettingsGroupId;
  title: string;
  description: string;
  targetPageId: SettingsPageId;
  pageCount: number;
  flagLabel?: string;
  pageLabels: string[];
}

export const SETTINGS_GROUP_ORDER: readonly SettingsGroupMeta[] = [
  {
    id: "identity",
    label: "身份与接入",
    description: "管理猫咪、账号和连接入口。",
  },
  {
    id: "runtime",
    label: "运行与策略",
    description: "调整能力、权限、环境与外观偏好。",
  },
  {
    id: "automation",
    label: "协作与自动化",
    description: "管理调度、审阅流程与设备接入。",
  },
  {
    id: "observability",
    label: "治理与观察",
    description: "查看治理状态，并通过右侧状态台观察运行指标。",
  },
] as const;

const SETTINGS_PAGES: readonly SettingsPageMeta[] = [
  {
    id: "overview",
    label: "设置总览",
    eyebrow: "Settings Overview",
    description: "先看四组工作入口，再决定当前要处理哪一块。",
    group: null,
    saveMode: "navigate",
    status: "active",
    keywords: ["overview", "总览", "入口", "导航"],
  },
  {
    id: "cats",
    label: "猫咪管理",
    eyebrow: "身份与接入",
    description: "管理猫咪身份、个性和运行来源。先选账号，Provider 和模型自动跟随。",
    group: "identity",
    saveMode: "manual",
    status: "active",
    keywords: ["cat", "猫咪", "身份", "模型", "mention"],
  },
  {
    id: "accounts",
    label: "AI Provider 编排",
    eyebrow: "身份与接入",
    description: "管理 Provider 运行通道、账号健康和猫咪绑定编排。",
    group: "identity",
    saveMode: "manual",
    status: "active",
    keywords: ["account", "provider", "api key", "subscription", "绑定"],
  },
  {
    id: "connectors",
    label: "连接器",
    eyebrow: "身份与接入",
    description: "配置对外连接入口，确认通道是否可用。",
    group: "identity",
    saveMode: "manual",
    status: "active",
    keywords: ["connector", "连接器", "webhook", "feishu", "telegram"],
  },
  {
    id: "capabilities",
    label: "能力配置",
    eyebrow: "运行与策略",
    description: "设置默认能力策略，后续可扩展到单猫覆盖。",
    group: "runtime",
    saveMode: "auto",
    status: "active",
    keywords: ["capability", "skill", "mcp", "能力", "探测"],
  },
  {
    id: "permissions",
    label: "权限",
    eyebrow: "运行与策略",
    description: "控制可执行动作和风险边界。",
    group: "runtime",
    saveMode: "auto",
    status: "active",
    keywords: ["permission", "权限", "risk", "网络", "执行命令"],
  },
  {
    id: "env",
    label: "环境变量",
    eyebrow: "运行与策略",
    description: "查看和修改运行时依赖的关键环境配置。",
    group: "runtime",
    saveMode: "manual",
    status: "active",
    keywords: ["env", "环境变量", "token", "secret", "redis"],
  },
  {
    id: "appearance",
    label: "外观",
    eyebrow: "运行与策略",
    description: "调整主题、视觉偏好和展示风格。",
    group: "runtime",
    saveMode: "manual",
    status: "active",
    keywords: ["appearance", "外观", "theme", "主题", "dark mode"],
  },
  {
    id: "scheduler",
    label: "任务调度",
    eyebrow: "协作与自动化",
    description: "管理定时任务和自动化执行入口。",
    group: "automation",
    saveMode: "auto",
    status: "active",
    keywords: ["scheduler", "调度", "task", "cron", "定时"],
  },
  {
    id: "review",
    label: "PR 审阅",
    eyebrow: "协作与自动化",
    description: "查看评审流程和当前的 PR 协作状态。",
    group: "automation",
    saveMode: "mixed",
    status: "active",
    keywords: ["review", "pr", "审阅", "github", "pull request"],
  },
  {
    id: "limbs",
    label: "Limb 设备",
    eyebrow: "协作与自动化",
    description: "管理外部设备节点和远程能力接入。",
    group: "automation",
    saveMode: "mixed",
    status: "active",
    keywords: ["limb", "device", "设备", "mobile", "remote"],
  },
  {
    id: "governance",
    label: "治理",
    eyebrow: "治理与观察",
    description: "查看项目治理状态，识别缺失、过期和待同步项。",
    group: "observability",
    saveMode: "mixed",
    status: "active",
    keywords: ["governance", "治理", "同步", "project", "健康"],
  },
] as const;

export function listSettingsPages(): SettingsPageMeta[] {
  return [...SETTINGS_PAGES];
}

export function findSettingsPage(id: SettingsPageId): SettingsPageMeta | undefined {
  return SETTINGS_PAGES.find((page) => page.id === id);
}

export function getSettingsPagesByGroup(groupId: SettingsGroupId): SettingsPageMeta[] {
  return SETTINGS_PAGES.filter((page) => page.group === groupId);
}

export function buildSettingsOverviewCards(): SettingsOverviewCard[] {
  return SETTINGS_GROUP_ORDER.map((group) => {
    const pages = getSettingsPagesByGroup(group.id);
    const migratingCount = pages.filter((page) => page.status === "migrating").length;

    return {
      groupId: group.id,
      title: group.label,
      description: group.description,
      targetPageId: pages[0]?.id ?? "overview",
      pageCount: pages.length,
      flagLabel: migratingCount > 0 ? "观察项含迁出页" : undefined,
      pageLabels: pages.map((page) => page.label),
    };
  });
}
