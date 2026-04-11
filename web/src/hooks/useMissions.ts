/** Missions hook — fetch and manage mission tasks. */

import { useState, useEffect, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export type TaskStatus = "backlog" | "todo" | "doing" | "blocked" | "done";
export type Priority = "P0" | "P1" | "P2" | "P3";

export interface MissionTask {
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

export interface TaskStats {
  total: number;
  backlog: number;
  todo: number;
  doing: number;
  blocked: number;
  done: number;
  by_priority: Record<string, number>;
}

interface UseMissionsReturn {
  tasks: MissionTask[];
  loading: boolean;
  error: string | null;
  filterPriority: Priority | "all";
  setFilterPriority: (priority: Priority | "all") => void;
  fetchTasks: () => Promise<void>;
  createTask: (task: Omit<MissionTask, "id" | "createdAt">) => Promise<MissionTask | null>;
  updateTask: (taskId: string, updates: Partial<Omit<MissionTask, "id">>) => Promise<boolean>;
  updateTaskStatus: (taskId: string, status: TaskStatus) => Promise<boolean>;
  deleteTask: (taskId: string) => Promise<boolean>;
  stats: TaskStats | null;
  fetchStats: () => Promise<void>;
}

export function useMissions(): UseMissionsReturn {
  const [tasks, setTasks] = useState<MissionTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterPriority, setFilterPriority] = useState<Priority | "all">("all");
  const [stats, setStats] = useState<TaskStats | null>(null);

  // Fetch tasks
  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterPriority !== "all") {
        params.set("priority", filterPriority);
      }

      const res = await fetch(`${API_BASE}/api/missions/tasks?${params}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch tasks: ${res.status}`);
      }
      const data = await res.json();
      setTasks(data.tasks ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [filterPriority]);

  // Create task
  const createTask = useCallback(async (task: Omit<MissionTask, "id" | "createdAt">): Promise<MissionTask | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/missions/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(task),
      });
      if (!res.ok) {
        throw new Error(`Failed to create task: ${res.status}`);
      }
      const newTask = await res.json();
      setTasks((prev) => [...prev, newTask]);
      return newTask;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
      return null;
    }
  }, []);

  // Update task
  const updateTask = useCallback(async (taskId: string, updates: Partial<Omit<MissionTask, "id">>): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/missions/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!res.ok) {
        return false;
      }
      const updatedTask = await res.json();
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updatedTask : t)));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Update task status
  const updateTaskStatus = useCallback(async (taskId: string, status: TaskStatus): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/missions/tasks/${taskId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) {
        return false;
      }
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status } : t))
      );
      return true;
    } catch {
      return false;
    }
  }, []);

  // Delete task
  const deleteTask = useCallback(async (taskId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/missions/tasks/${taskId}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        return false;
      }
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/missions/stats`);
      if (!res.ok) {
        throw new Error(`Failed to fetch stats: ${res.status}`);
      }
      const data = await res.json();
      setStats(data);
    } catch (err) {
      // Silently fail for stats
      console.error("Failed to fetch stats:", err);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchTasks();
    fetchStats();
  }, [fetchTasks, fetchStats]);

  return {
    tasks,
    loading,
    error,
    filterPriority,
    setFilterPriority,
    fetchTasks,
    createTask,
    updateTask,
    updateTaskStatus,
    deleteTask,
    stats,
    fetchStats,
  };
}
