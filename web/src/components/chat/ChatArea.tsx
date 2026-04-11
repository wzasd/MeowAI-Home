import { useThreadStore } from "../../stores/threadStore";
import { useChatStore } from "../../stores/chatStore";
import { api } from "../../api/client";
import { useRef, useEffect, useState } from "react";
import { MessageBubble } from "./MessageBubble";
import { InputBar } from "./InputBar";
import { StreamingIndicator } from "./StreamingIndicator";
import { AgentBadge } from "./AgentBadge";
import { IntentBadge } from "./IntentBadge";
import { ThinkingPanel } from "./ThinkingPanel";
import { SessionStatus } from "../session/SessionStatus";
import { ExportButton } from "./ExportButton";
import { CatSelector } from "../cat/CatSelector";
import { HistorySearchModal } from "./HistorySearchModal";
import type { MessageResponse } from "../../types";
import { formatDateTime } from "../../types";
import { PanelRightOpen, PanelRightClose } from "lucide-react";

interface ChatAreaProps {
  isRightPanelOpen?: boolean;
  onToggleRightPanel?: () => void;
}

export function ChatArea({ isRightPanelOpen, onToggleRightPanel }: ChatAreaProps) {
  const currentThread = useThreadStore((s) => s.currentThread);
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const streamingResponses = useChatStore((s) => s.streamingResponses);
  const streamingThinking = useChatStore((s) => s.streamingThinking);
  const fetchMessages = useChatStore((s) => s.fetchMessages);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const deleteMessage = useChatStore((s) => s.deleteMessage);
  const setReplyingTo = useChatStore((s) => s.setReplyingTo);
  const replyingTo = useChatStore((s) => s.replyingTo);
  const activeSkill = useChatStore((s) => s.activeSkill);
  const intentMode = useChatStore((s) => s.intentMode);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Fetch messages when thread changes
  useEffect(() => {
    if (currentThread) {
      fetchMessages(currentThread.id);
    }
  }, [currentThread?.id]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setIsSearchOpen(true);
      }
      if (e.key === "Escape") {
        setEditingId(null);
        setReplyingTo(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setReplyingTo]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingResponses]);

  // Message handlers
  const handleReply = (msg: MessageResponse) => {
    setReplyingTo(msg);
  };

  const handleEdit = async (msg: MessageResponse, newContent: string) => {
    if (!currentThread || !newContent.trim()) return;
    try {
      await api.messages.edit(currentThread.id, msg.id, newContent);
      updateMessage(msg.id, newContent);
      setEditingId(null);
    } catch (e) {
      console.error("Failed to edit message:", e);
    }
  };

  const handleDelete = async (msg: MessageResponse) => {
    if (!currentThread) return;
    if (!confirm("确定要删除这条消息吗？")) return;
    try {
      await api.messages.delete(currentThread.id, msg.id);
      deleteMessage(msg.id);
    } catch (e) {
      console.error("Failed to delete message:", e);
    }
  };

  const handleBranch = async (msg: MessageResponse) => {
    if (!currentThread) return;
    try {
      const result = await api.messages.branch(currentThread.id, msg.id);
      // Navigate to new thread
      window.location.href = `/?thread=${result.thread_id}`;
    } catch (e) {
      console.error("Failed to branch thread:", e);
    }
  };

  if (!currentThread) {
    return (
      <div className="flex h-full w-full items-center justify-center overflow-hidden text-gray-400 dark:text-gray-600">
        <div className="text-center">
          <div className="mb-4 text-6xl">🐱</div>
          <p className="text-lg dark:text-gray-400">选择或创建一个对话开始聊天</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex min-w-0 items-center gap-3">
          <CatSelector
            currentCatId={currentThread.current_cat_id}
            onCatChange={async (catId) => {
              try {
                await api.threads.switchCat(currentThread.id, catId);
                // Update local state
                if (currentThread) {
                  currentThread.current_cat_id = catId;
                }
              } catch (e) {
                console.error("Failed to switch cat:", e);
              }
            }}
          />
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
          <SessionStatus threadId={currentThread.id} />
          <ExportButton />
          <div className="hidden text-xs text-gray-400 dark:text-gray-500 sm:block">
            创建于 {formatDateTime(currentThread.created_at)}
          </div>
          {onToggleRightPanel && (
            <button
              onClick={onToggleRightPanel}
              className="ml-2 flex h-8 w-8 items-center justify-center rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              title={isRightPanelOpen ? "关闭右侧面板" : "打开右侧面板"}
            >
              {isRightPanelOpen ? (
                <PanelRightClose size={16} className="text-gray-600 dark:text-gray-400" />
              ) : (
                <PanelRightOpen size={16} className="text-gray-600 dark:text-gray-400" />
              )}
            </button>
          )}
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
          <MessageBubble
            key={i}
            message={msg}
            isEditing={editingId === msg.id}
            onReply={() => handleReply(msg)}
            onEdit={(content) => handleEdit(msg, content)}
            onDelete={() => handleDelete(msg)}
            onBranch={() => handleBranch(msg)}
            onStartEdit={() => setEditingId(msg.id)}
            onCancelEdit={() => setEditingId(null)}
          />
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
      <InputBar
        disabled={isStreaming}
        replyTo={replyingTo}
        onCancelReply={() => setReplyingTo(null)}
      />

      {/* Search Modal */}
      <HistorySearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
      />
    </div>
  );
}
