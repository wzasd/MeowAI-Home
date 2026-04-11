import { X, Reply } from "lucide-react";
import type { MessageResponse } from "../../types";

interface ReplyPillProps {
  message: MessageResponse;
  onCancel: () => void;
}

export function ReplyPill({ message, onCancel }: ReplyPillProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 dark:border-blue-800 dark:bg-blue-900/20">
      <Reply size={12} className="text-blue-500" />
      <span className="flex-1 truncate text-xs text-blue-700 dark:text-blue-400">
        回复: {message.content.slice(0, 60)}{message.content.length > 60 ? "..." : ""}
      </span>
      <button onClick={onCancel} className="rounded p-0.5 text-blue-400 hover:text-blue-600">
        <X size={12} />
      </button>
    </div>
  );
}
