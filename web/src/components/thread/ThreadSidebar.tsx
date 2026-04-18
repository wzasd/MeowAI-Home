import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  AlertTriangle,
  Archive,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Circle,
  Clock,
  FolderOpen,
  Layers,
  Plus,
  Search,
  Settings,
  Target,
  X,
} from "lucide-react";
import { api } from "../../api/client";
import type { MissionTask, Priority, TaskStatus } from "../../hooks/useMissions";
import { useCatStore } from "../../stores/catStore";
import { useThreadStore } from "../../stores/threadStore";
import { ThemeToggle } from "../ui/ThemeToggle";
import { ThreadItem } from "./ThreadItem";
import { buildThreadSidebarModel, type SidebarTaskGroup } from "./threadSidebarModel";

interface ThreadSidebarProps {
  onCloseMobile?: () => void;
  onOpenSettings?: () => void;
}

const STATUS_CONFIG: Record<TaskStatus, { icon: typeof Circle; color: string; label: string }> = {
  backlog: { icon: Circle, color: "text-gray-400", label: "待办池" },
  todo: { icon: Circle, color: "text-blue-500", label: "待开始" },
  doing: { icon: Clock, color: "text-amber-500", label: "进行中" },
  blocked: { icon: AlertTriangle, color: "text-red-500", label: "阻塞" },
  done: { icon: CheckCircle2, color: "text-emerald-500", label: "已完成" },
};

const PRIORITY_COLORS: Record<Priority, string> = {
  P0: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  P1: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  P2: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  P3: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
};

type SectionKey = "tasks" | "free" | "archived";

