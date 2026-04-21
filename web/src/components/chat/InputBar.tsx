import { useRef, useEffect, useState, useEffectEvent, type KeyboardEvent } from "react";
import { Send, Gamepad2, Lightbulb, Wrench, HelpCircle, X, Reply, AtSign, CornerDownLeft } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { useCatStore } from "../../stores/catStore";
import { useThreadStore } from "../../stores/threadStore";
import { useChatCommands } from "../../hooks/useChatCommands";
import { buildCatMentionOptions, type CatMentionOption } from "./mentionOptions";
import { VoiceInput } from "./VoiceInput";
import { FileUpload, AttachmentChip } from "./FileUpload";
import type { MessageResponse, Attachment } from "../../types";

interface InputBarProps {
  disabled?: boolean;
  replyTo?: MessageResponse | null;
  onCancelReply?: () => void;
}

// Slash commands
interface SlashCommand {
  id: string;
  command: string;
  icon: React.ReactNode;
  label: string;
  desc: string;
  template: string;
}

const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: "game",
    command: "/game",
    icon: <Gamepad2 size={16} />,
    label: "开始游戏",
    desc: "启动一个互动游戏",
    template: "/game 我们来玩一个",
  },
  {
    id: "ideate",
    command: "/ideate",
    icon: <Lightbulb size={16} />,
    label: "头脑风暴",
    desc: "切换到 ideate 模式进行创意讨论",
    template: "/ideate ",
  },
  {
    id: "execute",
    command: "/execute",
    icon: <Wrench size={16} />,
    label: "执行模式",
    desc: "切换到 execute 模式进行任务执行",
    template: "/execute ",
  },
  {
    id: "help",
    command: "/help",
    icon: <HelpCircle size={16} />,
    label: "查看帮助",
    desc: "显示可用命令列表",
    template: "/help",
  },
];

