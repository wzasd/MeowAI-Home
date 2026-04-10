import { useThreadStore } from "../../stores/threadStore";
import { useChatStore } from "../../stores/chatStore";
import { useRef, useEffect } from "react";
import { MessageBubble } from "./MessageBubble";
import { InputBar } from "./InputBar";
import { StreamingIndicator } from "./StreamingIndicator";
import { AgentBadge } from "./AgentBadge";
import { IntentBadge } from "./IntentBadge";
import { ThinkingPanel } from "./ThinkingPanel";
import { ExportButton } from "./ExportButton";
import { formatDateTime } from "../../types";

// Helper function to get cat emoji
const CAT_EMOJIS: Record<string, string> = {
  orange: "🐱",
  inky: "🐾",
  patch: "🌸",
};

export function ChatArea() {
  const currentThread = useThreadStore((s) => s.currentThread);
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const streamingResponses = useChatStore((s) => s.streamingResponses);
  const streamingThinking = useChatStore((s) => s.streamingThinking);
  const fetchMessages = useChatStore((s) => s.fetchMessages);
  const activeSkill = useChatStore((s) => s.activeSkill);
  const intentMode = useChatStore((s) => s.intentMode);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch messages when thread changes
  useEffect(() => {
    if (currentThread) {
      fetchMessages(currentThread.id);
    }
  }, [currentThread?.id]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingResponses]);

  if (!currentThread) {
    return (
      <div className="flex h-full flex-1 items-center justify-center text-gray-400 dark:text-gray-600">
        <div className="text-center">
          <div className="mb-4 text-6xl">🐱</div>
          <p className="text-lg dark:text-gray-400">选择或创建一个对话开始聊天</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-1 flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800 lg:pr-16">
        <div className="flex min-w-0 items-center gap-3">
          <span className="text-lg lg:hidden">
            {CAT_EMOJIS[currentThread.current_cat_id] || "🐱"}
          </span>
          <h2 className="truncate text-sm font-semibold text-gray-800 dark:text-gray-100">
            {currentThread.name}
          </h2>
          {intentMode && <IntentBadge mode={intentMode} />}
          {activeSkill && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              {activeSkill}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ExportButton />
          <div className="hidden text-xs text-gray-400 dark:text-gray-500 sm:block">
            创建于 {formatDateTime(currentThread.created_at)}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-1 overflow-y-auto bg-gray-50/50 px-4 py-4 dark:bg-gray-900/50 lg:px-6">
        {messages.length === 0 && !isStreaming && (
          <div className="mt-20 text-center text-gray-400 dark:text-gray-500">
            <p className="dark:text-gray-400">开始与猫猫对话吧！</p>
            <p className="mt-1 text-sm">
              输入{" "}
              <code className="rounded bg-gray-100 px-1 text-xs dark:bg-gray-700 dark:text-gray-300">
                @dev
              </code>{" "}
              开发猫,{" "}
              <code className="rounded bg-gray-100 px-1 text-xs dark:bg-gray-700 dark:text-gray-300">
                @review
              </code>{" "}
              审查猫,{" "}
              <code className="rounded bg-gray-100 px-1 text-xs dark:bg-gray-700 dark:text-gray-300">
                @research
              </code>{" "}
              研究猫
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}

        {/* Streaming responses */}
        {Array.from(streamingResponses.values()).map((resp) => (
          <div key={resp.catId} className="mb-4 flex justify-start">
            <AgentBadge catId={resp.catId} />
            <div className="max-w-[70%]">
              {/* Streaming thinking panel */}
              {streamingThinking.get(resp.catId) && (
                <ThinkingPanel
                  content={streamingThinking.get(resp.catId)!}
                  catId={resp.catId}
                  catName={resp.catName}
                />
              )}
              <div className="rounded-2xl border bg-white px-4 py-2 shadow-sm dark:border-gray-600 dark:bg-gray-800">
                <p className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                  {resp.content}
                </p>
                <span className="animate-pulse text-gray-400 dark:text-gray-500">|</span>
              </div>
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Streaming indicator */}
      {isStreaming && <StreamingIndicator />}

      {/* Input */}
      <InputBar disabled={isStreaming} />
    </div>
  );
}
