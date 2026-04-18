import { useEffect, useState } from "react";
import {
  X,
  Settings,
  Link,
  Variable,
  Palette,
  Cat,
  Shield,
  Zap,
  Scale,
  Key,
  CalendarClock,
  GitPullRequest,
  Cpu,
  LayoutDashboard,
} from "lucide-react";
import { ConnectorSettings } from "./ConnectorSettings";
import { EnvVarSettings } from "./EnvVarSettings";
import { CatSettings } from "./CatSettings";
import { AccountSettings } from "./AccountSettings";
import { AppearanceSettings } from "./AppearanceSettings";
import { CapabilityBoard } from "./CapabilityBoard";
import { PermissionsSettings } from "./PermissionsSettings";
import { GovernanceSettings } from "./GovernanceSettings";
import { TaskScheduler } from "./TaskScheduler";
import { ReviewPanel } from "./ReviewPanel";
import { LimbPanel } from "./LimbPanel";
import { SettingsOverviewPage } from "./SettingsOverviewPage";
import { SettingsPageHero } from "./SettingsPageHero";
import {
  SETTINGS_GROUP_ORDER,
  findSettingsPage,
  getSettingsPagesByGroup,
  type SettingsGroupId,
  type SettingsPageId,
} from "./settingsRegistry";

const PAGE_ICONS = {
  overview: LayoutDashboard,
  cats: Cat,
  accounts: Key,
  connectors: Link,
  capabilities: Zap,
  permissions: Shield,
  env: Variable,
  appearance: Palette,
  scheduler: CalendarClock,
  review: GitPullRequest,
  limbs: Cpu,
  governance: Scale,
} as const;

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [activePage, setActivePage] = useState<SettingsPageId>("overview");

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const activeMeta = findSettingsPage(activePage);

  const renderPage = (pageId: SettingsPageId) => {
    switch (pageId) {
      case "overview":
        return <SettingsOverviewPage onSelectPage={setActivePage} />;
      case "cats":
        return <CatSettings />;
      case "accounts":
        return <AccountSettings />;
      case "capabilities":
        return <CapabilityBoard />;
      case "permissions":
        return <PermissionsSettings />;
      case "scheduler":
        return <TaskScheduler />;
      case "review":
        return <ReviewPanel />;
      case "governance":
        return <GovernanceSettings />;
      case "connectors":
        return <ConnectorSettings />;
      case "env":
        return <EnvVarSettings />;
      case "appearance":
        return <AppearanceSettings />;
      case "limbs":
        return <LimbPanel />;
      default:
        return null;
    }
  };

  const renderNavItem = (pageId: Exclude<SettingsPageId, "overview">) => {
    const meta = findSettingsPage(pageId);
    if (!meta) return null;
    const Icon = PAGE_ICONS[pageId];

    return (
      <button
        key={pageId}
        type="button"
        onClick={() => setActivePage(pageId)}
        className={`nest-r-sm flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
          activePage === pageId
            ? "bg-[linear-gradient(135deg,rgba(183,103,37,0.14),rgba(47,116,103,0.08))] text-[var(--accent-deep)] shadow-[inset_0_1px_0_rgba(255,255,255,0.28)] dark:text-[var(--accent)]"
            : "text-[var(--text-soft)] hover:bg-white/40 dark:hover:bg-white/5"
        }`}
      >
        <Icon size={16} className="shrink-0" />
        <span className="min-w-0 flex-1 truncate">{meta.label}</span>
        {meta.status === "migrating" && (
          <span className="inline-flex shrink-0 items-center rounded-full border border-[rgba(141,104,68,0.18)] bg-[rgba(141,104,68,0.08)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-soft)] dark:bg-[rgba(234,203,168,0.08)]">
            迁
          </span>
        )}
      </button>
    );
  };

  const renderGroup = (groupId: SettingsGroupId) => {
    const group = SETTINGS_GROUP_ORDER.find((item) => item.id === groupId);
    if (!group) return null;

    return (
      <div key={groupId} className="space-y-1.5">
        <div className="px-3">
          <div className="nest-kicker">{group.label}</div>
        </div>
        <div className="space-y-1">
          {getSettingsPagesByGroup(groupId).map((page) =>
            renderNavItem(page.id as Exclude<SettingsPageId, "overview">)
          )}
        </div>
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="nest-panel-strong nest-r-2xl flex h-[85vh] w-full max-w-6xl overflow-hidden"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="w-64 border-r border-[var(--line)] bg-white/10 p-3 dark:bg-white/5">
          <div className="border-b border-[var(--line)] px-3 pb-4 pt-2">
            <div className="flex items-center gap-2">
              <Settings size={20} className="text-[var(--accent)]" />
              <div>
                <div className="nest-kicker">设置台</div>
                <h2 className="nest-title mt-1 font-semibold text-[var(--text-strong)]">
                  猫窝设置台
                </h2>
              </div>
            </div>
          </div>

          <nav className="mt-3 space-y-4">
            <button
              type="button"
              onClick={() => setActivePage("overview")}
              className={`nest-r-sm flex w-full items-center gap-3 px-3 py-3 text-left text-sm transition-colors ${
                activePage === "overview"
                  ? "bg-[linear-gradient(135deg,rgba(183,103,37,0.16),rgba(47,116,103,0.1))] text-[var(--accent-deep)] shadow-[inset_0_1px_0_rgba(255,255,255,0.32)] dark:text-[var(--accent)]"
                  : "text-[var(--text-soft)] hover:bg-white/40 dark:hover:bg-white/5"
              }`}
            >
              <LayoutDashboard size={16} className="shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="font-medium">设置总览</div>
                <div className="mt-1 text-[11px] text-[var(--text-faint)]">
                  先看入口，再决定当前要处理哪一块
                </div>
              </div>
            </button>

            {SETTINGS_GROUP_ORDER.map((group) => renderGroup(group.id))}
          </nav>
        </div>

        <div className="flex flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-[var(--line)] px-6 py-4">
            <div>
              <div className="nest-kicker">当前视图</div>
              <h3 className="nest-title mt-1 text-xl font-semibold text-[var(--text-strong)]">
                {activeMeta?.label ?? "设置总览"}
              </h3>
            </div>
            <button
              onClick={onClose}
              className="nest-button-ghost flex h-9 w-9 items-center justify-center rounded-full"
            >
              <X size={20} className="text-[var(--text-soft)]" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {activePage === "overview" ? (
              <div className="space-y-5">
                <SettingsPageHero
                  eyebrow={activeMeta?.eyebrow ?? "Settings Overview"}
                  title={activeMeta?.label ?? "设置总览"}
                  description={
                    activeMeta?.description ?? "先看四组工作入口，再决定当前要处理哪一块。"
                  }
                  saveMode={activeMeta?.saveMode ?? "navigate"}
                  status={activeMeta?.status}
                />
                {renderPage(activePage)}
              </div>
            ) : (
              <div className="space-y-5">
                <SettingsPageHero
                  eyebrow={activeMeta?.eyebrow ?? "当前设置"}
                  title={activeMeta?.label ?? "设置"}
                  description={activeMeta?.description ?? ""}
                  saveMode={activeMeta?.saveMode ?? "mixed"}
                  status={activeMeta?.status}
                />
                <div className="nest-panel nest-r-xl p-4 lg:p-5">{renderPage(activePage)}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
