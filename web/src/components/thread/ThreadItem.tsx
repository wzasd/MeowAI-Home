import { useEffect, useRef, useState } from "react";
import {
  Archive,
  Edit2,
  MessageSquare,
  MoreVertical,
  Trash2,
} from "lucide-react";
import type { ThreadResponse } from "../../types";

interface ThreadItemProps {
  thread: ThreadResponse;
  isActive: boolean;
  onSelect: () => void;
  onRename?: (id: string, name: string) => Promise<void>;
  onArchive?: (id: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
}

function formatUpdatedLabel(timestamp: string) {
  const date = new Date(timestamp);
  return `${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })} 更新`;
}

export function ThreadItem({
  thread,
  isActive,
  onSelect,
  onRename,
  onArchive,
  onDelete,
}: ThreadItemProps) {
  const [showMenu, setShowMenu] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(thread.name);
  const [isLoading, setIsLoading] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const handleRename = async () => {
    if (editName.trim() && editName !== thread.name) {
      setIsLoading(true);
      await onRename?.(thread.id, editName.trim());
      setIsLoading(false);
    }
    setIsEditing(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Enter") {
      handleRename();
    } else if (event.key === "Escape") {
      setEditName(thread.name);
      setIsEditing(false);
    }
  };

  const handleArchive = async () => {
    setIsLoading(true);
    setShowMenu(false);
    await onArchive?.(thread.id);
    setIsLoading(false);
  };

  const handleDelete = async () => {
    if (confirm(`确定要删除猫窝 "${thread.name}" 吗？此操作不可撤销。`)) {
      setIsLoading(true);
      setShowMenu(false);
      await onDelete?.(thread.id);
      setIsLoading(false);
    }
  };

  const projectLabel = thread.project_path?.split("/").filter(Boolean).pop();
  const supportLabel = thread.is_archived
    ? "归档记录"
    : projectLabel || "未绑定项目";

  return (
    <div
      className={`group relative mx-2 my-1 flex w-[calc(100%-1rem)] items-stretch overflow-visible rounded-2xl border transition-all ${
        isActive
          ? "border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(183,103,37,0.14),rgba(47,116,103,0.08))] shadow-[0_16px_36px_rgba(73,46,22,0.12)]"
          : "border-[var(--border)]/70 bg-white/20 hover:border-[var(--border)] hover:bg-white/35 dark:bg-white/5 dark:hover:bg-white/7"
      } ${isLoading ? "opacity-50" : ""}`}
    >
      <button
        onClick={onSelect}
        className="flex min-w-0 flex-1 items-start gap-3 px-3.5 py-3 text-left"
        disabled={isEditing}
      >
        <div
          className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border ${
            isActive
              ? "border-[rgba(183,103,37,0.22)] bg-white/65 text-[var(--accent)] dark:bg-white/5"
              : "border-[var(--border)] bg-white/50 text-[var(--text-faint)] dark:bg-white/5"
          }`}
        >
          <MessageSquare size={15} />
        </div>

        <div className="min-w-0 flex-1">
          {isEditing ? (
            <input
              ref={inputRef}
              type="text"
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleRename}
              disabled={isLoading}
              className="nest-field nest-r-sm w-full px-2 py-1.5 text-sm"
              onClick={(event) => event.stopPropagation()}
            />
          ) : (
            <>
              <div className="flex items-center gap-2">
                <span
                  className={`truncate text-sm font-semibold ${
                    thread.is_archived
                      ? "text-[var(--text-faint)] line-through"
                      : isActive
                        ? "text-[var(--text-strong)]"
                        : "text-[var(--text-soft)]"
                  }`}
                >
                  {thread.name}
                </span>
                {isActive && (
                  <span className="rounded-full bg-[var(--accent-soft)] px-1.5 py-0.5 text-[9px] font-semibold text-[var(--accent-deep)]">
                    当前
                  </span>
                )}
              </div>

              <div className="mt-1 text-[11px] text-[var(--text-faint)]">
                {thread.message_count} 条消息 · {formatUpdatedLabel(thread.updated_at)}
              </div>

              <div className="mt-1 truncate text-[10px] text-[var(--text-soft)]">
                {supportLabel}
              </div>
            </>
          )}
        </div>
      </button>

      {!isEditing && (
        <div ref={menuRef} className="relative flex shrink-0 items-start pr-2 pt-2">
          <button
            onClick={(event) => {
              event.stopPropagation();
              setShowMenu((value) => !value);
            }}
            className={`rounded-full p-1.5 transition-opacity ${
              showMenu ? "opacity-100" : "opacity-0 group-hover:opacity-100"
            } hover:bg-white/55 dark:hover:bg-white/10`}
            title="更多操作"
          >
            <MoreVertical size={14} className="text-[var(--text-faint)]" />
          </button>

          {showMenu && (
            <div className="nest-panel-strong nest-r-md absolute right-2 top-9 z-20 w-36 py-1">
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  setShowMenu(false);
                  setIsEditing(true);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[var(--text-soft)] hover:bg-white/40 dark:hover:bg-white/5"
              >
                <Edit2 size={14} />
                重命名
              </button>

              <button
                onClick={(event) => {
                  event.stopPropagation();
                  void handleArchive();
                }}
                disabled={isLoading}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[var(--text-soft)] hover:bg-white/40 dark:hover:bg-white/5"
              >
                <Archive size={14} />
                {thread.is_archived ? "取消归档" : "归档"}
              </button>

              <button
                onClick={(event) => {
                  event.stopPropagation();
                  void handleDelete();
                }}
                disabled={isLoading}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-[var(--danger)] hover:bg-red-50/70 dark:hover:bg-red-900/10"
              >
                <Trash2 size={14} />
                删除
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
