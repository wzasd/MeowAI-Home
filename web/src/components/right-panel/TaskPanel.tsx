import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Circle } from "lucide-react";
import { useCatStore } from "../../stores/catStore";
import { buildTaskBoardModel } from "./taskPanelModel";
import { buildApiUrl } from "../../api/runtimeConfig";

export interface TaskItem {
  id: string;
  title: string;
  status: "todo" | "doing" | "blocked" | "done";
  ownerCat?: string;
  description?: string;
}

const STATUS_CONFIG = {
  todo: { icon: Circle, color: "text-[var(--text-faint)]", label: "待办" },
  doing: { icon: Circle, color: "text-amber-500", label: "进行中" },
  blocked: { icon: AlertTriangle, color: "text-red-500", label: "阻塞" },
  done: { icon: CheckCircle2, color: "text-green-500", label: "完成" },
};

export function TaskPanel({ threadId }: { threadId: string | null }) {
  const cats = useCatStore((state) => state.cats);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const url = threadId
        ? buildApiUrl(`/api/tasks/entries?threadId=${threadId}`)
        : buildApiUrl("/api/tasks/entries");
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const board = buildTaskBoardModel(tasks, cats);
  const doneCount = tasks.filter((task) => task.status === "done").length;

  if (loading) {
    return <div className="text-sm text-[var(--text-faint)]">加载中...</div>;
  }

  if (board.sections.length === 0) {
    return <div className="text-sm text-[var(--text-faint)]">暂无任务</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--text-faint)]">
          猫咪任务
        </h4>
        <span className="text-xs text-[var(--text-faint)]">
          {doneCount}/{tasks.length} 完成
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-[rgba(141,104,68,0.12)] dark:bg-white/10">
        <div
          className="h-full rounded-full bg-green-500 transition-all"
          style={{ width: `${tasks.length > 0 ? (doneCount / tasks.length) * 100 : 0}%` }}
        />
      </div>

      <div className="space-y-2">
        {board.sections.map((section) => (
          <section
            key={section.id}
            className="nest-card nest-r-md border-[var(--border-strong)]/45 border p-3"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: section.color || "#9ca3af" }}
                  />
                  <span className="truncate text-sm font-semibold text-[var(--text-strong)]">
                    {section.name}
                  </span>
                </div>
                <p className="mt-1 text-[10px] text-[var(--text-faint)]">
                  {section.modelLabel || "无模型信息"}
                </p>
              </div>
              <div className="text-right text-[10px] text-[var(--text-faint)]">
                <div>进行 {section.counts.doing}</div>
                <div>失败/阻塞 {section.counts.blocked}</div>
                <div>完成 {section.counts.done}</div>
              </div>
            </div>

            <div className="mt-2 flex flex-wrap gap-1.5 text-[10px] text-[var(--text-faint)]">
              <TaskCountChip label="待办" value={section.counts.todo} />
              <TaskCountChip label="进行中" value={section.counts.doing} />
              <TaskCountChip label="失败/阻塞" value={section.counts.blocked} />
              <TaskCountChip label="完成" value={section.counts.done} />
            </div>

            {section.tasks.length > 0 ? (
              <div className="mt-3 space-y-1.5">
                {section.tasks.map((task) => {
                  const cfg = STATUS_CONFIG[task.status];
                  const Icon = cfg.icon;
                  return (
                    <div key={task.id} className="nest-card nest-r-sm flex items-start gap-2 p-2">
                      <Icon size={14} className={`mt-0.5 shrink-0 ${cfg.color}`} />
                      <div className="min-w-0 flex-1">
                        <p
                          className={`text-xs ${
                            task.status === "done"
                              ? "text-[var(--text-faint)] line-through"
                              : "text-[var(--text-strong)]"
                          }`}
                        >
                          {task.title}
                        </p>
                        {task.description && (
                          <p className="text-[10px] text-[var(--text-faint)]">{task.description}</p>
                        )}
                        <p className="mt-0.5 text-[10px] text-[var(--text-faint)]">{cfg.label}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="mt-3 rounded-xl border border-dashed border-[var(--border)] px-3 py-2 text-[11px] text-[var(--text-faint)]">
                暂无任务
              </div>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function TaskCountChip({ label, value }: { label: string; value: number }) {
  return (
    <span className="rounded-full border border-[var(--border)] bg-white/45 px-2 py-0.5 dark:bg-white/5">
      {label} {value}
    </span>
  );
}
