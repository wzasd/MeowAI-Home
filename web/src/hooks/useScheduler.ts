"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export interface ScheduledTask {
  id: string;
  name: string;
  description: string;
  trigger: "interval" | "cron";
  schedule: string;
  enabled: boolean;
  status: string;
  last_run?: number;
  next_run?: number;
  run_count: number;
  error_count: number;
  last_error?: string;
  created_at: number;
  updated_at: number;
  actor_role: string;
  cost_tier: string;
  task_template: string;
  task_config?: Record<string, unknown>;
}

export interface SchedulerTemplate {
  id: string;
  name: string;
  description: string;
  actor_role: string;
  cost_tier: string;
  default_config: Record<string, unknown>;
}

export interface TaskLog {
  task_id: string;
  success: boolean;
  execution_time_ms: number;
  timestamp: number;
  error?: string;
  actor_id?: string;
}

interface UseSchedulerReturn {
  tasks: ScheduledTask[];
  templates: SchedulerTemplate[];
  loading: boolean;
  error: string | null;
  fetchTasks: () => Promise<void>;
  fetchTemplates: () => Promise<void>;
  createTask: (task: Omit<ScheduledTask, "id" | "created_at" | "updated_at" | "status" | "run_count" | "error_count">) => Promise<ScheduledTask | null>;
  updateTask: (taskId: string, updates: Partial<Omit<ScheduledTask, "id">>) => Promise<ScheduledTask | null>;
  enableTask: (taskId: string) => Promise<boolean>;
  disableTask: (taskId: string) => Promise<boolean>;
  triggerTask: (taskId: string) => Promise<boolean>;
  deleteTask: (taskId: string) => Promise<boolean>;
  getLogs: (taskId: string) => Promise<TaskLog[]>;
  pauseAll: () => Promise<boolean>;
  resumeAll: () => Promise<boolean>;
}

export function useScheduler(): UseSchedulerReturn {
  const [tasks, setTasks] = useState<ScheduledTask[]>([]);
  const [templates, setTemplates] = useState<SchedulerTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks`);
      if (!res.ok) throw new Error(`Failed to fetch tasks: ${res.status}`);
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/templates`);
      if (!res.ok) throw new Error(`Failed to fetch templates: ${res.status}`);
      const data = await res.json();
      setTemplates(data.templates || []);
    } catch (err) {
      console.error("Failed to fetch templates:", err);
    }
  }, []);

  const createTask = useCallback(async (task: Omit<ScheduledTask, "id" | "created_at" | "updated_at" | "status" | "run_count" | "error_count">) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(task),
      });
      if (!res.ok) throw new Error(`Failed to create task: ${res.status}`);
      const newTask = await res.json();
      setTasks((prev) => [...prev, newTask]);
      return newTask;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
      return null;
    }
  }, []);

  const updateTask = useCallback(async (taskId: string, updates: Partial<Omit<ScheduledTask, "id">>) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      if (!res.ok) throw new Error(`Failed to update task: ${res.status}`);
      const updated = await res.json();
      setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
      return updated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update task");
      return null;
    }
  }, []);

  const enableTask = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}/enable`, { method: "POST" });
      if (!res.ok) return false;
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, enabled: true, status: "pending" } : t)));
      return true;
    } catch {
      return false;
    }
  }, []);

  const disableTask = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}/disable`, { method: "POST" });
      if (!res.ok) return false;
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, enabled: false, status: "disabled" } : t)));
      return true;
    } catch {
      return false;
    }
  }, []);

  const triggerTask = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}/trigger`, { method: "POST" });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  const deleteTask = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}`, { method: "DELETE" });
      if (!res.ok) return false;
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
      return true;
    } catch {
      return false;
    }
  }, []);

  const getLogs = useCallback(async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/tasks/${taskId}/logs`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.logs || [];
    } catch {
      return [];
    }
  }, []);

  const pauseAll = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/governance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "pause_all" }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  const resumeAll = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/scheduler/governance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "resume_all" }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    fetchTasks();
    fetchTemplates();
  }, [fetchTasks, fetchTemplates]);

  return {
    tasks,
    templates,
    loading,
    error,
    fetchTasks,
    fetchTemplates,
    createTask,
    updateTask,
    enableTask,
    disableTask,
    triggerTask,
    deleteTask,
    getLogs,
    pauseAll,
    resumeAll,
  };
}
