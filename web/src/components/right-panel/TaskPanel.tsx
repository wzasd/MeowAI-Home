import { useState, useEffect } from "react";
import { CheckCircle2, Circle, AlertTriangle } from "lucide-react";

export interface TaskItem {
  id: string;
  title: string;
  status: "todo" | "doing" | "blocked" | "done";
  ownerCat?: string;
  description?: string;
}

const STATUS_CONFIG = {
  todo: { icon: Circle, color: "text-gray-400", label: "待办" },
  doing: { icon: Circle, color: "text-blue-500", label: "进行中" },
  blocked: { icon: AlertTriangle, color: "text-amber-500", label: "阻塞" },
  done: { icon: CheckCircle2, color: "text-green-500", label: "完成" },
};

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function TaskPanel({ threadId }: { threadId: string | null }) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const url = threadId
        ? `${API_BASE}/api/tasks/entries?threadId=${threadId}`
        : `${API_BASE}/api/tasks/entries`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [threadId]);

  const groups = {
    doing: tasks.filter((t) => t.status === "doing"),
    todo: tasks.filter((t) => t.status === "todo"),
    blocked: tasks.filter((t) => t.status === "blocked"),
    done: tasks.filter((t) => t.status === "done"),
  };

  if (loading) {
    return <div className="text-sm text-gray-400">加载中...</div>;
  }

  if (tasks.length === 0) {
    return <div className="text-sm text-gray-400">暂无任务</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">任务进度</h4>
        <span className="text-xs text-gray-400">
          {groups.done.length}/{tasks.length} 完成
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className="h-full rounded-full bg-green-500 transition-all"
          style={{ width: `${tasks.length > 0 ? (groups.done.length / tasks.length) * 100 : 0}%` }}
        />
      </div>

      {(Object.entries(groups) as [keyof typeof groups, TaskItem[]][]).map(([status, items]) => {
        if (items.length === 0) return null;
        const cfg = STATUS_CONFIG[status];
        const Icon = cfg.icon;
        return (
          <div key={status}>
            <div className="mb-1 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Icon size={12} className={cfg.color} />
              <span>{cfg.label} ({items.length})</span>
            </div>
            <div className="space-y-1 pl-4">
              {items.map((task) => (
                <div
                  key={task.id}
                  className="flex items-start gap-2 rounded border border-gray-100 bg-gray-50 p-2 dark:border-gray-700 dark:bg-gray-800/50"
                >
                  <Icon size={14} className={`mt-0.5 shrink-0 ${cfg.color}`} />
                  <div className="min-w-0 flex-1">
                    <p className={`text-xs ${task.status === "done" ? "text-gray-400 line-through" : "text-gray-700 dark:text-gray-300"}`}>
                      {task.title}
                    </p>
                    {task.description && <p className="text-[10px] text-gray-400">{task.description}</p>}
                    {task.ownerCat && (
                      <span className="mt-0.5 inline-block rounded bg-gray-200 px-1 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                        {task.ownerCat}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
