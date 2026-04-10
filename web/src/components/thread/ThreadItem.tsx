import type { ThreadResponse } from "../../types";
import { MessageSquare } from "lucide-react";

interface ThreadItemProps {
  thread: ThreadResponse;
  isActive: boolean;
  onSelect: () => void;
}

export function ThreadItem({ thread, isActive, onSelect }: ThreadItemProps) {
  return (
    <button
      onClick={onSelect}
      className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors ${
        isActive
          ? "border-r-2 border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20"
          : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
      }`}
    >
      <MessageSquare
        size={16}
        className={`mt-0.5 shrink-0 ${isActive ? "text-blue-500 dark:text-blue-400" : "text-gray-400 dark:text-gray-500"}`}
      />
      <div className="min-w-0 flex-1">
        <div
          className={`truncate text-sm font-medium ${isActive ? "text-gray-800 dark:text-gray-100" : "text-gray-700 dark:text-gray-300"}`}
        >
          {thread.name}
        </div>
        <div className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
          {thread.message_count} 条消息
        </div>
      </div>
    </button>
  );
}
