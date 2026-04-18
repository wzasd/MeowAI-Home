export const RIGHT_PANEL_TABS = [
  { key: "status", label: "总览" },
  { key: "tasks", label: "任务" },
  { key: "metrics", label: "指标" },
  { key: "audit", label: "审计" },
] as const;

export type RightPanelTabKey = (typeof RIGHT_PANEL_TABS)[number]["key"];
