/** Missions hook — fetch and manage mission tasks. */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { MissionTask, TaskStats, TaskStatus, Priority } from "../api/client";

export type { TaskStatus, Priority, MissionTask, TaskStats } from "../api/client";

interface UseMissionsReturn {
  tasks: MissionTask[];
  loading: boolean;
  error: string | null;
  filterPriority: Priority | "all";
  setFilterPriority: (priority: Priority | "all") => void;
  fetchTasks: () => Promise<void>;
  getTask: (taskId: string) => Promise<MissionTask | null>;
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
      const data = await api.missions.listTasks(filterPriority !== "all" ? filterPriority : undefined);
      setTasks(data.tasks ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, [filterPriority]);

  // Get single task
  const getTask = useCallback(async (taskId: string): Promise<MissionTask | null> => {
    try {
      return await api.missions.getTask(taskId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch task");
      return null;
    }
  }, []);

  // Create task
  const createTask = useCallback(async (task: Omit<MissionTask, "id" | "createdAt">): Promise<MissionTask | null> => {
    try {
      const newTask = await api.missions.createTask(task);
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
      const updatedTask = await api.missions.updateTask(taskId, updates);
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updatedTask : t)));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Update task status
  const updateTaskStatus = useCallback(async (taskId: string, status: TaskStatus): Promise<boolean> => {
    try {
      await api.missions.updateTaskStatus(taskId, status);
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
      await api.missions.deleteTask(taskId);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      return true;
    } catch {
      return false;
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const data = await api.missions.getStats();
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
    getTask,
    createTask,
    updateTask,
    updateTaskStatus,
    deleteTask,
    stats,
    fetchStats,
  };
}
