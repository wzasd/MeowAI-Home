/** Mission Hub — task board with backlog, features, and dependency tracking. */

import { useState, useMemo } from "react";
import {
  LayoutGrid,
  List,
  Plus,
  Circle,
  CheckCircle2,
  Clock,
  AlertTriangle,
  User,
  BarChart3,
  Target,
  AlertCircle,
  Loader2,
  X,
  GitBranch,
  Zap,
  Layers,
  Settings2,
  MessageSquare,
} from "lucide-react";
import {
  useMissions,
  type MissionTask,
  type TaskStatus,
  type Priority,
} from "../../hooks/useMissions";
import { useWorkflows } from "../../hooks/useWorkflows";
import { PageHeader } from "../ui/PageHeader";
import { SlidingNav } from "../ui/SlidingNav";

const PRIORITY_COLORS: Record<Priority, string> = {
  P0: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  P1: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  P2: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  P3: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
};

const STATUS_CONFIG: Record<TaskStatus, { icon: typeof Circle; color: string; label: string }> = {
  backlog: { icon: Circle, color: "text-gray-400", label: "待办池" },
  todo: { icon: Circle, color: "text-blue-500", label: "待开始" },
  doing: { icon: Clock, color: "text-amber-500", label: "进行中" },
  blocked: { icon: AlertTriangle, color: "text-red-500", label: "阻塞" },
  done: { icon: CheckCircle2, color: "text-green-500", label: "已完成" },
};

function TaskCard({
  task,
  onStatusChange,
  onOpenThread,
}: {
  task: MissionTask;
  onStatusChange?: (id: string, status: TaskStatus) => void;
  onOpenThread?: (threadId: string) => void;
}) {
  const cfg = STATUS_CONFIG[task.status];
  const StatusIcon = cfg.icon;
  const sessionCount = task.session_ids?.length ?? 0;
  const threadCount = task.thread_ids?.length ?? 0;
  const firstThreadId = task.thread_ids?.[0];

  return (
    <div className="nest-card nest-r-lg p-4 transition-transform duration-150 hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h4 className="truncate text-sm font-semibold text-[var(--text-strong)]">{task.title}</h4>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-1 text-[10px] font-bold ${PRIORITY_COLORS[task.priority]}`}
        >
          {task.priority}
        </span>
      </div>
      <p className="mt-2 line-clamp-2 text-xs leading-6 text-[var(--text-soft)]">
        {task.description}
      </p>
      {task.progress !== undefined && task.progress < 100 && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
          <div
            className="h-full rounded-full bg-[var(--accent)]"
            style={{ width: `${task.progress}%` }}
          />
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {task.ownerCat && (
          <span className="nest-chip px-2 py-1 text-[10px] text-[var(--moss)]">
            <User size={10} /> {task.ownerCat}
          </span>
        )}
        {task.tags.slice(0, 2).map((tag) => (
          <span key={tag} className="nest-chip px-2 py-1 text-[10px]">
            {tag}
          </span>
        ))}
        {task.dueDate && (
          <span className="flex items-center gap-0.5 text-[10px] text-[var(--danger)]">
            <AlertCircle size={10} /> {task.dueDate.slice(5)}
          </span>
        )}
        {sessionCount > 0 && (
          <span className="nest-chip px-2 py-1 text-[10px] text-[var(--accent)]">
            {sessionCount} 会话
          </span>
        )}
        {threadCount > 0 && (
          <span className="nest-chip px-2 py-1 text-[10px] text-[var(--text-soft)]">
            {threadCount} 猫窝
          </span>
        )}
        {firstThreadId && onOpenThread && (
          <button
            onClick={() => onOpenThread(firstThreadId)}
            className="nest-button-secondary rounded-full p-1.5 text-[var(--text-faint)] hover:text-[var(--accent)]"
            title="进入猫窝"
          >
            <MessageSquare size={12} />
          </button>
        )}
        {onStatusChange && task.status !== "done" && (
          <button
            onClick={() => onStatusChange(task.id, task.status === "doing" ? "done" : "doing")}
            className="nest-button-secondary ml-auto rounded-full p-1.5 text-[var(--text-faint)] hover:text-green-600"
            title={task.status === "doing" ? "标记完成" : "开始处理"}
          >
            <StatusIcon size={12} className={cfg.color} />
          </button>
        )}
      </div>
    </div>
  );
}

function KanbanColumn({
  status,
  tasks,
  onStatusChange,
  onOpenThread,
}: {
  status: TaskStatus;
  tasks: MissionTask[];
  onStatusChange?: (id: string, status: TaskStatus) => void;
  onOpenThread?: (threadId: string) => void;
}) {
  const cfg = STATUS_CONFIG[status];
  const StatusIcon = cfg.icon;
  return (
    <div className="nest-panel-strong nest-r-xl flex w-[18.2rem] shrink-0 flex-col p-3 lg:w-[19rem]">
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/55 text-[var(--accent)] dark:bg-white/5">
          <StatusIcon size={14} className={cfg.color} />
        </div>
        <div>
          <span className="text-sm font-semibold text-[var(--text-strong)]">{cfg.label}</span>
          <div className="text-[10px] uppercase tracking-[0.2em] text-[var(--text-faint)]">
            {tasks.length} cards
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onStatusChange={onStatusChange}
            onOpenThread={onOpenThread}
          />
        ))}
        {tasks.length === 0 && (
          <div className="nest-r-md border border-dashed border-[var(--border)] bg-white/20 p-4 text-center text-xs text-[var(--text-faint)] dark:bg-white/5">
            暂无任务
          </div>
        )}
      </div>
    </div>
  );
}

