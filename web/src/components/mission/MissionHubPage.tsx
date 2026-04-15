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
} from "lucide-react";
import {
  useMissions,
  type MissionTask,
  type TaskStatus,
  type Priority,
} from "../../hooks/useMissions";
import { useWorkflows } from "../../hooks/useWorkflows";

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
}: {
  task: MissionTask;
  onStatusChange?: (id: string, status: TaskStatus) => void;
}) {
  const cfg = STATUS_CONFIG[task.status];
  const StatusIcon = cfg.icon;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200">{task.title}</h4>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${PRIORITY_COLORS[task.priority]}`}>
          {task.priority}
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">{task.description}</p>
      {task.progress !== undefined && task.progress < 100 && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
          <div className="h-full rounded-full bg-blue-500" style={{ width: `${task.progress}%` }} />
        </div>
      )}
      <div className="mt-2 flex items-center gap-2">
        {task.ownerCat && (
          <span className="flex items-center gap-0.5 rounded bg-purple-50 px-1.5 py-0.5 text-[10px] text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
            <User size={10} /> {task.ownerCat}
          </span>
        )}
        {task.tags.slice(0, 2).map((tag) => (
          <span key={tag} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
            {tag}
          </span>
        ))}
        {task.dueDate && (
          <span className="flex items-center gap-0.5 text-[10px] text-red-500">
            <AlertCircle size={10} /> {task.dueDate.slice(5)}
          </span>
        )}
        {onStatusChange && task.status !== "done" && (
          <button
            onClick={() => onStatusChange(task.id, task.status === "doing" ? "done" : "doing")}
            className="ml-auto rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-green-500 dark:hover:bg-gray-700"
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
}: {
  status: TaskStatus;
  tasks: MissionTask[];
  onStatusChange?: (id: string, status: TaskStatus) => void;
}) {
  const cfg = STATUS_CONFIG[status];
  const StatusIcon = cfg.icon;
  return (
    <div className="flex w-64 shrink-0 flex-col lg:w-72">
      <div className="mb-2 flex items-center gap-1.5">
        <StatusIcon size={14} className={cfg.color} />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">{cfg.label}</span>
        <span className="rounded bg-gray-200 px-1 py-0.5 text-[10px] text-gray-600 dark:bg-gray-600 dark:text-gray-300">{tasks.length}</span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onStatusChange={onStatusChange} />
        ))}
        {tasks.length === 0 && (
          <div className="rounded-lg border-2 border-dashed border-gray-200 p-4 text-center text-xs text-gray-400 dark:border-gray-700">
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
      <div className="flex items-center gap-4">
        <Loader2 size={14} className="animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
        <Target size={14} /> {total} 任务
      </div>
      <div className="flex items-center gap-1 text-xs text-green-600">
        <CheckCircle2 size={14} /> {done} 完成
      </div>
      <div className="flex items-center gap-1 text-xs text-amber-600">
        <Clock size={14} /> {doing} 进行中
      </div>
      <div className="flex items-center gap-1 text-xs text-red-600">
        <AlertTriangle size={14} /> {blocked} 阻塞
      </div>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div className="h-full rounded-full bg-green-500" style={{ width: `${total > 0 ? (done / total) * 100 : 0}%` }} />
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">新建任务</h3>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">标题</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="输入任务标题..."
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              rows={3}
              placeholder="输入任务描述..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">优先级</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="P0">P0 - 最高</option>
                <option value="P1">P1 - 高</option>
                <option value="P2">P2 - 中</option>
                <option value="P3">P3 - 低</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">状态</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as TaskStatus)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
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
              className="rounded bg-gray-200 px-4 py-2 text-sm text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
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
        <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">工作流模板</h3>
        <button
          onClick={fetchWorkflows}
          className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          刷新
        </button>
      </div>
      {loading && <Loader2 size={20} className="animate-spin text-gray-400" />}
      {error && <div className="text-xs text-red-500">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((t) => (
          <div
            key={t.id}
            className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
          >
            <div className="flex items-center gap-2 text-sm font-medium text-gray-800 dark:text-gray-200">
              <GitBranch size={14} className="text-blue-500" />
              {t.name}
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{t.description}</p>
          </div>
        ))}
      </div>

      <h3 className="mb-3 mt-6 text-sm font-semibold text-gray-800 dark:text-gray-200">活跃工作流</h3>
      {active.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-200 p-4 text-center text-xs text-gray-400 dark:border-gray-700">
          暂无活跃工作流
        </div>
      ) : (
        <div className="space-y-2">
          {active.map((w) => (
            <div
              key={w.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
            >
              <span className="text-sm text-gray-800 dark:text-gray-200">{w.name || w.id}</span>
              <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
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
      progress: ft.length > 0 ? Math.round((ft.filter((x) => x.status === "done").length / ft.length) * 100) : 0,
    }));
  }, [tasks]);

  return (
    <div className="h-full overflow-auto p-4">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-gray-200">
        <BarChart3 size={16} />
        功能模块进度
      </div>
      {features.length === 0 ? (
        <div className="flex h-64 items-center justify-center text-gray-400">
          暂无功能数据
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.name}
              className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200">{f.name}</h4>
                <span className="text-xs text-gray-500">{f.progress}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                <div className="h-full rounded-full bg-green-500" style={{ width: `${f.progress}%` }} />
              </div>
              <div className="mt-2 flex gap-3 text-[10px] text-gray-500 dark:text-gray-400">
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

function ResolutionsTab({ tasks, onStatusChange }: { tasks: MissionTask[]; onStatusChange?: (id: string, status: TaskStatus) => void }) {
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
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-red-600">
            <AlertTriangle size={14} /> 阻塞项 ({blocked.length})
          </h3>
          <div className="space-y-2">
            {blocked.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between rounded-lg border border-red-100 bg-red-50 p-3 dark:border-red-900/30 dark:bg-red-900/10"
              >
                <div>
                  <div className="text-sm font-medium text-gray-800 dark:text-gray-200">{t.title}</div>
                  <div className="text-xs text-gray-500">{t.description}</div>
                </div>
                {onStatusChange && (
                  <button
                    onClick={() => onStatusChange(t.id, "todo")}
                    className="rounded bg-white px-2 py-1 text-xs text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200"
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
              <div
                key={t.id}
                className="flex items-center justify-between rounded-lg border border-amber-100 bg-amber-50 p-3 dark:border-amber-900/30 dark:bg-amber-900/10"
              >
                <div>
                  <div className="text-sm font-medium text-gray-800 dark:text-gray-200">{t.title}</div>
                  <div className="text-xs text-gray-500">截止: {t.dueDate}</div>
                </div>
                <span className="rounded bg-white px-1.5 py-0.5 text-[10px] text-amber-700 dark:bg-gray-700">
                  {t.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {unassigned.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-2 flex items-center gap-1 text-sm font-semibold text-blue-600">
            <User size={14} /> 待分配 ({unassigned.length})
          </h3>
          <div className="space-y-2">
            {unassigned.map((t) => (
              <div
                key={t.id}
                className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="text-sm font-medium text-gray-800 dark:text-gray-200">{t.title}</div>
                <div className="text-xs text-gray-500">{t.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {blocked.length === 0 && dueSoon.length === 0 && unassigned.length === 0 && (
        <div className="flex h-64 items-center justify-center text-gray-400">
          <div className="text-center">
            <CheckCircle2 size={32} className="mx-auto mb-2 text-green-500" />
            <p>当前无需要处理的风险项</p>
          </div>
        </div>
      )}
    </div>
  );
}

export function MissionHubPage() {
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

  const filtered = filterPriority === "all" ? tasks : tasks.filter((t) => t.priority === filterPriority);
  const columns: TaskStatus[] = ["backlog", "todo", "doing", "blocked", "done"];

  const handleCreateTask = async (taskData: Omit<MissionTask, "id" | "createdAt">) => {
    await createTask(taskData);
  };

  const handleStatusChange = async (taskId: string, status: TaskStatus) => {
    await updateTaskStatus(taskId, status);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Mission Hub</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700"
            >
              <Plus size={12} /> 新任务
            </button>
            {tab === "projects" && (
              <div className="flex rounded border border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setView("kanban")}
                  className={`rounded-l px-2 py-1 ${view === "kanban" ? "bg-gray-100 dark:bg-gray-700" : ""}`}
                >
                  <LayoutGrid size={14} className="text-gray-600 dark:text-gray-400" />
                </button>
                <button
                  onClick={() => setView("list")}
                  className={`rounded-r px-2 py-1 ${view === "list" ? "bg-gray-100 dark:bg-gray-700" : ""}`}
                >
                  <List size={14} className="text-gray-600 dark:text-gray-400" />
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div className="flex gap-1">
            {[
              { key: "projects" as const, label: "项目", icon: Layers },
              { key: "workflows" as const, label: "工作流", icon: GitBranch },
              { key: "features" as const, label: "功能", icon: Zap },
              { key: "resolutions" as const, label: "决议队列", icon: Settings2 },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1 rounded px-3 py-1 text-xs font-medium ${
                  tab === t.key ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                <t.icon size={12} /> {t.label}
              </button>
            ))}
          </div>
          {tab === "projects" && <StatsBar tasks={tasks} loading={loading} stats={stats} />}
        </div>

        {/* Priority filter — projects only */}
        {tab === "projects" && (
          <div className="mt-2 flex items-center gap-1">
            <span className="text-xs text-gray-400">筛选:</span>
            {(["all", "P0", "P1", "P2", "P3"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setFilterPriority(p)}
                className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                  filterPriority === p
                    ? PRIORITY_COLORS[p as Priority] || "bg-gray-200 text-gray-800"
                    : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                {p === "all" ? "全部" : p}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mx-4 mt-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={14} />
          {error}
          <button onClick={fetchTasks} className="ml-auto text-blue-600 hover:underline">
            重试
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === "projects" && (
          <div className="h-full overflow-x-auto p-4">
            {loading && tasks.length === 0 ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 size={32} className="animate-spin text-gray-400" />
              </div>
            ) : view === "kanban" ? (
              <div className="flex gap-4" style={{ minWidth: columns.length * 280 }}>
                {columns.map((status) => (
                  <KanbanColumn
                    key={status}
                    status={status}
                    tasks={filtered.filter((t) => t.status === status)}
                    onStatusChange={handleStatusChange}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {filtered.map((task) => {
                  const cfg = STATUS_CONFIG[task.status];
                  const CfgIcon = cfg.icon;
                  return (
                    <div
                      key={task.id}
                      className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
                    >
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${PRIORITY_COLORS[task.priority]}`}>{task.priority}</span>
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200">{task.title}</h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{task.description}</p>
                      </div>
                      <span className="flex items-center gap-0.5 text-xs">
                        <CfgIcon size={12} className={cfg.color} />
                        <span className="text-gray-500 dark:text-gray-400">{cfg.label}</span>
                      </span>
                      {task.ownerCat && <span className="text-xs text-purple-600 dark:text-purple-400">@{task.ownerCat}</span>}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
        {tab === "workflows" && <WorkflowTab />}
        {tab === "features" && <FeaturesTab tasks={tasks} />}
        {tab === "resolutions" && <ResolutionsTab tasks={tasks} onStatusChange={handleStatusChange} />}
      </div>

      {/* Create Task Modal */}
      <CreateTaskModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateTask}
      />
    </div>
  );
}
