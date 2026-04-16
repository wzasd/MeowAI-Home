/** Task Scheduler panel — manage scheduled tasks with templates and logs. */

import { useState, useMemo } from "react";
import {
  Play,
  Pause,
  Trash2,
  Plus,
  Clock,
  Calendar,
  Loader2,
  ChevronDown,
  ChevronUp,
  Zap,
  AlertCircle,
  CheckCircle2,
  X,
} from "lucide-react";
import { useScheduler, type ScheduledTask, type SchedulerTemplate } from "../../hooks/useScheduler";

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function TemplateBadge({ template }: { template: string }) {
  const colors: Record<string, string> = {
    reminder: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    "repo-activity": "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    "web-digest": "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${colors[template] || "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"}`}>
      {template}
    </span>
  );
}

function TaskRow({
  task,
  onToggle,
  onTrigger,
  onDelete,
  expanded,
  onToggleExpand,
  logs,
  logsLoading,
}: {
  task: ScheduledTask;
  onToggle: () => void;
  onTrigger: () => void;
  onDelete: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
  logs: { task_id: string; success: boolean; timestamp: number; error?: string }[];
  logsLoading: boolean;
}) {
  const statusColor =
    task.status === "running"
      ? "text-amber-500"
      : task.status === "error"
      ? "text-red-500"
      : task.status === "disabled"
      ? "text-gray-400"
      : "text-green-500";

  return (
    <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center gap-3 px-3 py-2">
        <button
          onClick={onToggle}
          className={`rounded p-1 ${task.enabled ? "text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20" : "text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"}`}
          title={task.enabled ? "禁用" : "启用"}
        >
          {task.enabled ? <CheckCircle2 size={16} /> : <Pause size={16} />}
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{task.name}</span>
            <TemplateBadge template={task.task_template} />
            <span className={`text-[10px] capitalize ${statusColor}`}>{task.status}</span>
          </div>
          <div className="flex gap-3 text-[10px] text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-0.5">
              <Clock size={10} />
              {task.trigger === "interval" ? `每 ${task.schedule} 秒` : task.schedule}
            </span>
            <span>运行 {task.run_count} 次</span>
            {task.error_count > 0 && <span className="text-red-500">失败 {task.error_count} 次</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onTrigger}
            className="rounded p-1 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20"
            title="立即执行"
          >
            <Play size={14} />
          </button>
          <button
            onClick={onToggleExpand}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            title="查看日志"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          <button
            onClick={onDelete}
            className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
            title="删除"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 px-3 py-2 dark:border-gray-700">
          <div className="mb-2 text-[10px] text-gray-500">
            <div>上次运行: {formatTime(task.last_run)}</div>
            <div>下次运行: {formatTime(task.next_run)}</div>
            {task.last_error && <div className="mt-1 text-red-500">最后错误: {task.last_error}</div>}
          </div>

          <div className="text-xs font-medium text-gray-700 dark:text-gray-300">执行日志</div>
          {logsLoading ? (
            <div className="py-2">
              <Loader2 size={14} className="animate-spin text-gray-400" />
            </div>
          ) : logs.length === 0 ? (
            <div className="py-2 text-[10px] text-gray-400">暂无日志</div>
          ) : (
            <div className="mt-1 space-y-1">
              {logs.map((log, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span className={log.success ? "text-green-500" : "text-red-500"}>
                    {log.success ? "成功" : "失败"}
                  </span>
                  <span className="text-gray-400">{formatTime(log.timestamp)}</span>
                  {log.error && <span className="text-red-500 truncate max-w-[200px]">{log.error}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CreateTaskModal({
  isOpen,
  onClose,
  templates,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  templates: SchedulerTemplate[];
  onCreate: (task: any) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [trigger, setTrigger] = useState<"interval" | "cron">("interval");
  const [schedule, setSchedule] = useState("3600");
  const [templateId, setTemplateId] = useState("default");
  const [configJson, setConfigJson] = useState("{}");

  if (!isOpen) return null;

  const selectedTemplate = templates.find((t) => t.id === templateId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let taskConfig = {};
    try {
      taskConfig = JSON.parse(configJson);
    } catch {
      // ignore
    }
    onCreate({
      name: name.trim() || "未命名任务",
      description,
      trigger,
      schedule,
      enabled: true,
      task_template: templateId,
      actor_role: selectedTemplate?.actor_role || "default",
      cost_tier: selectedTemplate?.cost_tier || "standard",
      task_config: taskConfig,
    });
    setName("");
    setDescription("");
    setSchedule("3600");
    setConfigJson("{}");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-5 dark:bg-gray-800">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">新建定时任务</h3>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="任务名称"
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">描述</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="任务描述"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">触发器</label>
              <select
                value={trigger}
                onChange={(e) => setTrigger(e.target.value as "interval" | "cron")}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="interval">间隔</option>
                <option value="cron">Cron</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                {trigger === "interval" ? "间隔 (秒)" : "Cron 表达式"}
              </label>
              <input
                type="text"
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder={trigger === "interval" ? "3600" : "0 9 * * *"}
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">模板</label>
            <select
              value={templateId}
              onChange={(e) => {
                setTemplateId(e.target.value);
                const tmpl = templates.find((t) => t.id === e.target.value);
                if (tmpl) {
                  setConfigJson(JSON.stringify(tmpl.default_config || {}, null, 2));
                }
              }}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="default">默认</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">配置 (JSON)</label>
            <textarea
              value={configJson}
              onChange={(e) => setConfigJson(e.target.value)}
              className="h-20 w-full rounded border border-gray-300 px-2 py-1.5 text-xs font-mono dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder='{"key":"value"}'
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded bg-gray-200 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              取消
            </button>
            <button
              type="submit"
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function TaskScheduler() {
  const {
    tasks,
    templates,
    loading,
    error,
    fetchTasks,
    createTask,
    enableTask,
    disableTask,
    triggerTask,
    deleteTask,
    getLogs,
    pauseAll,
    resumeAll,
  } = useScheduler();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [logsMap, setLogsMap] = useState<Record<string, any[]>>({});
  const [logsLoadingMap, setLogsLoadingMap] = useState<Record<string, boolean>>({});

  const enabledCount = useMemo(() => tasks.filter((t) => t.enabled).length, [tasks]);

  const handleToggleExpand = async (taskId: string) => {
    if (expandedTaskId === taskId) {
      setExpandedTaskId(null);
      return;
    }
    setExpandedTaskId(taskId);
    setLogsLoadingMap((prev) => ({ ...prev, [taskId]: true }));
    const logs = await getLogs(taskId);
    setLogsMap((prev) => ({ ...prev, [taskId]: logs }));
    setLogsLoadingMap((prev) => ({ ...prev, [taskId]: false }));
  };

  const handleCreate = async (taskData: any) => {
    await createTask(taskData);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          管理定时任务与调度模板
          <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {enabledCount} / {tasks.length} 启用
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              await pauseAll();
              await fetchTasks();
            }}
            className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400"
          >
            全局暂停
          </button>
          <button
            onClick={async () => {
              await resumeAll();
              await fetchTasks();
            }}
            className="rounded bg-green-100 px-2 py-1 text-xs text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400"
          >
            全局恢复
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700"
          >
            <Plus size={12} /> 新建任务
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={12} />
          {error}
        </div>
      )}

      {/* Templates */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">快速模板</h4>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-center gap-1.5 text-sm font-medium text-gray-800 dark:text-gray-200">
                <Zap size={12} className="text-blue-500" />
                {t.name}
              </div>
              <p className="mt-1 text-[10px] text-gray-500 dark:text-gray-400">{t.description}</p>
              <button
                onClick={() => {
                  setIsCreateOpen(true);
                }}
                className="mt-2 text-[10px] text-blue-600 hover:underline dark:text-blue-400"
              >
                使用此模板
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Task list */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">任务列表</h4>
        {loading && tasks.length === 0 ? (
          <div className="py-8 text-center">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400 dark:border-gray-700">
            暂无定时任务
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map((task) => (
              <TaskRow
                key={task.id}
                task={task}
                onToggle={async () => {
                  if (task.enabled) {
                    await disableTask(task.id);
                  } else {
                    await enableTask(task.id);
                  }
                  await fetchTasks();
                }}
                onTrigger={async () => {
                  await triggerTask(task.id);
                  await fetchTasks();
                }}
                onDelete={async () => {
                  await deleteTask(task.id);
                }}
                expanded={expandedTaskId === task.id}
                onToggleExpand={() => handleToggleExpand(task.id)}
                logs={logsMap[task.id] || []}
                logsLoading={logsLoadingMap[task.id] || false}
              />
            ))}
          </div>
        )}
      </div>

      <CreateTaskModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        templates={templates}
        onCreate={handleCreate}
      />
    </div>
  );
}
