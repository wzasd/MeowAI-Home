import { useState, useEffect } from "react";
import { Menu } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { ThreadSidebar } from "./components/thread/ThreadSidebar";
import { ChatArea } from "./components/chat/ChatArea";
import { ThemeToggle } from "./components/ui/ThemeToggle";
import { HealthGuard } from "./components/ui/HealthGuard";
import { useThemeStore } from "./stores/themeStore";

export default function App() {
  useWebSocket();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { isDarkMode } = useThemeStore();

  // Close mobile menu on escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMobileMenuOpen(false);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  return (
    <div
      className={`flex h-screen overflow-hidden bg-gray-50 transition-colors dark:bg-gray-900 ${isDarkMode ? "dark" : ""}`}
    >
      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar - Fixed overlay on mobile, flex item on desktop */}
      <aside
        className={`${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        } fixed left-0 top-0 z-30 h-full w-64 transform border-r border-gray-200 bg-white transition-transform duration-300 ease-in-out dark:border-gray-700 dark:bg-gray-800 lg:static lg:w-64 lg:translate-x-0 lg:transition-none xl:w-72`}
      >
        <ThreadSidebar onCloseMobile={() => setIsMobileMenuOpen(false)} />
      </aside>

      {/* Main content area */}
      <main className="relative flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        {/* Mobile header */}
        <header className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2 dark:border-gray-700 dark:bg-gray-800 lg:hidden">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="flex h-9 w-9 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="打开菜单"
            >
              <Menu size={20} className="text-gray-600 dark:text-gray-300" />
            </button>
            <span className="text-lg font-bold text-gray-800 dark:text-gray-100">MeowAI</span>
          </div>
          <ThemeToggle />
        </header>

        {/* Desktop theme toggle */}
        <div className="absolute right-4 top-3 z-10 hidden lg:block">
          <ThemeToggle />
        </div>

        {/* Chat area - takes remaining space */}
        <ChatArea />
      </main>

      {/* Health protection guard */}
      <HealthGuard />
    </div>
  );
}
