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
import { HistorySearchModal } from "./HistorySearchModal";
import { PageHeader } from "../ui/PageHeader";
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
  const streamingStatuses = useChatStore((s) => s.streamingStatuses);
  const fetchMessages = useChatStore((s) => s.fetchMessages);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const deleteMessage = useChatStore((s) => s.deleteMessage);
  const setReplyingTo = useChatStore((s) => s.setReplyingTo);
  const replyingTo = useChatStore((s) => s.replyingTo);
  const activeSkill = useChatStore((s) => s.activeSkill);
  const intentMode = useChatStore((s) => s.intentMode);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const previousThreadIdRef = useRef<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const projectName = currentThread?.project_path?.split("/").filter(Boolean).pop();

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

  // Auto-scroll only inside the message pane, not the whole page.
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const isThreadSwitch = previousThreadIdRef.current !== currentThread?.id;
    container.scrollTo({
      top: container.scrollHeight,
      behavior: isThreadSwitch ? "auto" : "smooth",
    });
    previousThreadIdRef.current = currentThread?.id ?? null;
  }, [currentThread?.id, messages, streamingResponses]);

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
      <div className="flex h-full w-full items-center justify-center overflow-hidden px-6 text-[var(--text-faint)]">
        <div className="nest-card nest-r-xl max-w-lg p-10 text-center">
          <div className="mb-4 text-6xl">🐱</div>
          <h2 className="nest-title text-2xl font-semibold text-[var(--text-strong)]">
            今晚的猫窝还空着
          </h2>
          <p className="mt-3 text-sm leading-7 text-[var(--text-soft)]">
            选一个猫窝，或者搭一个新窝。消息、任务、文件和猫猫状态都会在这里汇流。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-transparent">
      <PageHeader
        eyebrow="当前会话"
        title={currentThread.name}
        titleClassName="truncate"
        description="在一张工作台里收住回复、思路、技能和任务流。"
        meta={
          <>
            {projectName && <span className="nest-chip">{projectName}</span>}
            {intentMode && <IntentBadge mode={intentMode} />}
            {activeSkill && <span className="nest-chip">{activeSkill}</span>}
          </>
        }
        actions={
          <>
            <div className="nest-chip">
              <SessionStatus threadId={currentThread.id} />
            </div>
            <div className="nest-chip">
              <ExportButton />
            </div>
            <div className="hidden text-xs text-[var(--text-faint)] sm:block">
              创建于 {formatDateTime(currentThread.created_at)}
            </div>
            {onToggleRightPanel && (
              <button
                onClick={onToggleRightPanel}
                className="nest-button-secondary flex h-10 items-center justify-center rounded-full px-3"
                title={isRightPanelOpen ? "关闭右侧面板" : "打开右侧面板"}
              >
                {isRightPanelOpen ? (
                  <PanelRightClose size={16} className="text-[var(--text-soft)]" />
                ) : (
                  <PanelRightOpen size={16} className="text-[var(--text-soft)]" />
                )}
                {!isRightPanelOpen && (
                  <span className="text-xs text-[var(--text-soft)]">状态台</span>
                )}
              </button>
            )}
          </>
        }
      />

      <div ref={scrollContainerRef} className="relative flex-1 overflow-y-auto px-4 py-4 lg:px-6">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.22),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.12),transparent_20%)] dark:bg-[radial-gradient(circle_at_top,rgba(230,162,93,0.08),transparent_34%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_20%)]" />
        <div className="relative space-y-1 pb-2">
          {messages.length === 0 && !isStreaming && (
            <div className="nest-card nest-r-xl mx-auto mt-10 max-w-2xl p-8 text-center">
              <div className="nest-kicker">今晚的猫窝</div>
              <h3 className="nest-title mt-3 text-2xl font-semibold text-[var(--text-strong)]">
                先把第一句话放进来
              </h3>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-7 text-[var(--text-soft)]">
                这里不是普通 IM，而是流浪猫工作室的共用桌面。提一个问题，或者直接点名：
              </p>
              <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
                <span className="nest-chip">@opus 架构</span>
                <span className="nest-chip">@砚砚 Review</span>
                <span className="nest-chip">@gemini 设计</span>
              </div>
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

          {Array.from(streamingResponses.values()).map((resp) => (
            <div key={resp.catId} className="mb-5 flex justify-start">
              <AgentBadge catId={resp.catId} />
              <div className="max-w-[78%] lg:max-w-[72%]">
                {streamingStatuses.get(resp.catId) && (
                  <div className="mb-2 flex items-center gap-1.5 px-1 text-xs text-[var(--text-faint)]">
                    <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />
                    <span>{streamingStatuses.get(resp.catId)}</span>
                  </div>
                )}
                {streamingThinking.get(resp.catId) && (
                  <ThinkingPanel
                    content={streamingThinking.get(resp.catId)!}
                    catId={resp.catId}
                    catName={resp.catName}
                  />
                )}
                <div className="nest-card nest-r-xl px-5 py-4">
                  <p className="whitespace-pre-wrap text-sm leading-7 text-[var(--text-strong)]">
                    {resp.content}
                  </p>
                  <span className="animate-pulse text-[var(--text-faint)]">|</span>
                </div>
              </div>
            </div>
          ))}

          {Array.from(streamingStatuses.entries())
            .filter(([catId]) => !streamingResponses.has(catId))
            .map(([catId, status]) => (
              <div key={`status-${catId}`} className="mb-5 flex justify-start">
                <AgentBadge catId={catId} />
                <div className="max-w-[78%] lg:max-w-[72%]">
                  <div className="mb-2 flex items-center gap-1.5 px-1 text-xs text-[var(--text-faint)]">
                    <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--accent)]" />
                    <span>{status}</span>
                  </div>
                  <div className="nest-card nest-r-lg px-4 py-3 text-sm text-[var(--text-soft)]">
                    这只猫正在赶来，消息马上到。
                    <span className="animate-pulse text-[var(--text-faint)]">|</span>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </div>

      {isStreaming && <StreamingIndicator />}

      <InputBar
        disabled={isStreaming}
        replyTo={replyingTo}
        onCancelReply={() => setReplyingTo(null)}
      />

      <HistorySearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  );
}
