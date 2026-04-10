import type { MessageResponse } from "../../types";
import { AgentBadge } from "./AgentBadge";
import { ThinkingPanel } from "./ThinkingPanel";
import { MarkdownContent } from "./MarkdownContent";
import { TTSButton } from "./TTSButton";
import { CAT_INFO, formatTime } from "../../types";

interface MessageBubbleProps {
  message: MessageResponse;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} group mb-4`}>
      {!isUser && message.cat_id && <AgentBadge catId={message.cat_id} />}

      <div className="flex max-w-[70%] flex-col">
        {/* Thinking panel for assistant messages */}
        {!isUser && message.thinking && message.cat_id && (
          <ThinkingPanel
            content={message.thinking}
            catId={message.cat_id}
            catName={message.cat_id}
          />
        )}

        <div
          className={`rounded-2xl px-4 py-2.5 ${
            isUser
              ? "bg-blue-500 text-white"
              : "border border-gray-200 bg-white text-gray-800 shadow-sm"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="text-sm leading-relaxed">
              <MarkdownContent content={message.content} />
            </div>
          )}
        </div>

        {/* Timestamp and TTS */}
        <div
          className={`mt-1 flex items-center gap-2 text-[10px] text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 ${
            isUser ? "justify-end" : "justify-start"
          }`}
        >
          <span>{formatTime(message.timestamp)}</span>
          {!isUser && message.cat_id && (
            <TTSButton
              content={message.content}
              catName={CAT_INFO[message.cat_id]?.name || message.cat_id}
            />
          )}
        </div>
      </div>
    </div>
  );
}
