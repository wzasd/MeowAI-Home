import { useChatStore } from "../../stores/chatStore";
import { CAT_INFO } from "../../types";

export function StreamingIndicator() {
  const streamingResponses = useChatStore((s) => s.streamingResponses);
  const cats = Array.from(streamingResponses.keys());

  if (cats.length === 0) return null;

  return (
    <div className="flex items-center gap-2 bg-blue-50 px-6 py-2">
      <div className="flex items-center gap-1">
        {cats.map((catId) => {
          const info = CAT_INFO[catId] || { name: catId, emoji: "🐾" };
          return (
            <span key={catId} className="text-sm">
              {info.emoji}
            </span>
          );
        })}
      </div>
      <span className="animate-pulse text-sm text-blue-600">
        {cats.length === 1 ? "正在思考..." : `${cats.length} 只猫正在思考...`}
      </span>
    </div>
  );
}
