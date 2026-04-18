import type { MessageResponse } from "../../types";
import { AgentBadge } from "./AgentBadge";
import { ThinkingPanel } from "./ThinkingPanel";
import { MarkdownContent } from "./MarkdownContent";
import { TTSButton } from "./TTSButton";
import { RichBlocks } from "../rich/RichBlocks";
import { parseRichBlocks } from "../../types/rich";
import { CAT_INFO, formatTime } from "../../types";
import { Reply, Pencil, Trash2, GitBranch, Check, X } from "lucide-react";
import { useState } from "react";

const COLOR_TONES: Record<string, string> = {
  orange: "border-l-[3px] border-l-[#c67835]",
  purple: "border-l-[3px] border-l-[#9b7bd6]",
  pink: "border-l-[3px] border-l-[#d4769f]",
};

function fmtTok(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

interface MessageMetaProps {
  meta: Record<string, unknown>;
}

function MessageMetaInline({ meta }: MessageMetaProps) {
  const usage = meta.usage as
    | {
        prompt_tokens?: number;
        completion_tokens?: number;
        cache_read_tokens?: number;
        cache_creation_tokens?: number;
      }
    | undefined;
  const cliCommand = meta.cli_command as string | undefined;
  const defaultModel = meta.default_model as string | undefined;

  const hasUsage =
    !!usage && ((usage.prompt_tokens ?? 0) > 0 || (usage.completion_tokens ?? 0) > 0);
  const hasInfo = cliCommand || defaultModel || hasUsage;
  if (!hasInfo) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-[var(--text-faint)]">
      {defaultModel && (
        <span className="rounded-full border border-[var(--border)] bg-white/30 px-2 py-0.5 dark:bg-white/5">
          {defaultModel}
        </span>
      )}
      {cliCommand && (
        <span className="rounded-full border border-[var(--border)] bg-white/30 px-2 py-0.5 font-mono dark:bg-white/5">
          {cliCommand}
        </span>
      )}
      {usage && (usage.prompt_tokens ?? 0) > 0 && (
        <span className="rounded-full border border-[var(--border)] bg-white/30 px-2 py-0.5 dark:bg-white/5">
          ↑{fmtTok(usage.prompt_tokens ?? 0)} ↓{fmtTok(usage.completion_tokens ?? 0)}
          {usage.cache_read_tokens ? ` ⚡${fmtTok(usage.cache_read_tokens)}` : ""}
        </span>
      )}
    </div>
  );
}

interface MessageBubbleProps {
  message: MessageResponse;
  isEditing?: boolean;
  onReply?: () => void;
  onEdit?: (content: string) => void;
  onDelete?: () => void;
  onBranch?: () => void;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
}

