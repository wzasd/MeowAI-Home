import { useEffect, useState } from "react";
import { useThreadStore } from "../../stores/threadStore";
import { useCatStore } from "../../stores/catStore";
import { ThreadItem } from "./ThreadItem";
import { Plus, Search, X, Pin, Clock, Star, ChevronDown, ChevronRight } from "lucide-react";

interface ThreadSidebarProps {
  onCloseMobile?: () => void;
}

export function ThreadSidebar({ onCloseMobile }: ThreadSidebarProps) {
  const threads = useThreadStore((s) => s.threads);
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const fetchThreads = useThreadStore((s) => s.fetchThreads);
  const selectThread = useThreadStore((s) => s.selectThread);
  const createThread = useThreadStore((s) => s.createThread);
  const renameThread = useThreadStore((s) => s.renameThread);
  const archiveThread = useThreadStore((s) => s.archiveThread);
  const deleteThread = useThreadStore((s) => s.deleteThread);

  const cats = useCatStore((s) => s.cats);
  const defaultCatId = useCatStore((s) => s.defaultCatId);
  const fetchCats = useCatStore((s) => s.fetchCats);

  const [search, setSearch] = useState("");
  const [expandedSections, setExpandedSections] = useState({ recent: true, archived: false });

  const [isCreating, setIsCreating] = useState(false);
  const [newThreadName, setNewThreadName] = useState("");
  const [selectedCat, setSelectedCat] = useState("");
  const [projectPath, setProjectPath] = useState("");

  useEffect(() => {
    fetchThreads();
    fetchCats();
  }, [fetchThreads, fetchCats]);

  useEffect(() => {
    if (defaultCatId && !selectedCat) {
      setSelectedCat(defaultCatId);
    }
  }, [defaultCatId, selectedCat]);

  const filtered = threads.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));
  const activeThreads = filtered.filter((t) => !t.is_archived);
  const archivedThreads = filtered.filter((t) => t.is_archived);

  const pinnedThreads = activeThreads.slice(0, Math.min(2, activeThreads.length));
  const recentThreads = activeThreads.slice(Math.min(2, activeThreads.length));

  const handleStartCreate = () => {
    setNewThreadName(`对话 ${threads.length + 1}`);
    setProjectPath("");
    setSelectedCat(defaultCatId || cats[0]?.id || "orange");
    setIsCreating(true);
  };

  const handleCancelCreate = () => {
    setIsCreating(false);
  };

  const handleSubmitCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newThreadName.trim() || !projectPath.trim()) return;
    const id = await createThread(newThreadName.trim(), selectedCat || undefined, projectPath.trim());
    setIsCreating(false);
    if (id) await fetchThreads();
  };

  const handleSelect = (threadId: string) => {
    selectThread(threadId);
    onCloseMobile?.();
  };

  const toggleSection = (key: keyof typeof expandedSections) =>
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="flex flex-1 w-full flex-col overflow-hidden bg-white dark:bg-gray-800">
      {/* Header */}
      <div className="border-b border-gray-100 p-4 dark:border-gray-700">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🐱</span>
            <h1 className="text-lg font-bold text-gray-800 dark:text-gray-100">MeowAI</h1>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={handleStartCreate} className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700" title="新建对话">
              <Plus size={20} />
            </button>
            {onCloseMobile && (
              <button onClick={onCloseMobile} className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 lg:hidden">
                <X size={20} />
              </button>
            )}
          </div>
        </div>
        <div className="relative">
          <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          <input
            type="text" placeholder="搜索对话..." value={search} onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-8 pr-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:focus:ring-blue-500"
          />
        </div>

        {/* Create thread form */}
        {isCreating && (
          <form onSubmit={handleSubmitCreate} className="mt-3 space-y-2 rounded-lg border border-blue-100 bg-blue-50/50 p-3 dark:border-blue-900 dark:bg-blue-900/20">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-200">新建对话</span>
              <button type="button" onClick={handleCancelCreate} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <X size={14} />
              </button>
            </div>
            <input
              type="text"
              value={newThreadName}
              onChange={(e) => setNewThreadName(e.target.value)}
              placeholder="对话名称"
              className="w-full rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
              required
            />
            <select
              value={selectedCat}
              onChange={(e) => setSelectedCat(e.target.value)}
              className="w-full rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
            >
              {cats.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.displayName || cat.name}</option>
              ))}
            </select>
            <input
              type="text"
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder="项目目录绝对路径"
              className="w-full rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
              required
            />
            <button
              type="submit"
              className="w-full rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
            >
              创建
            </button>
          </form>
        )}
      </div>

      {/* Thread list with sections */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-4 text-center text-sm text-gray-400 dark:text-gray-500">
            {threads.length === 0 ? "暂无对话，点击 + 创建" : "没有匹配的对话"}
          </div>
        ) : (
          <>
            {/* Pinned section */}
            {pinnedThreads.length > 0 && (
              <SectionGroup
                title="置顶" icon={<Pin size={10} />} count={pinnedThreads.length}
                expanded={true} onToggle={() => {}}
              >
                {pinnedThreads.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isActive={thread.id === currentThreadId}
                    onSelect={() => handleSelect(thread.id)} onRename={renameThread} onArchive={archiveThread} onDelete={deleteThread}
                  />
                ))}
              </SectionGroup>
            )}

            {/* Recent section */}
            {recentThreads.length > 0 && (
              <SectionGroup
                title="最近" icon={<Clock size={10} />} count={recentThreads.length}
                expanded={expandedSections.recent} onToggle={() => toggleSection("recent")}
              >
                {recentThreads.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isActive={thread.id === currentThreadId}
                    onSelect={() => handleSelect(thread.id)} onRename={renameThread} onArchive={archiveThread} onDelete={deleteThread}
                  />
                ))}
              </SectionGroup>
            )}

            {/* Archived section */}
            {archivedThreads.length > 0 && (
              <SectionGroup
                title="已归档" icon={<Star size={10} />} count={archivedThreads.length}
                expanded={expandedSections.archived} onToggle={() => toggleSection("archived")}
              >
                {archivedThreads.map((thread) => (
                  <ThreadItem key={thread.id} thread={thread} isActive={thread.id === currentThreadId}
                    onSelect={() => handleSelect(thread.id)} onRename={renameThread} onArchive={archiveThread} onDelete={deleteThread}
                  />
                ))}
              </SectionGroup>
            )}
          </>
        )}
      </div>

      <div className="border-t border-gray-100 p-3 text-center text-xs text-gray-400 dark:border-gray-700 dark:text-gray-500">
        v0.8.0 · MeowAI Home
      </div>
    </div>
  );
}

function SectionGroup({
  title, icon, count, expanded, onToggle, children,
}: {
  title: string;
  icon: React.ReactNode;
  count: number;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase text-gray-400 hover:bg-gray-50 dark:text-gray-500 dark:hover:bg-gray-700/50"
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        {icon}
        {title}
        <span className="ml-auto rounded bg-gray-100 px-1 py-0.5 text-[9px] dark:bg-gray-700">{count}</span>
      </button>
      {expanded && children}
    </div>
  );
}
