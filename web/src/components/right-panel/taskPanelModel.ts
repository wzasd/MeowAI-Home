import type { Cat } from "../../stores/catStore";
import type { TaskItem } from "./TaskPanel";

export interface TaskBoardCatSection {
  id: string;
  name: string;
  modelLabel: string | null;
  color: string | null;
  tasks: TaskItem[];
  counts: {
    todo: number;
    doing: number;
    blocked: number;
    done: number;
  };
}

export interface TaskBoardModel {
  total: number;
  sections: TaskBoardCatSection[];
}

function normalizeOwner(value?: string) {
  return value?.trim().replace(/^@/, "").toLowerCase() ?? "";
}

function matchesCat(task: TaskItem, cat: Cat) {
  const owner = normalizeOwner(task.ownerCat);
  if (!owner) return false;
  return [cat.id, cat.name, cat.displayName].some((value) => normalizeOwner(value) === owner);
}

function countStatuses(tasks: TaskItem[]) {
  return {
    todo: tasks.filter((task) => task.status === "todo").length,
    doing: tasks.filter((task) => task.status === "doing").length,
    blocked: tasks.filter((task) => task.status === "blocked").length,
    done: tasks.filter((task) => task.status === "done").length,
  };
}

function sectionRank(section: TaskBoardCatSection) {
  if (section.counts.doing > 0) return 4;
  if (section.counts.blocked > 0) return 3;
  if (section.counts.todo > 0) return 2;
  if (section.counts.done > 0) return 1;
  return 0;
}

export function buildTaskBoardModel(tasks: TaskItem[], cats: Cat[]): TaskBoardModel {
  const sections: TaskBoardCatSection[] = cats
    .filter((cat) => cat.isAvailable)
    .map((cat) => {
      const ownedTasks = tasks.filter((task) => matchesCat(task, cat));
      return {
        id: cat.id,
        name: cat.displayName || cat.name,
        modelLabel: cat.defaultModel || null,
        color: cat.colorPrimary || null,
        tasks: ownedTasks,
        counts: countStatuses(ownedTasks),
      };
    })
    .filter((section) => section.tasks.length > 0);

  const unassignedTasks = tasks.filter((task) => !normalizeOwner(task.ownerCat));
  if (unassignedTasks.length > 0) {
    sections.push({
      id: "unassigned",
      name: "未指派",
      modelLabel: null,
      color: null,
      tasks: unassignedTasks,
      counts: countStatuses(unassignedTasks),
    });
  }

  sections.sort((left, right) => {
    const diff = sectionRank(right) - sectionRank(left);
    if (diff !== 0) return diff;
    return right.tasks.length - left.tasks.length || left.name.localeCompare(right.name);
  });

  return {
    total: tasks.length,
    sections,
  };
}
