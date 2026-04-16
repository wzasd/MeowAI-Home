import { useState, useEffect } from "react";
import { Menu, Settings, Inbox, Target, Code, MessageSquare, PanelRightOpen, PanelRightClose } from "lucide-react";
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
import { useAuthStore } from "./stores/authStore";
import { LoginModal } from "./components/auth/LoginModal";

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
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState<Page>("chat");
  const { isDarkMode } = useThemeStore();
  const token = useAuthStore((s) => s.token);
  const isAuthLoading = useAuthStore((s) => s.isLoading);
  const initAuth = useAuthStore((s) => s.init);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  // Close mobile menu on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMobileMenuOpen(false);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  if (isAuthLoading) {
    return (
      <div className={`flex h-screen items-center justify-center bg-gray-50 transition-colors dark:bg-gray-900 ${isDarkMode ? "dark" : ""}`}>
        <div className="text-gray-500 dark:text-gray-400">初始化中...</div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className={`flex h-screen overflow-hidden bg-gray-50 transition-colors dark:bg-gray-900 ${isDarkMode ? "dark" : ""}`}>
        <LoginModal />
      </div>
    );
  }

  return (
    <div className={`flex h-screen overflow-hidden bg-gray-50 transition-colors dark:bg-gray-900 ${isDarkMode ? "dark" : ""}`}>
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-20 bg-black/50 lg:hidden" onClick={() => setIsMobileMenuOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        } fixed left-0 top-0 z-30 flex h-full w-64 flex-col border-r border-gray-200 bg-white transition-transform duration-300 ease-in-out dark:border-gray-700 dark:bg-gray-800 lg:static lg:w-64 lg:translate-x-0 lg:transition-none xl:w-72`}
      >
        {/* Nav tabs at top of sidebar */}
        <div className="flex shrink-0 items-center justify-between border-b border-gray-200 px-2 py-2 dark:border-gray-700">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => { setCurrentPage(item.key); setIsMobileMenuOpen(false); }}
              className={`flex flex-1 items-center justify-center gap-1 rounded px-1 py-1.5 text-xs font-medium transition-colors ${
                currentPage === item.key
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              }`}
              title={item.label}
            >
              <item.icon size={14} />
              <span className="hidden lg:inline">{item.shortLabel}</span>
            </button>
          ))}
        </div>
        <ThreadSidebar onCloseMobile={() => setIsMobileMenuOpen(false)} onOpenSettings={() => setIsSettingsOpen(true)} />
      </aside>

      {/* Main content area */}
      <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2 dark:border-gray-700 dark:bg-gray-800 lg:hidden">
          <div className="flex items-center gap-3">
            <button onClick={() => setIsMobileMenuOpen(true)} className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" aria-label="打开菜单">
              <Menu size={20} className="text-gray-600 dark:text-gray-300" />
            </button>
            <span className="text-lg font-bold text-gray-800 dark:text-gray-100">MeowAI</span>
          </div>
          <div className="flex items-center gap-1">
            {currentPage === "chat" && (
              <button onClick={() => setIsRightPanelOpen(!isRightPanelOpen)} className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700">
                {isRightPanelOpen ? <PanelRightClose size={18} className="text-gray-600 dark:text-gray-300" /> : <PanelRightOpen size={18} className="text-gray-600 dark:text-gray-300" />}
              </button>
            )}
            <button onClick={() => setIsSettingsOpen(true)} className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" aria-label="设置">
              <Settings size={18} className="text-gray-600 dark:text-gray-300" />
            </button>
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Main page */}
          <div className="relative flex-1 overflow-hidden">
            {currentPage === "chat" && (
              <ChatArea
                isRightPanelOpen={isRightPanelOpen}
                onToggleRightPanel={() => setIsRightPanelOpen(!isRightPanelOpen)}
              />
            )}
            {currentPage === "signals" && <SignalInboxPage />}
            {currentPage === "mission" && <MissionHubPage />}
            {currentPage === "workspace" && <WorkspacePanel />}
          </div>

          {/* Right panel (chat only) */}
          {currentPage === "chat" && isRightPanelOpen && (
            <RightStatusPanel
              threadId={null}
              isOpen={isRightPanelOpen}
              onClose={() => setIsRightPanelOpen(false)}
            />
          )}
        </div>
      </main>

      <HealthGuard />
      <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
}