export function ThreadSidebar({ onCloseMobile, onOpenSettings }: ThreadSidebarProps) {
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
  const [tasks, setTasks] = useState<MissionTask[]>([]);
  const [expandedSections, setExpandedSections] = useState<Record<SectionKey, boolean>>({
    tasks: true,
    free: true,
    archived: false,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [newThreadName, setNewThreadName] = useState("");
  const [selectedCat, setSelectedCat] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [isPickingDirectory, setIsPickingDirectory] = useState(false);

  useEffect(() => {
    fetchThreads();
    fetchCats();
    api.missions
      .listTasks()
      .then((res) => {
        setTasks(res.tasks ?? []);
      })
      .catch(() => {
        setTasks([]);
      });
  }, [fetchThreads, fetchCats]);

  useEffect(() => {
    if (defaultCatId && !selectedCat) {
      setSelectedCat(defaultCatId);
    }
  }, [defaultCatId, selectedCat]);

  const model = buildThreadSidebarModel({
    search,
    threads,
    cats,
    tasks,
  });

  const handleStartCreate = () => {
    setNewThreadName(`猫窝 ${threads.length + 1}`);
    setProjectPath("");
    setSelectedCat(defaultCatId || cats[0]?.id || "orange");
    setIsCreating(true);
  };

  const handleCancelCreate = () => {
    setIsCreating(false);
  };

  const handleSubmitCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newThreadName.trim() || !projectPath.trim()) return;
    const id = await createThread(
      newThreadName.trim(),
      selectedCat || undefined,
      projectPath.trim()
    );
    setIsCreating(false);
    if (id) await fetchThreads();
  };

  const handlePickDirectory = async () => {
    setIsPickingDirectory(true);
    try {
      const { path } = await api.workspace.pickDirectory();
      if (path) setProjectPath(path);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.warn("Pick directory failed:", message);
    } finally {
      setIsPickingDirectory(false);
    }
  };

  const handleSelect = (threadId: string) => {
    selectThread(threadId);
    onCloseMobile?.();
  };

  const toggleSection = (key: SectionKey) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-transparent">
      <div className="border-b border-[var(--line)] px-3 py-3">
        <div className="nest-card nest-r-lg px-3 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="nest-kicker">猫窝工作室</span>
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
              </div>
              <div className="mt-1 text-[15px] font-semibold text-[var(--text-strong)]">
                {model.summary.title}
              </div>
              <p className="mt-1 text-[12px] font-medium leading-5 text-[var(--text-soft)]">
                {model.summary.compactLine}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-[var(--line)] pt-2 text-[10px] text-[var(--text-faint)]">
                <HeaderMetric label="在线" value={String(model.summary.activeNestCount)} />
                <HeaderMetric label="自由" value={String(model.summary.freeNestCount)} />
                <HeaderMetric label="值班" value={String(model.summary.onDutyCatCount)} />
                <HeaderMetric label="任务" value={String(model.summary.activeTaskCount)} />
                {model.summary.blockedTaskCount > 0 && (
                  <HeaderMetric label="阻塞" value={String(model.summary.blockedTaskCount)} />
                )}
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleStartCreate}
                className="nest-button-primary flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                title="新建猫窝"
              >
                <Plus size={16} />
              </button>
              {onCloseMobile && (
                <button
                  type="button"
                  onClick={onCloseMobile}
                  className="nest-button-ghost flex h-9 w-9 shrink-0 items-center justify-center rounded-full lg:hidden"
                  title="关闭"
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="mt-2 flex items-center gap-2">
          <div className="relative min-w-0 flex-1">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)]"
            />
            <input
              type="text"
              placeholder="搜索猫窝 / 任务 / 项目..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="nest-field nest-r-md w-full py-2.5 pl-9 pr-3 text-sm"
            />
          </div>
        </div>

        {isCreating && (
          <form onSubmit={handleSubmitCreate} className="nest-card nest-r-lg mt-2 space-y-3 p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="nest-kicker">新建猫窝</div>
                <div className="mt-1 text-sm font-semibold text-[var(--text-strong)]">
                  新开一个工作上下文
                </div>
              </div>
              <button
                type="button"
                onClick={handleCancelCreate}
                className="nest-button-ghost flex h-8 w-8 items-center justify-center rounded-full"
                title="收起"
              >
                <X size={14} />
              </button>
            </div>

            <input
              type="text"
              value={newThreadName}
              onChange={(e) => setNewThreadName(e.target.value)}
              placeholder="猫窝名称"
              className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
              required
            />

            <select
              value={selectedCat}
              onChange={(e) => setSelectedCat(e.target.value)}
              className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
            >
              {cats.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.displayName || cat.name}
                </option>
              ))}
            </select>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder="项目目录绝对路径"
                className="nest-field nest-r-sm min-w-0 flex-1 px-3 py-2.5 text-sm"
                required
              />
              <button
                type="button"
                onClick={handlePickDirectory}
                disabled={isPickingDirectory}
                className="nest-button-secondary flex h-10 shrink-0 items-center gap-1.5 rounded-full px-3 text-xs"
              >
                <FolderOpen size={14} />
                浏览
              </button>
            </div>

            <button
              type="submit"
              className="nest-button-primary w-full rounded-full px-3 py-2.5 text-sm font-semibold"
            >
              创建猫窝
            </button>
          </form>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2">
        {model.isEmpty ? (
          <div className="nest-card nest-r-md mx-2 p-5 text-center text-sm text-[var(--text-faint)]">
            {model.emptyMessage}
          </div>
        ) : (
          <>
            {model.taskGroups.length > 0 && (
              <SectionGroup
                title="任务猫窝"
                icon={<Target size={10} />}
                countLabel={`${model.taskGroups.reduce((sum, group) => sum + group.threads.length, 0)} 个窝`}
                expanded={expandedSections.tasks}
                onToggle={() => toggleSection("tasks")}
              >
                <div className="space-y-2 px-1">
                  {model.taskGroups.map((group) => (
                    <TaskThreadGroup
                      key={group.task.id}
                      group={group}
                      currentThreadId={currentThreadId}
                      onSelect={handleSelect}
                      onRename={renameThread}
                      onArchive={archiveThread}
                      onDelete={deleteThread}
                    />
                  ))}
                </div>
              </SectionGroup>
            )}

            {model.freeThreads.length > 0 && (
              <SectionGroup
                title="自由猫窝"
                icon={<Layers size={10} />}
                countLabel={`${model.freeThreads.length} 个窝`}
                expanded={expandedSections.free}
                onToggle={() => toggleSection("free")}
              >
                {model.freeThreads.map((thread) => (
                  <ThreadItem
                    key={thread.id}
                    thread={thread}
                    isActive={thread.id === currentThreadId}
                    onSelect={() => handleSelect(thread.id)}
                    onRename={renameThread}
                    onArchive={archiveThread}
                    onDelete={deleteThread}
                  />
                ))}
              </SectionGroup>
            )}

            {model.archivedThreads.length > 0 && (
              <SectionGroup
                title="已归档"
                icon={<Archive size={10} />}
                countLabel={`${model.archivedThreads.length} 个窝`}
                expanded={expandedSections.archived}
                onToggle={() => toggleSection("archived")}
              >
                {model.archivedThreads.map((thread) => (
                  <ThreadItem
                    key={thread.id}
                    thread={thread}
                    isActive={thread.id === currentThreadId}
                    onSelect={() => handleSelect(thread.id)}
                    onRename={renameThread}
                    onArchive={archiveThread}
                    onDelete={deleteThread}
                  />
                ))}
              </SectionGroup>
            )}
          </>
        )}
      </div>

      <div className="border-t border-[var(--line)] px-3 py-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <button
              onClick={onOpenSettings}
              className="nest-button-secondary flex h-9 w-9 items-center justify-center rounded-full"
              title="设置"
            >
              <Settings size={16} />
            </button>
            <ThemeToggle />
          </div>
          <div className="text-[10px] tracking-[0.08em] text-[var(--text-faint)]">暖窝模式</div>
        </div>
      </div>
    </div>
  );
}

function HeaderMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span>{label}</span>
      <span className="text-[11px] font-semibold text-[var(--text-strong)]">{value}</span>
    </div>
  );
}

function TaskThreadGroup({
  group,
  currentThreadId,
  onSelect,
  onRename,
  onArchive,
  onDelete,
}: {
  group: SidebarTaskGroup;
  currentThreadId: string | null;
  onSelect: (id: string) => void;
  onRename: (id: string, name: string) => Promise<void>;
  onArchive: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const { task, threads } = group;
  const [expanded, setExpanded] = useState(task.status !== "done");
  const cfg = STATUS_CONFIG[task.status];
  const StatusIcon = cfg.icon;
  const metaParts = [cfg.label, `${threads.length} 个窝`];

  if (task.ownerCat) {
    metaParts.push(task.ownerCat.replace(/^@/, ""));
  }

  return (
    <div className="nest-card nest-r-md border-[var(--border-strong)]/60 p-2.5">
      <button
        type="button"
        onClick={() => setExpanded((value) => !value)}
        className="flex w-full items-start gap-2 text-left"
      >
        <div className="mt-0.5 text-[var(--text-faint)]">
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-[var(--text-strong)]">
              {task.title}
            </span>
            <span
              className={`shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-bold ${PRIORITY_COLORS[task.priority]}`}
            >
              {task.priority}
            </span>
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px] text-[var(--text-faint)]">
            <StatusIcon size={10} className={cfg.color} />
            <span>{metaParts.join(" · ")}</span>
          </div>
        </div>
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5 border-t border-[var(--line)] pt-2">
          {threads.map((thread) => (
            <ThreadItem
              key={thread.id}
              thread={thread}
              isActive={thread.id === currentThreadId}
              onSelect={() => onSelect(thread.id)}
              onRename={onRename}
              onArchive={onArchive}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SectionGroup({
  title,
  icon,
  countLabel,
  expanded,
  onToggle,
  children,
}: {
  title: string;
  icon: ReactNode;
  countLabel: string;
  expanded: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <div className="mb-2">
      <button
        type="button"
        onClick={onToggle}
        className="mx-2 flex w-[calc(100%-1rem)] items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-semibold tracking-[0.12em] text-[var(--text-faint)] transition-colors hover:bg-white/40 dark:hover:bg-white/5"
      >
        {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        {icon}
        <span>{title}</span>
        <span className="ml-auto text-[10px] tracking-normal">{countLabel}</span>
      </button>

      {expanded && <div className="px-1 pt-1">{children}</div>}
    </div>
  );
}
