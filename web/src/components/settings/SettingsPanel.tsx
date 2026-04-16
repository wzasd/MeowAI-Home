import { useState } from "react";
import { X, Settings, Link, Variable, Palette, Cat, Shield, BarChart3, Zap, Trophy, Scale, Key, CalendarClock, GitPullRequest, Cpu } from "lucide-react";
import { ConnectorSettings } from "./ConnectorSettings";
import { EnvVarSettings } from "./EnvVarSettings";
import { CatSettings } from "./CatSettings";
import { AccountSettings } from "./AccountSettings";
import { AppearanceSettings } from "./AppearanceSettings";
import { CapabilityBoard } from "./CapabilityBoard";
import { QuotaBoard } from "./QuotaBoard";
import { LeaderboardTab } from "./LeaderboardTab";
import { PermissionsSettings } from "./PermissionsSettings";
import { GovernanceSettings } from "./GovernanceSettings";
import { TaskScheduler } from "./TaskScheduler";
import { ReviewPanel } from "./ReviewPanel";
import { LimbPanel } from "./LimbPanel";

type SettingsTab = "accounts" | "connectors" | "env" | "cats" | "appearance" | "capabilities" | "quota" | "leaderboard" | "permissions" | "governance" | "scheduler" | "review" | "limbs";

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("cats");

  if (!isOpen) return null;

  const tabs = [
    { id: "cats" as const, label: "猫咪管理", icon: Cat },
    { id: "accounts" as const, label: "AI Providers", icon: Key },
    { id: "capabilities" as const, label: "能力配置", icon: Zap },
    { id: "permissions" as const, label: "权限", icon: Shield },
    { id: "scheduler" as const, label: "任务调度", icon: CalendarClock },
    { id: "review" as const, label: "PR 审阅", icon: GitPullRequest },
    { id: "limbs" as const, label: "Limb 设备", icon: Cpu },
    { id: "governance" as const, label: "治理", icon: Scale },
    { id: "quota" as const, label: "配额看板", icon: BarChart3 },
    { id: "leaderboard" as const, label: "排行榜", icon: Trophy },
    { id: "connectors" as const, label: "连接器", icon: Link },
    { id: "env" as const, label: "环境变量", icon: Variable },
    { id: "appearance" as const, label: "外观", icon: Palette },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex h-[85vh] w-full max-w-5xl overflow-hidden rounded-xl bg-white shadow-2xl dark:bg-gray-800">
        {/* Sidebar */}
        <div className="w-56 border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
          <div className="flex items-center gap-2 border-b border-gray-200 p-4 dark:border-gray-700">
            <Settings size={20} className="text-gray-600 dark:text-gray-400" />
            <h2 className="font-semibold text-gray-800 dark:text-gray-200">MeowAI Hub</h2>
          </div>

          <nav className="space-y-0.5 p-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                    activeTab === tab.id
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      : "text-gray-700 hover:bg-gray-200 dark:text-gray-300 dark:hover:bg-gray-700"
                  }`}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="flex flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">
              {tabs.find((t) => t.id === activeTab)?.label}
            </h3>
            <button onClick={onClose} className="rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-700">
              <X size={20} className="text-gray-500 dark:text-gray-400" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "cats" && <CatSettings />}
            {activeTab === "accounts" && <AccountSettings />}
            {activeTab === "capabilities" && <CapabilityBoard />}
            {activeTab === "permissions" && <PermissionsSettings />}
            {activeTab === "scheduler" && <TaskScheduler />}
            {activeTab === "review" && <ReviewPanel />}
            {activeTab === "governance" && <GovernanceSettings />}
            {activeTab === "quota" && <QuotaBoard />}
            {activeTab === "leaderboard" && <LeaderboardTab />}
            {activeTab === "connectors" && <ConnectorSettings />}
            {activeTab === "env" && <EnvVarSettings />}
            {activeTab === "appearance" && <AppearanceSettings />}
            {activeTab === "limbs" && <LimbPanel />}
          </div>
        </div>
      </div>
    </div>
  );
}
