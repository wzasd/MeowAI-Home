/** Mission Hub — task board with backlog, features, and dependency tracking. */

import { useState } from "react";
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
} from "lucide-react";

// === Types ===

type TaskStatus = "backlog" | "todo" | "doing" | "blocked" | "done";
type Priority = "P0" | "P1" | "P2" | "P3";

interface MissionTask {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: Priority;
  ownerCat?: string;
  tags: string[];
  createdAt: string;
  dueDate?: string;
  progress?: number;
}

// === Mock Data ===

const MOCK_TASKS: MissionTask[] = [
  { id: "m1", title: "实现消息编辑功能", description: "支持用户编辑已发送的消息", status: "doing", priority: "P0", ownerCat: "orange", tags: ["聊天", "核心"], createdAt: "2026-04-10", progress: 60 },
  { id: "m2", title: "添加 Signal 收件箱页面", description: "展示聚合文章，支持学习模式", status: "done", priority: "P1", ownerCat: "patch", tags: ["Signal"], createdAt: "2026-04-09", progress: 100 },
  { id: "m3", title: "富文本块组件", description: "Card, Diff, Checklist, Media blocks", status: "done", priority: "P1", ownerCat: "inky", tags: ["UI", "聊天"], createdAt: "2026-04-09", progress: 100 },
  { id: "m4", title: "右侧面板开发", description: "Token统计、Session链、任务面板、队列管理", status: "doing", priority: "P0", ownerCat: "inky", tags: ["UI", "面板"], createdAt: "2026-04-10", progress: 40 },
  { id: "m5", title: "Workspace IDE 面板", description: "文件树 + 代码查看器 + 终端", status: "backlog", priority: "P2", tags: ["Workspace", "IDE"], createdAt: "2026-04-11" },
  { id: "m6", title: "Split Pane 多线程视图", description: "2x2 分屏同时查看多个线程", status: "backlog", priority: "P2", tags: ["聊天", "UI"], createdAt: "2026-04-11" },
  { id: "m7", title: "语音输入输出", description: "Whisper API 集成 + TTS 流式播放", status: "backlog", priority: "P3", tags: ["语音"], createdAt: "2026-04-11" },
  { id: "m8", title: "消息分支功能", description: "从任意消息分支出新线程", status: "todo", priority: "P1", ownerCat: "orange", tags: ["聊天", "线程"], createdAt: "2026-04-10" },
  { id: "m9", title: "历史搜索模态框", description: "全文搜索历史对话", status: "todo", priority: "P1", tags: ["搜索"], createdAt: "2026-04-10" },
  { id: "m10", title: "依赖图可视化", description: "DAGre + React Flow 任务依赖关系图", status: "blocked", priority: "P2", tags: ["Mission", "图表"], createdAt: "2026-04-10", dueDate: "2026-04-15" },
];

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

// === Sub-components ===

function TaskCard({ task }: { task: MissionTask }) {
  const cfg = STATUS_CONFIG[task.status];
  const StatusIcon = cfg.icon;
  void StatusIcon; // suppress unused variable warning
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
      </div>
    </div>
  );
}

function KanbanColumn({ status, tasks }: { status: TaskStatus; tasks: MissionTask[] }) {
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
          <TaskCard key={task.id} task={task} />
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

function StatsBar({ tasks }: { tasks: MissionTask[] }) {
  const done = tasks.filter((t) => t.status === "done").length;
  const total = tasks.length;
  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
        <Target size={14} /> {total} 任务
      </div>
      <div className="flex items-center gap-1 text-xs text-green-600">
        <CheckCircle2 size={14} /> {done} 完成
      </div>
      <div className="flex items-center gap-1 text-xs text-amber-600">
        <Clock size={14} /> {tasks.filter((t) => t.status === "doing").length} 进行中
      </div>
      <div className="flex items-center gap-1 text-xs text-red-600">
        <AlertTriangle size={14} /> {tasks.filter((t) => t.status === "blocked").length} 阻塞
      </div>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div className="h-full rounded-full bg-green-500" style={{ width: `${(done / total) * 100}%` }} />
      </div>
    </div>
  );
}

// === Main Component ===

export function MissionHubPage() {
  const [tasks] = useState<MissionTask[]>(MOCK_TASKS);
  const [view, setView] = useState<"kanban" | "list">("kanban");
  const [filterPriority, setFilterPriority] = useState<Priority | "all">("all");
  const [tab, setTab] = useState<"board" | "features" | "risks">("board");

  const filtered = filterPriority === "all" ? tasks : tasks.filter((t) => t.priority === filterPriority);

  const columns: TaskStatus[] = ["backlog", "todo", "doing", "blocked", "done"];

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Mission Hub</h2>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700">
              <Plus size={12} /> 新任务
            </button>
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
          </div>
        </div>

        <div className="mt-2 flex items-center justify-between">
          <div className="flex gap-1">
            {(["board", "features", "risks"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-xs font-medium ${
                  tab === t ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
              >
                {t === "board" ? "看板" : t === "features" ? "功能" : "风险"}
              </button>
            ))}
          </div>
          <StatsBar tasks={tasks} />
        </div>

        {/* Priority filter */}
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
      </div>

      {/* Content */}
      <div className="flex-1 overflow-x-auto p-4">
        {tab === "board" && view === "kanban" && (
          <div className="flex gap-4" style={{ minWidth: columns.length * 280 }}>
            {columns.map((status) => (
              <KanbanColumn key={status} status={status} tasks={filtered.filter((t) => t.status === status)} />
            ))}
          </div>
        )}
        {tab === "board" && view === "list" && (
          <div className="space-y-2">
            {filtered.map((task) => (
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
                  {(() => { const cfg = STATUS_CONFIG[task.status]; const CfgIcon = cfg.icon; return <CfgIcon size={12} className={cfg.color} />; })()}
                  <span className="text-gray-500 dark:text-gray-400">{STATUS_CONFIG[task.status].label}</span>
                </span>
                {task.ownerCat && <span className="text-xs text-purple-600 dark:text-purple-400">@{task.ownerCat}</span>}
              </div>
            ))}
          </div>
        )}
        {tab === "features" && (
          <div className="flex h-full items-center justify-center text-gray-400">
            <div className="text-center">
              <BarChart3 size={32} className="mx-auto mb-2" />
              <p>功能进度追踪面板</p>
              <p className="text-sm">按功能模块追踪整体完成度</p>
            </div>
          </div>
        )}
        {tab === "risks" && (
          <div className="flex h-full items-center justify-center text-gray-400">
            <div className="text-center">
              <AlertTriangle size={32} className="mx-auto mb-2" />
              <p>风险评估面板</p>
              <p className="text-sm">展示阻塞项和延期风险</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