export function InputBar({ disabled = false, replyTo, onCancelReply }: InputBarProps) {
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const slashMenuRef = useRef<HTMLDivElement>(null);
  const mentionMenuRef = useRef<HTMLDivElement>(null);
  const mentionListRef = useRef<HTMLDivElement>(null);
  const startStreaming = useChatStore((s) => s.startStreaming);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const cats = useCatStore((s) => s.cats);
  const fetchCats = useCatStore((s) => s.fetchCats);

  const { processCommand } = useChatCommands();

  const syncReplyDraft = useEffectEvent((nextReplyTo: MessageResponse | null | undefined) => {
    if (!nextReplyTo) {
      setText("");
    }
  });

  // Clear text when reply is cancelled
  useEffect(() => {
    syncReplyDraft(replyTo);
  }, [replyTo]);

  // Mention autocomplete state
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionStartPos, setMentionStartPos] = useState(0);

  // Slash command state
  const [showSlashMenu, setShowSlashMenu] = useState(false);
  const [slashQuery, setSlashQuery] = useState("");
  const [slashSelectedIndex, setSlashSelectedIndex] = useState(0);

  // Filter slash commands
  const filteredSlashCommands = SLASH_COMMANDS.filter(
    (cmd) =>
      cmd.command.toLowerCase().includes(slashQuery.toLowerCase()) ||
      cmd.label.toLowerCase().includes(slashQuery.toLowerCase())
  );

  const syncThreadDraft = useEffectEvent((threadId: string | null) => {
    if (threadId) {
      const draft = localStorage.getItem(`draft:${threadId}`);
      setText(draft || "");
      return;
    }
    setText("");
  });

  // Draft persistence: load draft when thread changes
  useEffect(() => {
    syncThreadDraft(currentThreadId);
  }, [currentThreadId]);

  useEffect(() => {
    if (cats.length === 0) {
      void fetchCats();
    }
  }, [cats.length, fetchCats]);

  // Draft persistence: save draft on text change
  useEffect(() => {
    if (currentThreadId) {
      if (text.trim()) {
        localStorage.setItem(`draft:${currentThreadId}`, text);
      } else {
        localStorage.removeItem(`draft:${currentThreadId}`);
      }
    }
  }, [text, currentThreadId]);

  // Filter options based on query
  const mentionOptions = buildCatMentionOptions(cats);
  const filteredOptions = mentionOptions.filter(
    (opt) =>
      opt.name.toLowerCase().includes(mentionQuery.toLowerCase()) ||
      opt.id.toLowerCase().includes(mentionQuery.toLowerCase()) ||
      opt.aliases.some((a) => a.toLowerCase().includes(mentionQuery.toLowerCase()))
  );
  const activeMentionIndex = filteredOptions[selectedIndex] ? selectedIndex : 0;
  const activeMentionOption = filteredOptions[activeMentionIndex] ?? null;
  const secondaryMentionOptions = filteredOptions
    .map((option, index) => ({ option, index }))
    .filter(({ index }) => index !== activeMentionIndex);

  const handleSend = async (deliveryMode?: "queue" | "force") => {
    if ((!text.trim() && attachments.length === 0) || disabled) return;
    const trimmed = text.trim();

    // Slash command interception — before streaming / WS send
    const result = await processCommand(trimmed);
    if (result.consumed) {
      if (result.forward) {
        // Forward with forced intent (e.g. /ideate content)
        startStreaming();
        const event = new CustomEvent("meowai:send", {
          detail: {
            content: result.forward.content,
            attachments,
            forceIntent: result.forward.forceIntent,
            deliveryMode,
          },
        });
        window.dispatchEvent(event);
      }
      setText("");
      setAttachments([]);
      setShowMentions(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      return;
    }

    // For queue mode, do NOT call startStreaming() — message goes to queue
    if (deliveryMode !== "queue") {
      startStreaming();
    }

    const event = new CustomEvent("meowai:send", {
      detail: { content: trimmed, attachments, deliveryMode },
    });
    window.dispatchEvent(event);
    setText("");
    setAttachments([]);
    setShowMentions(false);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const insertMention = (option: CatMentionOption) => {
    const primaryAlias = option.aliases[0] ?? `@${option.id}`;
    const beforeMention = text.slice(0, mentionStartPos);
    const afterMention = text.slice(mentionStartPos + mentionQuery.length + 1);
    const newText = beforeMention + primaryAlias + " " + afterMention;
    const cursorPos = mentionStartPos + primaryAlias.length + 1;
    setText(newText);
    setShowMentions(false);
    setTimeout(() => {
      const el = textareaRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(cursorPos, cursorPos);
      }
    }, 0);
  };

  const insertSlashCommand = (cmd: SlashCommand) => {
    const newText = cmd.template;
    setText(newText);
    setShowSlashMenu(false);
    setTimeout(() => {
      const el = textareaRef.current;
      if (el) {
        el.focus();
        el.setSelectionRange(newText.length, newText.length);
      }
    }, 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle slash command menu
    if (showSlashMenu && filteredSlashCommands.length > 0) {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSlashSelectedIndex((prev) => (prev + 1) % filteredSlashCommands.length);
          return;
        case "ArrowUp":
          e.preventDefault();
          setSlashSelectedIndex(
            (prev) => (prev - 1 + filteredSlashCommands.length) % filteredSlashCommands.length
          );
          return;
        case "Enter":
        case "Tab":
          e.preventDefault();
          if (filteredSlashCommands[slashSelectedIndex]) {
            insertSlashCommand(filteredSlashCommands[slashSelectedIndex]);
          }
          return;
        case "Escape":
          setShowSlashMenu(false);
          return;
      }
    }

    // Handle mention menu
    if (showMentions && filteredOptions.length > 0) {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) => (prev + 1) % filteredOptions.length);
          return;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => (prev - 1 + filteredOptions.length) % filteredOptions.length);
          return;
        case "Enter":
        case "Tab":
          e.preventDefault();
          if (filteredOptions[selectedIndex]) {
            insertMention(filteredOptions[selectedIndex]);
          }
          return;
        case "Escape":
          setShowMentions(false);
          return;
      }
    }

    if (e.key === "Enter" && !e.shiftKey && !showMentions && !showSlashMenu) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    const cursorPos = e.target.selectionStart;
    setText(newText);

    // Check for slash command at the beginning
    if (newText.startsWith("/") && cursorPos <= newText.length) {
      const query = newText.slice(1, cursorPos);
      // Only show if no whitespace in the query (still typing command)
      if (!/\s/.test(query)) {
        setSlashQuery(query);
        setShowSlashMenu(true);
        setSlashSelectedIndex(0);
        setShowMentions(false);
        return;
      }
    }
    setShowSlashMenu(false);

    // Check for @ trigger
    const beforeCursor = newText.slice(0, cursorPos);
    const atIndex = beforeCursor.lastIndexOf("@");

    if (atIndex !== -1) {
      const afterAt = beforeCursor.slice(atIndex + 1);
      const hasWhitespaceAfterAt = /\s/.test(afterAt);
      const prevChar = atIndex > 0 ? beforeCursor.charAt(atIndex - 1) : " ";
      const precededByWhitespace = atIndex === 0 || /\s/.test(prevChar);

      // Only show if preceded by whitespace, no whitespace after @, and still within length limit
      if (precededByWhitespace && !hasWhitespaceAfterAt && afterAt.length <= 12) {
        setMentionQuery(afterAt);
        setMentionStartPos(atIndex);
        setShowMentions(true);
        setSelectedIndex(0);
      } else {
        setShowMentions(false);
      }
    } else {
      setShowMentions(false);
    }
  };

  // Keep the highlighted mention visible by scrolling only the mention list itself.
  useEffect(() => {
    if (!showMentions || !mentionListRef.current) return;

    const container = mentionListRef.current;
    const selectedBtn = container.querySelector<HTMLElement>(`[data-index="${selectedIndex}"]`);
    if (!selectedBtn) return;

    const top = selectedBtn.offsetTop;
    const bottom = top + selectedBtn.offsetHeight;
    const viewTop = container.scrollTop;
    const viewBottom = viewTop + container.clientHeight;

    if (top < viewTop) {
      container.scrollTop = top;
    } else if (bottom > viewBottom) {
      container.scrollTop = bottom - container.clientHeight;
    }
  }, [selectedIndex, showMentions]);

  // Close menus on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      const inTextarea = textareaRef.current?.contains(target);
      const inMentionMenu = mentionMenuRef.current?.contains(target);
      const inSlashMenu = slashMenuRef.current?.contains(target);
      if (!inTextarea && !inMentionMenu && !inSlashMenu) {
        setShowMentions(false);
        setShowSlashMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  }, [text]);

  return (
    <div className="relative border-t border-[var(--line)] bg-transparent px-4 py-4 lg:px-6">
      {replyTo && (
        <div className="nest-card nest-r-md mx-auto mb-3 flex max-w-4xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 text-sm">
            <Reply size={14} className="text-[var(--accent)]" />
            <span className="text-[var(--text-soft)]">
              回复:
              <span className="ml-1 line-clamp-1 max-w-[200px] text-[var(--text-strong)]">
                {replyTo.content.slice(0, 50)}...
              </span>
            </span>
          </div>
          <button
            onClick={onCancelReply}
            className="nest-button-ghost flex h-8 w-8 items-center justify-center rounded-full"
          >
            <X size={14} />
          </button>
        </div>
      )}
      {attachments.length > 0 && (
        <div className="mx-auto mb-2 flex max-w-4xl flex-wrap gap-2">
          {attachments.map((att, idx) => (
            <AttachmentChip
              key={`${att.name}-${idx}`}
              attachment={att}
              onRemove={() =>
                setAttachments((prev) => prev.filter((_, i) => i !== idx))
              }
            />
          ))}
        </div>
      )}
      <div className="nest-panel nest-r-2xl overflow-visible mx-auto max-w-4xl px-3 py-3">
        <div className="mb-3 flex flex-wrap items-center gap-2 px-1">
          <span className="nest-kicker">输入区</span>
          <span className="nest-chip">Enter 发送</span>
          <span className="nest-chip">@ 提及猫咪</span>
          <span className="nest-chip">/ 指令</span>
        </div>
        <div className="flex items-end gap-2">
          <VoiceInput
            onTranscript={(t) => setText((prev) => prev + t)}
            disabled={disabled}
          />
          <FileUpload
            threadId={currentThreadId}
            disabled={disabled}
            onUpload={(att) => setAttachments((prev) => [...prev, att])}
          />
          <div className="relative flex-1">
            {showMentions && (
              <div
                ref={mentionMenuRef}
                className="absolute bottom-[calc(100%+0.75rem)] left-0 z-20 w-full max-w-[31rem] overflow-hidden rounded-[22px] border border-[var(--border-strong)] bg-[linear-gradient(180deg,rgba(255,250,244,0.96),rgba(255,255,255,0.88))] shadow-[0_22px_48px_rgba(73,46,22,0.16)] dark:bg-[linear-gradient(180deg,rgba(34,25,20,0.97),rgba(30,23,18,0.94))]"
              >
                <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] px-3 py-2.5">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent-deep)]">
                      <AtSign size={15} />
                    </div>
                    <div className="min-w-0">
                      <div className="truncate text-sm font-semibold text-[var(--text-strong)]">
                        {mentionQuery ? `@${mentionQuery}` : "@ 点名"}
                      </div>
                      <div className="text-[11px] text-[var(--text-faint)]">
                        {filteredOptions.length} 位候选
                      </div>
                    </div>
                  </div>
                  <div className="hidden items-center gap-1 rounded-full border border-[var(--border)] bg-white/40 px-2.5 py-1 text-[11px] text-[var(--text-faint)] dark:bg-white/5 sm:flex">
                    <CornerDownLeft size={12} />
                    Enter
                  </div>
                </div>

                <div ref={mentionListRef} className="max-h-64 overflow-y-auto p-2.5">
                  {activeMentionOption ? (
                    <div className="space-y-2">
                      <button
                        data-index={activeMentionIndex}
                        onMouseEnter={() => setSelectedIndex(activeMentionIndex)}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          insertMention(activeMentionOption);
                        }}
                        className={`group w-full overflow-hidden rounded-[18px] border px-3 py-3 text-left transition-all duration-200 hover:-translate-y-0.5 ${activeMentionOption.toneClass} ${activeMentionOption.borderClass} ${
                          activeMentionIndex === selectedIndex
                            ? "shadow-[0_16px_28px_rgba(73,46,22,0.14)]"
                            : "shadow-[0_8px_18px_rgba(73,46,22,0.08)]"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-[15px] text-xl shadow-sm ${activeMentionOption.bgColor}`}
                          >
                            {activeMentionOption.emoji}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className={`truncate text-sm font-semibold ${activeMentionOption.color}`}>
                                {activeMentionOption.name}
                              </span>
                              <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${activeMentionOption.aliasClass}`}
                              >
                                {activeMentionOption.aliases[0]}
                              </span>
                            </div>
                            <p className="truncate text-xs text-[var(--text-soft)]">
                              {activeMentionOption.desc}
                            </p>
                          </div>
                          <div className="hidden shrink-0 rounded-full border border-[var(--border)] bg-white/45 px-2.5 py-1 text-[11px] font-semibold text-[var(--text-soft)] dark:bg-white/5 sm:block">
                            当前
                          </div>
                        </div>
                      </button>

                      {secondaryMentionOptions.length > 0 && (
                        <div className="grid gap-2 sm:grid-cols-2">
                          {secondaryMentionOptions.map(({ option, index }) => (
                            <button
                              key={option.id}
                              data-index={index}
                              onMouseEnter={() => setSelectedIndex(index)}
                              onMouseDown={(e) => {
                                e.preventDefault();
                                insertMention(option);
                              }}
                              className={`flex w-full items-center gap-2.5 rounded-[16px] border px-3 py-2.5 text-left transition-all duration-200 hover:-translate-y-0.5 ${option.toneClass} ${option.borderClass} ${
                                index === selectedIndex
                                  ? "shadow-[0_14px_24px_rgba(73,46,22,0.12)]"
                                  : "shadow-[0_6px_16px_rgba(73,46,22,0.06)]"
                              }`}
                            >
                              <div
                                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[13px] text-lg ${option.bgColor}`}
                              >
                                {option.emoji}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className={`truncate text-sm font-semibold ${option.color}`}>
                                  {option.name}
                                </div>
                                <div className="truncate text-[11px] text-[var(--text-faint)]">
                                  {option.aliases[0]}
                                </div>
                              </div>
                            </button>
                          ))}
                        </div>
                      )}

                      <div className="flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-[var(--text-faint)]">
                        <span>支持连续点名 `@opus @砚砚`</span>
                        <span>Esc 关闭</span>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-[18px] border border-dashed border-[var(--border)] bg-white/35 px-3 py-4 text-sm text-[var(--text-faint)] dark:bg-white/5">
                      没找到匹配对象。试试输入完整句柄，例如 `@gemini`。
                    </div>
                  )}
                </div>
              </div>
            )}
            {showSlashMenu && (
              <div
                ref={slashMenuRef}
                className="nest-panel-strong nest-r-xl absolute bottom-[calc(100%+0.75rem)] left-0 z-10 w-72 overflow-hidden"
              >
                <div className="max-h-60 overflow-y-auto">
                  {filteredSlashCommands.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-[var(--text-faint)]">无匹配命令</div>
                  ) : (
                    filteredSlashCommands.map((cmd, index) => (
                      <button
                        key={cmd.id}
                        data-index={index}
                        onMouseEnter={() => setSlashSelectedIndex(index)}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          insertSlashCommand(cmd);
                        }}
                        className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                          index === slashSelectedIndex ? "bg-white/55 dark:bg-white/5" : "hover:bg-white/35 dark:hover:bg-white/5"
                        }`}
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent-deep)] dark:bg-[var(--accent-soft)] dark:text-[var(--accent)]">
                          {cmd.icon}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-semibold text-[var(--text-strong)]">{cmd.label}</div>
                          <div className="truncate text-xs text-[var(--text-faint)]">{cmd.desc}</div>
                        </div>
                      </button>
                    ))
                  )}
                </div>
                <div className="border-t border-[var(--line)] bg-white/20 px-4 py-1.5 text-xs text-[var(--text-faint)] dark:bg-white/5">
                  ↑↓ 选择 · Enter 确认 · Esc 关闭
                </div>
              </div>
            )}

            <textarea
              ref={textareaRef}
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              placeholder="把消息、任务或灵感丢进这张工作台..."
              disabled={disabled}
              rows={1}
              className="nest-field nest-r-lg w-full resize-none px-4 py-3 text-sm leading-6 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>
          {isStreaming ? (
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleSend("queue")}
                disabled={disabled || (!text.trim() && attachments.length === 0)}
                className="h-12 w-12 rounded-xl bg-violet-500 text-white shadow-sm hover:bg-violet-600 disabled:cursor-not-allowed disabled:opacity-40"
                title="排队发送"
              >
                <svg className="mx-auto h-[18px] w-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 6h18M3 12h18M3 18h18" />
                </svg>
              </button>
              <button
                onClick={() => handleSend("force")}
                disabled={disabled || (!text.trim() && attachments.length === 0)}
                className="h-12 w-12 rounded-xl bg-red-500 text-white shadow-sm hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                title="强制发送（取消当前）"
              >
                <Send size={18} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => handleSend()}
              disabled={disabled || (!text.trim() && attachments.length === 0)}
              className="nest-button-primary nest-r-md h-12 w-12 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send size={18} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
