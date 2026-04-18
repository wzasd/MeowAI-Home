import type { RightPanelTabKey } from "./panelLayout";

export function getRightPanelSubtitle(
  activeTab: RightPanelTabKey,
  threadId: string | null
): string {
  if (activeTab === "metrics") {
    return "全局指标与跨猫表现";
  }

  if (activeTab === "audit") {
    return "系统审计与安全观察";
  }

  if (threadId) {
    return `当前线程 ${threadId.slice(0, 8)}`;
  }

  if (activeTab === "tasks") {
    return "未选线程时展示全局任务";
  }

  return "未选线程时展示全局运行态";
}