function StatsBar({
  tasks,
  loading,
  stats,
}: {
  tasks: MissionTask[];
  loading: boolean;
  stats: { total: number; done: number; doing: number; blocked: number } | null;
}) {
  const done = stats?.done ?? tasks.filter((t) => t.status === "done").length;
  const total = stats?.total ?? tasks.length;
  const doing = stats?.doing ?? tasks.filter((t) => t.status === "doing").length;
  const blocked = stats?.blocked ?? tasks.filter((t) => t.status === "blocked").length;

  if (loading) {
    return (
      <div className="flex items-center gap-3 text-[var(--text-faint)]">
        <Loader2 size={14} className="animate-spin" />
        <span className="text-xs">正在整理任务温度...</span>
      </div>
    );
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {[
        { icon: Target, label: "全部任务", value: total, tone: "text-[var(--text-soft)]" },
        { icon: CheckCircle2, label: "已完成", value: done, tone: "text-green-600" },
        { icon: Clock, label: "进行中", value: doing, tone: "text-amber-600" },
        { icon: AlertTriangle, label: "阻塞", value: blocked, tone: "text-[var(--danger)]" },
      ].map((item) => (
        <div key={item.label} className="nest-card nest-r-md px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--text-faint)]">{item.label}</span>
            <item.icon size={14} className={item.tone} />
          </div>
          <div className="mt-2 text-xl font-semibold text-[var(--text-strong)]">{item.value}</div>
        </div>
      ))}
      <div className="nest-card nest-r-md px-4 py-3 sm:col-span-2 xl:col-span-4">
        <div className="flex items-center justify-between text-xs text-[var(--text-faint)]">
          <span>完成热度</span>
          <span>{total > 0 ? Math.round((done / total) * 100) : 0}%</span>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
          <div
            className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent),var(--moss))]"
            style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function CreateTaskModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (task: Omit<MissionTask, "id" | "createdAt">) => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Priority>("P2");
  const [status, setStatus] = useState<TaskStatus>("backlog");

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onCreate({
      title: title.trim(),
      description: description.trim(),
      priority,
      status,
      tags: [],
    });
    setTitle("");
    setDescription("");
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="nest-panel-strong nest-r-xl w-full max-w-md p-6"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div>
            <div className="nest-kicker">任务创建</div>
            <h3 className="nest-title mt-2 text-2xl font-semibold text-[var(--text-strong)]">
              新建任务
            </h3>
          </div>
          <button
            onClick={onClose}
            className="nest-button-ghost flex h-9 w-9 items-center justify-center rounded-full"
          >
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-soft)]">标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
              placeholder="输入任务标题..."
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-[var(--text-soft)]">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
              rows={3}
              placeholder="输入任务描述..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-[var(--text-soft)]">
                优先级
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority)}
                className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
              >
                <option value="P0">P0 - 最高</option>
                <option value="P1">P1 - 高</option>
                <option value="P2">P2 - 中</option>
                <option value="P3">P3 - 低</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-[var(--text-soft)]">状态</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as TaskStatus)}
                className="nest-field nest-r-sm w-full px-3 py-2.5 text-sm"
              >
                <option value="backlog">待办池</option>
                <option value="todo">待开始</option>
                <option value="doing">进行中</option>
                <option value="blocked">阻塞</option>
                <option value="done">已完成</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="nest-button-secondary px-4 py-2 text-sm"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="nest-button-primary px-4 py-2 text-sm disabled:opacity-50"
            >
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function WorkflowTab() {
  const { templates, active, loading, error, fetchWorkflows } = useWorkflows();

  return (
    <div className="h-full overflow-auto p-4">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="nest-title text-xl font-semibold text-[var(--text-strong)]">工作流模板</h3>
        <button onClick={fetchWorkflows} className="nest-button-secondary px-3 py-1.5 text-xs">
          刷新
        </button>
      </div>
      {loading && <Loader2 size={20} className="animate-spin text-[var(--text-faint)]" />}
      {error && <div className="text-xs text-[var(--danger)]">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((t) => (
          <div key={t.id} className="nest-card nest-r-lg p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--text-strong)]">
              <GitBranch size={14} className="text-[var(--accent)]" />
              {t.name}
            </div>
            <p className="mt-2 text-xs leading-6 text-[var(--text-soft)]">{t.description}</p>
          </div>
        ))}
      </div>

      <h3 className="nest-title mb-3 mt-6 text-xl font-semibold text-[var(--text-strong)]">
        活跃工作流
      </h3>
      {active.length === 0 ? (
        <div className="nest-r-lg border border-dashed border-[var(--border)] bg-white/15 p-4 text-center text-xs text-[var(--text-faint)]">
          暂无活跃工作流
        </div>
      ) : (
        <div className="space-y-2">
          {active.map((w) => (
            <div key={w.id} className="nest-card nest-r-md flex items-center justify-between p-4">
              <span className="text-sm text-[var(--text-strong)]">{w.name || w.id}</span>
              <span className="nest-chip px-2 py-1 text-[10px] text-[var(--accent)]">
                {w.status || "running"}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FeaturesTab({ tasks }: { tasks: MissionTask[] }) {
  const features = useMemo(() => {
    const map = new Map<string, MissionTask[]>();
    tasks.forEach((t) => {
      const key = t.tags[0] || "未分类";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(t);
    });
    return Array.from(map.entries()).map(([name, ft]) => ({
      name,
      total: ft.length,
      done: ft.filter((x) => x.status === "done").length,
      doing: ft.filter((x) => x.status === "doing").length,
      blocked: ft.filter((x) => x.status === "blocked").length,
      progress:
        ft.length > 0
          ? Math.round((ft.filter((x) => x.status === "done").length / ft.length) * 100)
          : 0,
    }));
  }, [tasks]);

  return (
    <div className="h-full overflow-auto p-4">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-[var(--text-strong)]">
        <BarChart3 size={16} />
        功能模块进度
      </div>
      {features.length === 0 ? (
        <div className="flex h-64 items-center justify-center text-[var(--text-faint)]">
          暂无功能数据
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.name} className="nest-card nest-r-lg p-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-[var(--text-strong)]">{f.name}</h4>
                <span className="text-xs text-[var(--text-faint)]">{f.progress}%</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,var(--accent),var(--moss))]"
                  style={{ width: `${f.progress}%` }}
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-[var(--text-soft)]">
                <span>{f.total} 任务</span>
                <span className="text-green-600">{f.done} 完成</span>
                <span className="text-amber-600">{f.doing} 进行中</span>
                {f.blocked > 0 && <span className="text-red-600">{f.blocked} 阻塞</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ResolutionsTab({
  tasks,
  onStatusChange,
}: {
  tasks: MissionTask[];
  onStatusChange?: (id: string, status: TaskStatus) => void;
}) {
  const blocked = tasks.filter((t) => t.status === "blocked");
  const dueSoon = tasks.filter((t) => {
    if (!t.dueDate || t.status === "done") return false;
    const due = new Date(t.dueDate);
    const now = new Date();
    const diff = (due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
    return diff <= 3;
  });
  const unassigned = tasks.filter((t) => !t.ownerCat && t.status !== "done");

  return (
    <div className="h-full overflow-auto p-4">
      {blocked.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-[var(--danger)]">
            <AlertTriangle size={14} /> 阻塞项 ({blocked.length})
          </h3>
          <div className="space-y-2">
            {blocked.map((t) => (
              <div
                key={t.id}
                className="nest-card nest-r-md flex items-center justify-between border-red-100/70 p-4 dark:border-red-900/30"
              >
                <div>
                  <div className="text-sm font-semibold text-[var(--text-strong)]">{t.title}</div>
                  <div className="text-xs text-[var(--text-soft)]">{t.description}</div>
                </div>
                {onStatusChange && (
                  <button
                    onClick={() => onStatusChange(t.id, "todo")}
                    className="nest-button-secondary px-3 py-1.5 text-xs"
                  >
                    解除阻塞
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {dueSoon.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-amber-600">
            <Clock size={14} /> 即将到期 ({dueSoon.length})
          </h3>
          <div className="space-y-2">
            {dueSoon.map((t) => (
              <div key={t.id} className="nest-card nest-r-md flex items-center justify-between p-4">
                <div>
                  <div className="text-sm font-semibold text-[var(--text-strong)]">{t.title}</div>
                  <div className="text-xs text-[var(--text-soft)]">截止: {t.dueDate}</div>
                </div>
                <span className="nest-chip px-2 py-1 text-[10px] text-amber-700">{t.priority}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {unassigned.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-[var(--moss)]">
            <User size={14} /> 待分配 ({unassigned.length})
          </h3>
          <div className="space-y-2">
            {unassigned.map((t) => (
              <div key={t.id} className="nest-card nest-r-md p-4">
                <div className="text-sm font-semibold text-[var(--text-strong)]">{t.title}</div>
                <div className="text-xs text-[var(--text-soft)]">{t.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {blocked.length === 0 && dueSoon.length === 0 && unassigned.length === 0 && (
        <div className="flex h-64 items-center justify-center text-[var(--text-faint)]">
          <div className="text-center">
            <CheckCircle2 size={32} className="mx-auto mb-2 text-green-500" />
            <p>当前无需要处理的风险项</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function MissionHubPage({ onOpenThread }: { onOpenThread?: (threadId: string) => void }) {
  const {
    tasks,
    loading,
    error,
    filterPriority,
    setFilterPriority,
    fetchTasks,
    createTask,
    updateTaskStatus,
    stats,
  } = useMissions();

  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [tab, setTab] = useState<"projects" | "workflows" | "features" | "resolutions">("projects");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const filtered =
    filterPriority === "all" ? tasks : tasks.filter((t) => t.priority === filterPriority);
  const columns: TaskStatus[] = ["backlog", "todo", "doing", "blocked", "done"];

  const handleCreateTask = async (taskData: Omit<MissionTask, "id" | "createdAt">) => {
    await createTask(taskData);
  };

  const handleStatusChange = async (taskId: string, status: TaskStatus) => {
    await updateTaskStatus(taskId, status);
  };

  return (
    <div className="flex h-full flex-col bg-transparent">
      <PageHeader
        eyebrow="任务墙"
        title="猫窝任务墙"
        description="把捡回来的任务、阻塞和进度摊成一整面墙。重要的事情先亮出来，不让它们埋在列表里。"
        actions={
          <>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="nest-button-primary px-4 py-2 text-xs font-semibold"
            >
              <Plus size={12} /> 新任务
            </button>
            {tab === "projects" && (
              <div className="nest-panel flex rounded-full p-1">
                <button
                  onClick={() => setView("kanban")}
                  className={`nest-tab ${view === "kanban" ? "nest-tab-active" : ""}`}
                >
                  <LayoutGrid size={14} />
                </button>
                <button
                  onClick={() => setView("list")}
                  className={`nest-tab ${view === "list" ? "nest-tab-active" : ""}`}
                >
                  <List size={14} />
                </button>
              </div>
            )}
          </>
        }
      >
        {tab === "projects" && <StatsBar tasks={tasks} loading={loading} stats={stats} />}

        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="w-full max-w-[22rem]">
            <SlidingNav
              items={[
                { key: "projects", label: "项目", icon: Layers },
                { key: "workflows", label: "工作流", icon: GitBranch },
                { key: "features", label: "功能", icon: Zap },
                { key: "resolutions", label: "决议队列", icon: Settings2 },
              ]}
              activeKey={tab}
              onChange={(key) =>
                setTab(key as "projects" | "workflows" | "features" | "resolutions")
              }
              className="nest-nav-strip-compact"
            />
          </div>
          {tab === "projects" && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-xs text-[var(--text-faint)]">筛选</span>
              {(["all", "P0", "P1", "P2", "P3"] as const).map((p) => (
                <button
                  key={p}
                  onClick={() => setFilterPriority(p)}
                  className={`rounded-full px-3 py-1.5 text-[10px] font-medium ${
                    filterPriority === p
                      ? PRIORITY_COLORS[p as Priority] || "bg-gray-200 text-gray-800"
                      : "nest-chip"
                  }`}
                >
                  {p === "all" ? "全部" : p}
                </button>
              ))}
            </div>
          )}
        </div>
      </PageHeader>

      {error && (
        <div className="nest-r-md mx-4 mt-3 flex items-center gap-2 bg-red-50/80 px-4 py-3 text-xs text-[var(--danger)] dark:bg-red-900/20 lg:mx-6">
          <AlertCircle size={14} />
          {error}
          <button onClick={fetchTasks} className="ml-auto underline decoration-dotted">
            重试
          </button>
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        {tab === "projects" && (
          <div className="h-full overflow-x-auto p-4">
            {loading && tasks.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 size={32} className="animate-spin text-[var(--text-faint)]" />
              </div>
            ) : view === "kanban" ? (
              <div className="flex gap-4" style={{ minWidth: columns.length * 280 }}>
                {columns.map((status) => (
                  <KanbanColumn
                    key={status}
                    status={status}
                    tasks={filtered.filter((t) => t.status === status)}
                    onStatusChange={handleStatusChange}
                    onOpenThread={onOpenThread}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {filtered.map((task) => {
                  const cfg = STATUS_CONFIG[task.status];
                  const CfgIcon = cfg.icon;
                  return (
                    <div key={task.id} className="nest-card nest-r-md flex items-center gap-3 p-4">
                      <span
                        className={`rounded-full px-2 py-1 text-[10px] font-bold ${PRIORITY_COLORS[task.priority]}`}
                      >
                        {task.priority}
                      </span>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-[var(--text-strong)]">
                          {task.title}
                        </h4>
                        <p className="text-xs text-[var(--text-soft)]">{task.description}</p>
                      </div>
                      <span className="flex items-center gap-0.5 text-xs">
                        <CfgIcon size={12} className={cfg.color} />
                        <span className="text-[var(--text-soft)]">{cfg.label}</span>
                      </span>
                      {task.ownerCat && (
                        <span className="text-xs text-[var(--moss)]">@{task.ownerCat}</span>
                      )}
                      {(task.session_ids?.length ?? 0) > 0 && (
                        <span className="text-[10px] text-[var(--accent)]">
                          {task.session_ids!.length} 会话
                        </span>
                      )}
                      {(task.thread_ids?.length ?? 0) > 0 && (
                        <span className="text-[10px] text-[var(--text-soft)]">
                          {task.thread_ids!.length} 猫窝
                        </span>
                      )}
                      {task.thread_ids?.[0] && onOpenThread && (
                        <button
                          onClick={() => {
                            const threadId = task.thread_ids?.[0];
                            if (threadId) onOpenThread(threadId);
                          }}
                          className="nest-button-secondary rounded-full p-1.5 text-[var(--text-faint)] hover:text-[var(--accent)]"
                          title="进入猫窝"
                        >
                          <MessageSquare size={12} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        {tab === "workflows" && <WorkflowTab />}
        {tab === "features" && <FeaturesTab tasks={tasks} />}
        {tab === "resolutions" && (
          <ResolutionsTab tasks={tasks} onStatusChange={handleStatusChange} />
        )}
      </div>

      <CreateTaskModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateTask}
      />
    </div>
  );
}
