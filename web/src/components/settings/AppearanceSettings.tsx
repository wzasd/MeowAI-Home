import { useThemeStore } from "../../stores/themeStore";
import { Moon, Sun, Monitor } from "lucide-react";

export function AppearanceSettings() {
  const { isDarkMode, setDarkMode } = useThemeStore();

  return (
    <div className="space-y-6">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        自定义 MeowAI 的外观和主题。
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">主题</h4>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <button
            onClick={() => isDarkMode && setDarkMode(false)}
            className={`flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors ${
              !isDarkMode
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
            }`}
          >
            <Sun size={24} className="text-amber-500" />
            <span className="text-sm">浅色</span>
          </button>

          <button
            onClick={() => !isDarkMode && setDarkMode(true)}
            className={`flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors ${
              isDarkMode
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                : "border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700"
            }`}
          >
            <Moon size={24} className="text-indigo-500" />
            <span className="text-sm">深色</span>
          </button>

          <button className="flex flex-col items-center gap-2 rounded-lg border border-gray-200 p-4 opacity-50 cursor-not-allowed dark:border-gray-700">
            <Monitor size={24} className="text-gray-500" />
            <span className="text-sm">系统</span>
          </button>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h4 className="font-medium text-gray-900 dark:text-gray-100">语言</h4>
        <div className="mt-3">
          <select
            disabled
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
          >
            <option>简体中文</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">更多语言支持即将推出</p>
        </div>
      </div>
    </div>
  );
}
