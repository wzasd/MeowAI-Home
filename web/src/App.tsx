import { useState, useEffect } from "react";
import {
  Menu,
  Settings,
  Inbox,
  Target,
  Code,
  MessageSquare,
  PanelRightOpen,
  PanelRightClose,
} from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { ThreadSidebar } from "./components/thread/ThreadSidebar";
import { ChatArea } from "./components/chat/ChatArea";
import { ThemeToggle } from "./components/ui/ThemeToggle";
import { HealthGuard } from "./components/ui/HealthGuard";
import { SettingsPanel } from "./components/settings/SettingsPanel";
import { RightStatusPanel } from "./components/right-panel/RightStatusPanel";
import { SignalInboxPage } from "./components/signals/SignalInboxPage";
import { MissionHubPage } from "./components/mission/MissionHubPage";
import { WorkspacePanel } from "./components/workspace/WorkspacePanel";
import { useThemeStore } from "./stores/themeStore";
import { useChatStore } from "./stores/chatStore";
import { useThreadStore } from "./stores/threadStore";
import { SlidingNav } from "./components/ui/SlidingNav";

type Page = "chat" | "signals" | "mission" | "workspace";

const NAV_ITEMS: { key: Page; icon: typeof MessageSquare; label: string; shortLabel: string }[] = [
  { key: "chat", icon: MessageSquare, label: "对话", shortLabel: "对话" },
  { key: "signals", icon: Inbox, label: "收件箱", shortLabel: "收件箱" },
  { key: "mission", icon: Target, label: "任务看板", shortLabel: "任务" },
  { key: "workspace", icon: Code, label: "工作区", shortLabel: "工作区" },
];

export default function App() {
  useWebSocket();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState<boolean>(false);
  const [currentPage, setCurrentPage] = useState<Page>("chat");
  const { isDarkMode } = useThemeStore();
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const currentNav = NAV_ITEMS.find((item) => item.key === currentPage) ?? NAV_ITEMS[0]!;

  // Reset stale streaming state on mount (e.g. after HMR or page reload)
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  useEffect(() => { stopStreaming(); }, [stopStreaming]);

  // Close mobile menu on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsMobileMenuOpen(false);
        setIsSettingsOpen(false);
        setIsRightPanelOpen(false);
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  return (
    <div className={isDarkMode ? "dark" : ""}>
      <div className="relative flex h-screen overflow-hidden bg-[var(--bg-canvas)] text-[var(--text-strong)] transition-colors lg:gap-4 lg:p-4">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute left-[-8%] top-[-10%] h-80 w-80 rounded-full bg-[radial-gradient(circle,rgba(229,162,93,0.28),transparent_66%)] blur-3xl" />
          <div className="absolute bottom-[-18%] right-[-10%] h-[26rem] w-[26rem] rounded-full bg-[radial-gradient(circle,rgba(54,129,112,0.18),transparent_64%)] blur-3xl" />
        </div>

        {isMobileMenuOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/35 backdrop-blur-sm lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        )}

        <aside
          className={`${
            isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
          } fixed left-4 top-4 z-30 flex h-[calc(100%-2rem)] w-[20rem] flex-col transition-transform duration-300 ease-in-out lg:static lg:left-auto lg:top-auto lg:h-full lg:w-72 lg:translate-x-0 lg:transition-none`}
        >
          <div className="nest-panel-strong nest-r-2xl flex h-full min-h-0 flex-col overflow-hidden">
            <div className="border-b border-[var(--line)] px-3 py-3">
              <SlidingNav
                items={NAV_ITEMS.map((item) => ({
                  key: item.key,
                  icon: item.icon,
                  label: item.shortLabel,
                }))}
                activeKey={currentPage}
                onChange={(key) => {
                  setCurrentPage(key as Page);
                  setIsMobileMenuOpen(false);
                }}
              />
            </div>
            <ThreadSidebar
              onCloseMobile={() => setIsMobileMenuOpen(false)}
              onOpenSettings={() => setIsSettingsOpen(true)}
            />
          </div>
        </aside>

        <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden">
          <header className="px-3 pt-3 lg:hidden">
            <div className="nest-panel nest-r-lg flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setIsMobileMenuOpen(true)}
                  className="nest-button-ghost flex h-9 w-9 items-center justify-center rounded-full"
                  aria-label="打开菜单"
                >
                  <Menu size={20} className="text-[var(--text-soft)]" />
                </button>
                <div>
                  <div className="nest-kicker">猫窝工作室</div>
                  <div className="nest-title text-base font-semibold">{currentNav.label}</div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                {currentPage === "chat" && (
                  <button
                    onClick={() => setIsRightPanelOpen(!isRightPanelOpen)}
                    className="nest-button-ghost flex h-9 w-9 items-center justify-center rounded-full"
                  >
                    {isRightPanelOpen ? (
                      <PanelRightClose size={18} className="text-[var(--text-soft)]" />
                    ) : (
                      <PanelRightOpen size={18} className="text-[var(--text-soft)]" />
                    )}
                  </button>
                )}
                <button
                  onClick={() => setIsSettingsOpen(true)}
                  className="nest-button-ghost flex h-9 w-9 items-center justify-center rounded-full"
                  aria-label="设置"
                >
                  <Settings size={18} className="text-[var(--text-soft)]" />
                </button>
                <ThemeToggle />
              </div>
            </div>
          </header>

          <div className="flex flex-1 overflow-hidden p-3 pt-2 lg:gap-4 lg:p-0">
            <div className="nest-panel-strong nest-r-2xl relative flex-1 overflow-hidden">
              {currentPage === "chat" && (
                <ChatArea
                  isRightPanelOpen={isRightPanelOpen}
                  onToggleRightPanel={() => setIsRightPanelOpen(!isRightPanelOpen)}
                />
              )}
              {currentPage === "signals" && <SignalInboxPage />}
              {currentPage === "mission" && (
                <MissionHubPage
                  onOpenThread={(threadId) => {
                    useThreadStore.getState().selectThread(threadId);
                    setCurrentPage("chat");
                  }}
                />
              )}
              {currentPage === "workspace" && <WorkspacePanel />}
            </div>

            {currentPage === "chat" && isRightPanelOpen && (
              <RightStatusPanel
                threadId={currentThreadId}
                isOpen={isRightPanelOpen}
                onClose={() => setIsRightPanelOpen(false)}
              />
            )}
          </div>
        </main>

        <HealthGuard />
        <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      </div>
    </div>
  );
}
