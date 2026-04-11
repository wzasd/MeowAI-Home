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
  const [showActions, setShowActions] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const richBlocks = parseRichBlocks(message.metadata);

  const handleSave = () => {
    if (editContent.trim() && editContent !== message.content) {
      onEdit?.(editContent);
    } else {
      onCancelEdit?.();
    }
  };

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} group mb-4`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {!isUser && message.cat_id && <AgentBadge catId={message.cat_id} />}

      <div className="flex max-w-[70%] flex-col">
        {/* Reply indicator */}
        {message.reply_to && (
          <div className="mb-1 flex items-center gap-1 text-xs text-gray-400">
            <Reply size={10} />
            <span className="truncate">回复消息</span>
          </div>
        )}

        {/* Thinking panel for assistant messages */}
        {!isUser && message.thinking && message.cat_id && (
          <ThinkingPanel
            content={message.thinking}
            catId={message.cat_id}
            catName={message.cat_id}
          />
        )}

        {/* Message content or edit mode */}
        {isEditing ? (
          <div className="rounded-2xl border bg-white px-4 py-2.5 shadow-sm dark:border-gray-600 dark:bg-gray-800">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full min-w-[200px] resize-none rounded border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
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
                className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              >
                <X size={12} /> 取消
              </button>
              <button
                onClick={handleSave}
                className="flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
              >
                <Check size={12} /> 保存
              </button>
            </div>
          </div>
        ) : (
          <div
            className={`rounded-2xl px-4 py-2.5 ${
              isUser
                ? "bg-blue-500 text-white"
                : "border border-gray-200 bg-white text-gray-800 shadow-sm dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            }`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
            ) : (
              <div className="text-sm leading-relaxed">
                <MarkdownContent content={message.content} />
              </div>
            )}
            {/* Rich content blocks */}
            {!isUser && richBlocks.length > 0 && (
              <div className="mt-2 border-t border-gray-100 pt-2 dark:border-gray-700">
                <RichBlocks blocks={richBlocks} />
              </div>
            )}
          </div>
        )}

        {/* Message actions */}
        {!isEditing && (
          <div
            className={`mt-1 flex items-center gap-2 text-[10px] ${
              isUser ? "justify-end" : "justify-start"
            } ${showActions ? "opacity-100" : "opacity-0"} transition-opacity`}
          >
            <span className="text-gray-400">
              {formatTime(message.timestamp)}
              {message.is_edited && <span className="ml-1">(已编辑)</span>}
            </span>
            <div className="flex items-center gap-0.5">
              {onReply && (
                <button
                  onClick={onReply}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700"
                  title="回复"
                >
                  <Reply size={12} />
                </button>
              )}
              {onStartEdit && isUser && (
                <button
                  onClick={onStartEdit}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700"
                  title="编辑"
                >
                  <Pencil size={12} />
                </button>
              )}
              {onBranch && (
                <button
                  onClick={onBranch}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700"
                  title="分支"
                >
                  <GitBranch size={12} />
                </button>
              )}
              {onDelete && (
                <button
                  onClick={onDelete}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-700"
                  title="删除"
                >
                  <Trash2 size={12} />
                </button>
              )}
            </div>
            {!isUser && message.cat_id && (
              <TTSButton
                content={message.content}
                catName={CAT_INFO[message.cat_id]?.name || message.cat_id}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
