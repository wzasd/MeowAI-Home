import type { MissionTask } from "../../api/client";
import type { Cat } from "../../stores/catStore";
import type { ThreadResponse } from "../../types";

export interface SidebarSummaryFact {
  label: string;
  value: string;
}

export interface SidebarTaskGroup {
  task: MissionTask;
  threads: ThreadResponse[];
  latestUpdatedAt: string | null;
}

export interface ThreadSidebarSummary {
  title: string;
  compactLine: string;
  supportLine: string;
  activeNestCount: number;
  freeNestCount: number;
  archivedNestCount: number;
  onDutyCatCount: number;
  activeTaskCount: number;
  blockedTaskCount: number;
  facts: SidebarSummaryFact[];
}

export interface ThreadSidebarModel {
  summary: ThreadSidebarSummary;
  taskGroups: SidebarTaskGroup[];
  freeThreads: ThreadResponse[];
  archivedThreads: ThreadResponse[];
  isEmpty: boolean;
  emptyMessage: string;
}

interface BuildThreadSidebarModelInput {
  search: string;
  threads: ThreadResponse[];
  cats: Cat[];
  tasks: MissionTask[];
}

const PRIORITY_RANK: Record<MissionTask["priority"], number> = {
  P0: 4,
  P1: 3,
  P2: 2,
  P3: 1,
};

const STATUS_RANK: Record<MissionTask["status"], number> = {
  blocked: 5,
  doing: 4,
  todo: 3,
  backlog: 2,
  done: 1,
};

function normalize(value?: string | null) {
  return value?.trim().toLowerCase() ?? "";
}

function parseTime(value?: string | null) {
  if (!value) return 0;
  const ts = Date.parse(value);
  return Number.isNaN(ts) ? 0 : ts;
}

function sortThreadsByUpdatedDesc(threads: ThreadResponse[]) {
  return [...threads].sort((left, right) => {
    return parseTime(right.updated_at) - parseTime(left.updated_at);
  });
}

function matchesSearch(thread: ThreadResponse, task: MissionTask | undefined, search: string) {
  if (!search) return true;

  const query = normalize(search);
  const haystack = [
    thread.name,
    thread.project_path,
    task?.title,
    task?.description,
    task?.ownerCat,
    task?.priority,
    task?.status,
  ]
    .filter(Boolean)
    .join(" ");

  return normalize(haystack).includes(query);
}

export function buildThreadSidebarModel({
  search,
  threads,
  cats,
  tasks,
}: BuildThreadSidebarModelInput): ThreadSidebarModel {
  const activeThreads = threads.filter((thread) => !thread.is_archived);
  const archivedThreads = threads.filter((thread) => thread.is_archived);
  const onDutyCatCount = cats.filter((cat) => cat.isAvailable).length;
  const activeTaskCount = tasks.filter((task) => task.status === "doing").length;
  const blockedTaskCount = tasks.filter((task) => task.status === "blocked").length;
  const archivedNestCount = archivedThreads.length;

  const taskByThreadId = new Map<string, MissionTask>();
  for (const task of tasks) {
    for (const threadId of task.thread_ids ?? []) {
      if (!taskByThreadId.has(threadId)) {
        taskByThreadId.set(threadId, task);
      }
    }
  }

  const filteredThreads = threads.filter((thread) =>
    matchesSearch(thread, taskByThreadId.get(thread.id), search)
  );

  const filteredActiveThreads = filteredThreads.filter((thread) => !thread.is_archived);
  const filteredArchivedThreads = sortThreadsByUpdatedDesc(
    filteredThreads.filter((thread) => thread.is_archived)
  );

  const taskGroups: SidebarTaskGroup[] = tasks
    .map((task) => {
      const groupThreads = sortThreadsByUpdatedDesc(
        filteredActiveThreads.filter((thread) => task.thread_ids?.includes(thread.id))
      );

      return {
        task,
        threads: groupThreads,
        latestUpdatedAt: groupThreads[0]?.updated_at ?? null,
      };
    })
    .filter((group) => group.threads.length > 0)
    .sort((left, right) => {
      const statusDiff = STATUS_RANK[right.task.status] - STATUS_RANK[left.task.status];
      if (statusDiff !== 0) return statusDiff;

      const priorityDiff = PRIORITY_RANK[right.task.priority] - PRIORITY_RANK[left.task.priority];
      if (priorityDiff !== 0) return priorityDiff;

      return parseTime(right.latestUpdatedAt) - parseTime(left.latestUpdatedAt);
    });

  const taskThreadIds = new Set(taskGroups.flatMap((group) => group.threads.map((thread) => thread.id)));
  const freeThreads = sortThreadsByUpdatedDesc(
    filteredActiveThreads.filter((thread) => !taskThreadIds.has(thread.id))
  );
  const activeFreeCount = activeThreads.filter((thread) => !taskByThreadId.has(thread.id)).length;

  const hasAnyThreads = threads.length > 0;
  const isEmpty =
    taskGroups.length === 0 && freeThreads.length === 0 && filteredArchivedThreads.length === 0;

  return {
    summary: {
      title: "流浪猫工作室",
      compactLine: `今晚有 ${activeThreads.length} 个在线猫窝，${onDutyCatCount} 只猫值班`,
      supportLine: `自由窝 ${activeFreeCount} · 任务 ${activeTaskCount} · 归档 ${archivedNestCount}`,
      activeNestCount: activeThreads.length,
      freeNestCount: activeFreeCount,
      archivedNestCount,
      onDutyCatCount,
      activeTaskCount,
      blockedTaskCount,
      facts: [
        { label: "在线猫窝", value: String(activeThreads.length) },
        { label: "自由猫窝", value: String(activeFreeCount) },
        { label: "值班猫咪", value: String(onDutyCatCount) },
        { label: "进行任务", value: String(activeTaskCount) },
      ],
    },
    taskGroups,
    freeThreads,
    archivedThreads: filteredArchivedThreads,
    isEmpty,
    emptyMessage: hasAnyThreads ? "没有匹配的猫窝" : "暂无猫窝，点击 + 创建",
  };
}