export function MessageBubble({
  message,
  isEditing,
  onReply,
  onEdit,
  onDelete,
  onBranch,
  onStartEdit,
  onCancelEdit,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.metadata?.is_error === true;
  const [showActions, setShowActions] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const richBlocks = parseRichBlocks(message.metadata);
  const catLabel = message.cat_id ? CAT_INFO[message.cat_id]?.name || message.cat_id : "系统";
  const toneClass = message.cat_id ? COLOR_TONES[CAT_INFO[message.cat_id]?.color || ""] || "" : "";

  const handleSave = () => {
    if (editContent.trim() && editContent !== message.content) {
      onEdit?.(editContent);
    } else {
      onCancelEdit?.();
    }
  };

  return (
    <div
      className={`group mb-5 flex ${isUser ? "justify-end" : "justify-start"}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {!isUser && message.cat_id && !isError && <AgentBadge catId={message.cat_id} />}

      <div className="flex max-w-[78%] flex-col lg:max-w-[72%]">
        {!isUser && (
          <div className="mb-1 flex items-center gap-2 px-1 text-[11px] text-[var(--text-faint)]">
            <span className="font-medium">{catLabel}</span>
            {!isError && <span className="bg-[var(--text-faint)]/60 h-1 w-1 rounded-full" />}
            {!isError && <span>工作室席位在线</span>}
          </div>
        )}

        {message.reply_to && (
          <div className="mb-2 flex items-center gap-1 px-1 text-xs text-[var(--text-faint)]">
            <Reply size={10} />
            <span className="truncate">回复消息</span>
          </div>
        )}

        {!isUser && message.thinking && message.cat_id && (
          <ThinkingPanel
            content={message.thinking}
            catId={message.cat_id}
            catName={message.cat_id}
          />
        )}

        {isEditing ? (
          <div className={`nest-card nest-r-xl px-4 py-3 ${toneClass}`}>
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="nest-field nest-r-md w-full min-w-[200px] resize-none px-3 py-2.5 text-sm"
              rows={3}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.metaKey) handleSave();
                if (e.key === "Escape") onCancelEdit?.();
              }}
            />
            <div className="mt-2 flex items-center justify-end gap-2">
              <button
                onClick={onCancelEdit}
                className="nest-button-ghost rounded-full px-3 py-1.5 text-xs"
              >
                <X size={12} /> 取消
              </button>
              <button
                onClick={handleSave}
                className="nest-button-primary rounded-full px-3 py-1.5 text-xs"
              >
                <Check size={12} /> 保存
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`nest-r-xl px-5 py-4 transition-transform duration-150 group-hover:-translate-y-0.5 ${
              isUser
                ? "nest-user-bubble"
                : isError
                  ? "border border-red-200/80 bg-red-50/85 text-red-900 shadow-[0_16px_34px_rgba(164,70,42,0.1)] dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-100"
                  : `nest-card text-[var(--text-strong)] ${toneClass}`
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
            ) : (
              <div className="text-sm leading-7">
                <MarkdownContent content={message.content} />
              </div>
            )}
            {isUser && Array.isArray(message.metadata?.attachments) && (
              <div className="mt-2 flex flex-wrap gap-2">
                {(
                  message.metadata.attachments as Array<{
                    name: string;
                    size: number;
                    url: string;
                    mimeType?: string;
                  }>
                ).map((att, idx) => (
                  <a
                    key={idx}
                    href={att.url}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:bg-white/28 flex items-center gap-1.5 rounded-full bg-white/20 px-3 py-1.5 text-xs text-white"
                    title={att.mimeType || "file"}
                  >
                    <span className="max-w-[140px] truncate">{att.name}</span>
                    <span className="opacity-80">
                      {att.size < 1024
                        ? `${att.size} B`
                        : att.size < 1024 * 1024
                          ? `${(att.size / 1024).toFixed(1)} KB`
                          : `${(att.size / (1024 * 1024)).toFixed(1)} MB`}
                    </span>
                  </a>
                ))}
              </div>
            )}
            {!isUser && richBlocks.length > 0 && (
              <div className="mt-3 border-t border-[var(--line)] pt-3">
                <RichBlocks blocks={richBlocks} />
              </div>
            )}
          </div>
        )}

        {/* Message actions */}
        {!isEditing && (
          <div
            className={`mt-2 flex items-center gap-2 px-1 text-[10px] ${
              isUser ? "justify-end" : "justify-start"
            }`}
          >
            <span className="text-[var(--text-faint)]">
              {formatTime(message.timestamp)}
              {message.is_edited && <span className="ml-1">(已编辑)</span>}
            </span>
            {showActions ? (
              <div className="flex items-center gap-0.5">
                {onReply && (
                  <button
                    onClick={onReply}
                    className="rounded-full p-1 text-[var(--text-faint)] hover:bg-white/40 hover:text-[var(--accent)] dark:hover:bg-white/5"
                    title="回复"
                  >
                    <Reply size={12} />
                  </button>
                )}
                {onStartEdit && isUser && (
                  <button
                    onClick={onStartEdit}
                    className="rounded-full p-1 text-[var(--text-faint)] hover:bg-white/40 hover:text-[var(--accent)] dark:hover:bg-white/5"
                    title="编辑"
                  >
                    <Pencil size={12} />
                  </button>
                )}
                {onBranch && (
                  <button
                    onClick={onBranch}
                    className="rounded-full p-1 text-[var(--text-faint)] hover:bg-white/40 hover:text-[var(--accent)] dark:hover:bg-white/5"
                    title="分支"
                  >
                    <GitBranch size={12} />
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={onDelete}
                    className="rounded-full p-1 text-[var(--text-faint)] hover:bg-white/40 hover:text-[var(--danger)] dark:hover:bg-white/5"
                    title="删除"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            ) : (
              !isUser && !isError && message.metadata && <MessageMetaInline meta={message.metadata} />
            )}
            {!isUser && message.cat_id && !isError && (
              <TTSButton
                content={message.content}
                catId={message.cat_id}
                catName={CAT_INFO[message.cat_id]?.name || message.cat_id}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
