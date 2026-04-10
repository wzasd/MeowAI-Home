import { useEffect } from "react";
import { useThreadStore } from "../../stores/threadStore";
import { ThreadItem } from "./ThreadItem";
import { Plus, Search, X } from "lucide-react";
import { useState } from "react";

interface ThreadSidebarProps {
  onCloseMobile?: () => void;
}

export function ThreadSidebar({ onCloseMobile }: ThreadSidebarProps) {
  const threads = useThreadStore((s) => s.threads);
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const fetchThreads = useThreadStore((s) => s.fetchThreads);
  const selectThread = useThreadStore((s) => s.selectThread);
  const createThread = useThreadStore((s) => s.createThread);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const filtered = threads.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  const handleCreate = async () => {
    const name = `对话 ${threads.length + 1}`;
    const id = await createThread(name);
    if (id) {
      await fetchThreads();
    }
  };

  const handleSelect = (threadId: string) => {
    selectThread(threadId);
    onCloseMobile?.();
  };

  return (
    <div className="flex h-full w-64 flex-col border-r border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 lg:w-72">
      {/* Header */}
      <div className="border-b border-gray-100 p-4 dark:border-gray-700">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🐱</span>
            <h1 className="text-lg font-bold text-gray-800 dark:text-gray-100">MeowAI</h1>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={handleCreate}
              className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              title="新建对话"
            >
              <Plus size={20} />
            </button>
            {/* Close button for mobile */}
            {onCloseMobile && (
              <button
                onClick={onCloseMobile}
                className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 lg:hidden"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            type="text"
            placeholder="搜索对话..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-8 pr-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">
            {threads.length === 0 ? "暂无对话，点击 + 创建" : "没有匹配的对话"}
          </div>
        ) : (
          filtered.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              isActive={thread.id === currentThreadId}
              onSelect={() => handleSelect(thread.id)}
            />
          ))
        )}
      </div>

      {/* Footer with version */}
      <div className="border-t border-gray-100 p-3 text-center text-xs text-gray-400 dark:border-gray-700 dark:text-gray-500">
        v0.5.0 · Phase 5
      </div>
    </div>
  );
}
