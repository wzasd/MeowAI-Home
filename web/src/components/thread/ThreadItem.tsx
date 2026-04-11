import type { ThreadResponse } from "../../types";
import { MessageSquare, MoreVertical, Edit2, Archive, Trash2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";

interface ThreadItemProps {
  thread: ThreadResponse;
  isActive: boolean;
  onSelect: () => void;
  onRename?: (id: string, name: string) => Promise<void>;
  onArchive?: (id: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
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

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input when editing
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleRename();
    } else if (e.key === "Escape") {
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
    if (confirm(`确定要删除对话 "${thread.name}" 吗？此操作不可撤销。`)) {
      setIsLoading(true);
      setShowMenu(false);
      await onDelete?.(thread.id);
      setIsLoading(false);
    }
  };

  return (
    <div
      className={`group relative flex w-full items-center transition-colors ${
        isActive
          ? "border-r-2 border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20"
          : "hover:bg-gray-50 dark:hover:bg-gray-700/50"
      } ${isLoading ? "opacity-50" : ""}`}
    >
      <button
        onClick={onSelect}
        className="flex flex-1 items-start gap-3 px-4 py-3 text-left"
        disabled={isEditing}
      >
        <MessageSquare
          size={16}
          className={`mt-0.5 shrink-0 ${
            isActive ? "text-blue-500 dark:text-blue-400" : "text-gray-400 dark:text-gray-500"
          }`}
        />
        <div className="min-w-0 flex-1">
          {isEditing ? (
            <input
              ref={inputRef}
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={handleKeyDown}
              onBlur={handleRename}
              disabled={isLoading}
              className="w-full rounded border border-blue-300 bg-white px-1.5 py-0.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-blue-600 dark:bg-gray-700 dark:text-gray-100"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <>
              <div
                className={`truncate text-sm font-medium ${
                  thread.is_archived
                    ? "text-gray-500 line-through dark:text-gray-500"
                    : isActive
                      ? "text-gray-800 dark:text-gray-100"
                      : "text-gray-700 dark:text-gray-300"
                }`}
              >
                {thread.name}
              </div>
              <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
                <span>{thread.message_count} 条消息</span>
                {thread.is_archived && (
                  <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] dark:bg-gray-700">
                    已归档
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      </button>

      {/* Actions menu */}
      {!isEditing && (
        <div ref={menuRef} className="relative pr-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            className={`rounded p-1 opacity-0 transition-opacity group-hover:opacity-100 ${
              showMenu ? "opacity-100" : ""
            } hover:bg-gray-200 dark:hover:bg-gray-600`}
          >
            <MoreVertical size={14} className="text-gray-500 dark:text-gray-400" />
          </button>

          {showMenu && (
            <div className="absolute right-2 top-8 z-20 w-32 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-600 dark:bg-gray-800">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowMenu(false);
                  setIsEditing(true);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                <Edit2 size={14} />
                重命名
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleArchive();
                }}
                disabled={isLoading}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                <Archive size={14} />
                {thread.is_archived ? "取消归档" : "归档"}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete();
                }}
                disabled={isLoading}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
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
