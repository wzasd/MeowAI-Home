/** Dark mode toggle button */

import { Moon, Sun } from "lucide-react";
import { useThemeStore } from "../../stores/themeStore";

export function ThemeToggle() {
  const { isDarkMode, toggleDarkMode } = useThemeStore();

  return (
    <button
      onClick={toggleDarkMode}
      className="nest-button-secondary flex h-9 w-9 items-center justify-center rounded-full"
      title={isDarkMode ? "切换到浅色模式" : "切换到深色模式"}
    >
      {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}
