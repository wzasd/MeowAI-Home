/** Thinking content collapsible panel - shows cat's reasoning process */

import { useState } from "react";
import { Brain, ChevronDown } from "lucide-react";

interface ThinkingPanelProps {
  content: string;
  catId: string;
  catName: string;
}

const CAT_COLORS: Record<string, { bg: string; border: string; icon: string }> = {
  orange: { bg: "bg-orange-50", border: "border-orange-200", icon: "text-orange-500" },
  inky: { bg: "bg-purple-50", border: "border-purple-200", icon: "text-purple-500" },
  patch: { bg: "bg-pink-50", border: "border-pink-200", icon: "text-pink-500" },
};

export function ThinkingPanel({ content, catId, catName }: ThinkingPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const colors = CAT_COLORS[catId] || {
    bg: "bg-gray-50",
    border: "border-gray-200",
    icon: "text-gray-500",
  };

  // Preview: first 60 chars
  const preview = content.slice(0, 60) + (content.length > 60 ? "..." : "");

  return (
    <div className={`my-2 rounded-lg border ${colors.border} ${colors.bg} overflow-hidden`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-opacity hover:opacity-80"
      >
        <Brain size={14} className={colors.icon} />
        <span className="text-xs font-medium text-gray-600">{catName}的思考</span>
        <ChevronDown
          size={14}
          className={`ml-auto text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
        />
      </button>

      {isExpanded ? (
        <div className="px-3 pb-3">
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-gray-600">{content}</p>
        </div>
      ) : (
        <button onClick={() => setIsExpanded(true)} className="block w-full px-3 pb-2 text-left">
          <p className="truncate text-xs text-gray-400">{preview}</p>
        </button>
      )}
    </div>
  );
}
