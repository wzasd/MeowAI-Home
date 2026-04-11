import { useRef, useEffect, useState, type KeyboardEvent } from "react";
import { Send, Gamepad2, Lightbulb, Wrench, HelpCircle, X, Reply } from "lucide-react";
import { useChatStore } from "../../stores/chatStore";
import { useThreadStore } from "../../stores/threadStore";
import { VoiceInput } from "./VoiceInput";
import type { MessageResponse } from "../../types";

interface InputBarProps {
  disabled?: boolean;
  replyTo?: MessageResponse | null;
  onCancelReply?: () => void;
}

interface CatOption {
  id: string;
  name: string;
  emoji: string;
  color: string;
  bgColor: string;
  aliases: string[];
  desc: string;
}

const CAT_OPTIONS: CatOption[] = [
  {
    id: "orange",
    name: "阿橘",
    emoji: "🐱",
    color: "text-orange-700",
    bgColor: "bg-orange-100",
    aliases: ["@dev", "@orange"],
    desc: "开发实现",
  },
  {
    id: "inky",
    name: "墨点",
    emoji: "🐾",
    color: "text-purple-700",
    bgColor: "bg-purple-100",
    aliases: ["@review", "@inky"],
    desc: "代码审查",
  },
  {
    id: "patch",
    name: "花花",
    emoji: "🌸",
    color: "text-pink-700",
    bgColor: "bg-pink-100",
    aliases: ["@research", "@patch"],
    desc: "研究设计",
  },
];

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const startStreaming = useChatStore((s) => s.startStreaming);
  const currentThreadId = useThreadStore((s) => s.currentThreadId);

  // Clear text when reply is cancelled
  useEffect(() => {
    if (!replyTo) {
      setText("");
    }
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

  // Draft persistence: load draft when thread changes
  useEffect(() => {
    if (currentThreadId) {
      const draft = localStorage.getItem(`draft:${currentThreadId}`);
      setText(draft || "");
    }
  }, [currentThreadId]);

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
  const filteredOptions = CAT_OPTIONS.filter(
    (opt) =>
      opt.name.toLowerCase().includes(mentionQuery.toLowerCase()) ||
      opt.id.toLowerCase().includes(mentionQuery.toLowerCase()) ||
      opt.aliases.some((a) => a.toLowerCase().includes(mentionQuery.toLowerCase()))
  );

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    startStreaming();

    const event = new CustomEvent("meowai:send", {
      detail: { content: text.trim() },
    });
    window.dispatchEvent(event);
    setText("");
    setShowMentions(false);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const insertMention = (option: CatOption) => {
    const beforeMention = text.slice(0, mentionStartPos);
    const afterMention = text.slice(mentionStartPos + mentionQuery.length + 1);
    const newText = beforeMention + option.aliases[0] + " " + afterMention;
    setText(newText);
    setShowMentions(false);
    textareaRef.current?.focus();
  };

  const insertSlashCommand = (cmd: SlashCommand) => {
    const newText = cmd.template;
    setText(newText);
    setShowSlashMenu(false);
    textareaRef.current?.focus();
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

      // Only show if no whitespace after @ (i.e., still typing the mention)
      if (!hasWhitespaceAfterAt && afterAt.length <= 12) {
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

  // Auto-scroll selected item into view
  useEffect(() => {
    if (showMentions && menuRef.current) {
      const selectedBtn = menuRef.current.querySelector(`[data-index="${selectedIndex}"]`);
      selectedBtn?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex, showMentions]);

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 160) + "px";
    }
  }, [text]);

  return (
    <div className="relative border-t border-gray-200 bg-white px-4 py-4 dark:border-gray-700 dark:bg-gray-800 lg:px-6">
      {/* Reply indicator */}
      {replyTo && (
        <div className="mb-2 flex items-center justify-between rounded-lg bg-blue-50 px-3 py-2 dark:bg-blue-900/20">
          <div className="flex items-center gap-2 text-sm">
            <Reply size={14} className="text-blue-500" />
            <span className="text-gray-600 dark:text-gray-400">
              回复: <span className="line-clamp-1 max-w-[200px] text-gray-800 dark:text-gray-200">{replyTo.content.slice(0, 50)}...</span>
            </span>
          </div>
          <button
            onClick={onCancelReply}
            className="rounded p-1 text-gray-400 hover:bg-blue-100 hover:text-gray-600 dark:hover:bg-blue-800"
          >
            <X size={14} />
          </button>
        </div>
      )}
      {/* Slash command dropdown */}
      {showSlashMenu && (
        <div
          ref={menuRef}
          className="absolute bottom-full left-6 z-10 mb-2 w-72 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg"
        >
          <div className="max-h-60 overflow-y-auto">
            {filteredSlashCommands.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-400">无匹配命令</div>
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
                    index === slashSelectedIndex ? "bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-600">
                    {cmd.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-gray-700">{cmd.label}</div>
                    <div className="truncate text-xs text-gray-400">{cmd.desc}</div>
                  </div>
                </button>
              ))
            )}
          </div>
          <div className="border-t border-gray-100 bg-gray-50 px-4 py-1.5 text-xs text-gray-400">
            ↑↓ 选择 · Enter 确认 · Esc 关闭
          </div>
        </div>
      )}

      {/* Mention dropdown */}
      {showMentions && (
        <div
          ref={menuRef}
          className="absolute bottom-full left-6 z-10 mb-2 w-64 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg"
        >
          <div className="max-h-60 overflow-y-auto">
            {filteredOptions.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-400">无匹配猫咪</div>
            ) : (
              filteredOptions.map((option, index) => (
                <button
                  key={option.id}
                  data-index={index}
                  onMouseEnter={() => setSelectedIndex(index)}
                  onMouseDown={(e) => {
                    e.preventDefault(); // Prevent textarea blur
                    insertMention(option);
                  }}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                    index === selectedIndex ? "bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full text-lg ${option.bgColor}`}
                  >
                    {option.emoji}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className={`text-sm font-semibold ${option.color}`}>{option.name}</div>
                    <div className="truncate text-xs text-gray-400">
                      {option.aliases.join(" / ")} · {option.desc}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
          <div className="border-t border-gray-100 bg-gray-50 px-4 py-1.5 text-xs text-gray-400">
            ↑↓ 选择 · Enter 确认 · Esc 关闭
          </div>
        </div>
      )}

      <div className="mx-auto flex max-w-4xl items-end gap-2">
        <VoiceInput
          onTranscript={(t) => setText((prev) => prev + t)}
          disabled={disabled}
        />
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行，@ 提及猫咪，/ 斜杠命令)"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="rounded-xl bg-blue-500 p-2.5 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
