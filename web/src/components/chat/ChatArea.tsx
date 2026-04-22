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
import { CliOutputBlock } from "./CliOutputBlock";
import { toolCallStateToCliEvents } from "./toCliEvents";
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
  const streamingTools = useChatStore((s) => s.streamingTools);
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
  const [isUserAtBottom, setIsUserAtBottom] = useState(true);
  const [newMessageCount, setNewMessageCount] = useState(0);
  const prevMessageCountRef = useRef(0);
  const knownMsgIdsRef = useRef<Set<string>>(new Set());
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

  // Smart scroll: only follow if user is at bottom.
  // Show "new message" capsule when reading history.
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const isThreadSwitch = previousThreadIdRef.current !== currentThread?.id;
    if (isThreadSwitch) {
      container.scrollTo({ top: container.scrollHeight, behavior: "auto" });
      setIsUserAtBottom(true);
      setNewMessageCount(0);
      previousThreadIdRef.current = currentThread?.id ?? null;
      prevMessageCountRef.current = messages.length;
      // Mark all current messages as known (no entrance animation on load)
      knownMsgIdsRef.current = new Set(messages.filter((m) => m.id).map((m) => m.id));
      return;
    }

    // Detect truly new messages (not in known set)
    const newIds: string[] = [];
    for (const m of messages) {
      if (!knownMsgIdsRef.current.has(m.id)) {
        newIds.push(m.id);
      }
    }
    for (const id of newIds) {
      if (id) knownMsgIdsRef.current.add(id);
    }

    const newCount = newIds.length;

    if (newCount > 0 && isUserAtBottom) {
      // User is at bottom — follow the conversation
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
      setNewMessageCount(0);
    } else if (newCount > 0) {
      // User is reading history — show capsule
      setNewMessageCount((c) => c + newCount);
    }
  }, [currentThread?.id, messages, isUserAtBottom]);

  // Track whether user is at bottom of scroll
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const threshold = 80;
      const atBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
      setIsUserAtBottom(atBottom);
      if (atBottom) setNewMessageCount(0);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Also follow streaming responses if at bottom
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || !isUserAtBottom) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [streamingResponses, isUserAtBottom]);

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

          {messages.map((msg, i) => {
            const prevMsg = i > 0 ? messages[i - 1] : null;
            const isConsecutive = !!(prevMsg && prevMsg.cat_id && prevMsg.cat_id === msg.cat_id);
            const isNew = msg.id ? !knownMsgIdsRef.current.has(msg.id) : false;
            return (
              <MessageBubble
                key={msg.id || `msg-${i}`}
                message={msg}
                isEditing={editingId === msg.id}
                isEntering={isNew}
                isConsecutive={isConsecutive}
                onReply={() => handleReply(msg)}
                onEdit={(content) => handleEdit(msg, content)}
                onDelete={() => handleDelete(msg)}
                onBranch={() => handleBranch(msg)}
                onStartEdit={() => setEditingId(msg.id)}
                onCancelEdit={() => setEditingId(null)}
              />
            );
          })}

          {Array.from(streamingResponses.values()).map((resp) => {
            const tools = streamingTools.get(resp.catId);
            const cliEvents = tools ? toolCallStateToCliEvents(tools) : [];
            const hasCliBlock = cliEvents.length > 0;
            const hasContent = resp.content.trim().length > 0;
            return (
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
                  <div className="nest-card nest-r-xl relative px-5 py-4 overflow-hidden">
                    <div className="msg-ink-line" />
                    {/* Text content (clowder style: only show if has content) */}
                    {hasContent && (
                      <p className="whitespace-pre-wrap text-sm leading-7 text-[var(--text-strong)]">
                        {resp.content}
                        <span className="animate-pulse text-[var(--text-faint)]">|</span>
                      </p>
                    )}
                    {/* CliOutputBlock inside the bubble (clowder style) */}
                    {hasCliBlock && (
                      <CliOutputBlock
                        events={cliEvents}
                        status="streaming"
                        breedColor="#7C3AED"
                      />
                    )}
                    {/* Placeholder when no content and no tools */}
                    {!hasContent && !hasCliBlock && (
                      <span className="text-xs text-[var(--text-soft)]">Thinking...</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Tool events for cats that have tools but no streaming response yet */}
          {Array.from(streamingTools.entries())
            .filter(([catId]) => !streamingResponses.has(catId))
            .filter(([, tools]) => tools.length > 0)
            .map(([catId, tools]) => {
              const cliEvents = toolCallStateToCliEvents(tools);
              return (
                <div key={`tools-${catId}`} className="mb-5 flex justify-start">
                  <AgentBadge catId={catId} />
                  <div className="max-w-[78%] lg:max-w-[72%]">
                    <div className="nest-card nest-r-xl relative px-5 py-4 overflow-hidden">
                      <CliOutputBlock
                        events={cliEvents}
                        status="streaming"
                        breedColor="#7C3AED"
                      />
                    </div>
                  </div>
                </div>
              );
            })}

          {Array.from(streamingStatuses.entries())
            .filter(([catId]) => !streamingResponses.has(catId) && !streamingTools.has(catId))
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


      {newMessageCount > 0 && !isUserAtBottom && (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-10">
          <button
            onClick={() => {
              const container = scrollContainerRef.current;
              if (container) {
                container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
                setNewMessageCount(0);
                setIsUserAtBottom(true);
              }
            }}
            className="msg-capsule nest-button-primary flex items-center gap-2 rounded-full px-4 py-2 text-xs shadow-lg"
          >
            <span className="inline-block h-2 w-2 rounded-full bg-white/70" />
            {newMessageCount} 条新消息
          </button>
        </div>
      )}

      <InputBar
        disabled={!currentThread}
        replyTo={replyingTo}
        onCancelReply={() => setReplyingTo(null)}
      />

      <HistorySearchModal isOpen={isSearchOpen} onClose={() => setIsSearchOpen(false)} />
    </div>
  );
}
