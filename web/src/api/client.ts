/** REST API client for MeowAI Home backend. */

import type {
  ThreadDetailResponse,
  ThreadListResponse,
  MessageListResponse,
  MessageResponse,
  CatListResponse,
  CatDetailResponse,
  ConnectorListResponse,
  ConnectorBindingStatus,
  ConnectorQrResponse,
  EnvVarListResponse,
  AccountListResponse,
  AccountResponse,
  TestKeyResponse,
  CapabilityBoardResponse,
  CapabilityPatchRequest,
  Attachment,
  AuthUserResponse,
  TokenResponse,
} from "../types";

// Mission types
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

// Workspace types
export interface WorktreeEntry {
  id: string;
  root: string;
  branch: string;
  head: string;
}

export interface TreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeNode[];
}

export interface FileData {
  path: string;
  content: string;
  sha256: string;
  size: number;
  mime: string;
  truncated: boolean;
  binary?: boolean;
}

export interface SearchResult {
  path: string;
  line: number;
  content: string;
  context_before?: string;
  context_after?: string;
}

export interface GitStatusItem {
  status: string;
  path: string;
  original_path?: string;
}

export interface GitStatus {
  branch: string;
  ahead: number;
  behind: number;
  clean: boolean;
  files: GitStatusItem[];
}

export interface TerminalResult {
  stdout: string;
  stderr: string;
  returncode: number;
}

// Workflow types
export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
}

export interface ActiveWorkflow {
  id: string;
  name?: string;
  status?: string;
}

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("meowai:token");
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();
  const isFormData = options?.body instanceof FormData;

  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (options?.headers) {
    const extra = options.headers as Record<string, string>;
    Object.entries(extra).forEach(([k, v]) => {
      headers[k] = v;
    });
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  threads: {
    list: () => request<ThreadListResponse>("/api/threads"),

    get: (id: string) => request<ThreadDetailResponse>(`/api/threads/${id}`),

    create: (name: string, catId?: string, projectPath?: string) =>
      request<ThreadDetailResponse>("/api/threads", {
        method: "POST",
        body: JSON.stringify({ name, cat_id: catId, project_path: projectPath }),
      }),

    rename: (id: string, name: string) =>
      request<ThreadDetailResponse>(`/api/threads/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),

    switchCat: (id: string, catId: string) =>
      request<ThreadDetailResponse>(`/api/threads/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ current_cat_id: catId }),
      }),

    delete: (id: string) => request<{ status: string }>(`/api/threads/${id}`, { method: "DELETE" }),

    archive: (id: string) =>
      request<ThreadDetailResponse>(`/api/threads/${id}/archive`, {
        method: "POST",
      }),

    sessions: (id: string) =>
      request<Array<{
        session_id: string;
        cat_id: string;
        cat_name: string;
        status: "active" | "sealed";
        created_at: number;
        consecutive_restore_failures: number;
      }>>(`/api/threads/${id}/sessions`),
  },

  sessions: {
    get: (sessionId: string) =>
      request<{
        session_id: string;
        cat_id: string;
        cat_name: string;
        status: "active" | "sealed";
        created_at: number;
        consecutive_restore_failures: number;
      }>(`/api/sessions/${sessionId}`),
    seal: (sessionId: string) =>
      request<{ success: boolean; session_id: string; status: string; message: string }>(
        `/api/sessions/${sessionId}/seal`,
        { method: "POST" }
      ),
    unseal: (sessionId: string) =>
      request<{ success: boolean; session_id: string; status: string; message: string }>(
        `/api/sessions/${sessionId}/unseal`,
        { method: "POST" }
      ),
  },

  messages: {
    list: (threadId: string, limit = 50, offset = 0) =>
      request<MessageListResponse>(
        `/api/threads/${threadId}/messages?limit=${limit}&offset=${offset}`
      ),

    edit: (threadId: string, messageId: string, content: string) =>
      request<MessageResponse>(`/api/threads/${threadId}/messages/${messageId}`, {
        method: "PATCH",
        body: JSON.stringify({ content }),
      }),

    delete: (threadId: string, messageId: string) =>
      request<{ success: boolean }>(`/api/threads/${threadId}/messages/${messageId}`, {
        method: "DELETE",
      }),

    reply: (threadId: string, content: string, replyToId: string) =>
      request<MessageResponse>(`/api/threads/${threadId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content, reply_to: replyToId }),
      }),

    branch: (threadId: string, messageId: string) =>
      request<{ thread_id: string }>(`/api/threads/${threadId}/messages/${messageId}/branch`, {
        method: "POST",
      }),

    search: (query: string, limit = 20) =>
      request<{ results: Array<{ threadId: string; messageId: string; content: string; timestamp: string }> }>(
        `/api/messages/search?q=${encodeURIComponent(query)}&limit=${limit}`
      ),
  },

  uploads: {
    upload: (threadId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<Attachment>(`/api/threads/${threadId}/uploads`, {
        method: "POST",
        body: formData,
      });
    },
  },

  cats: {
    list: () => request<CatListResponse>("/api/cats"),
    get: (id: string) => request<CatDetailResponse>(`/api/cats/${id}`),
    invoke: (id: string) =>
      request<{ success: boolean; message: string }>(`/api/cats/${id}/invoke`, {
        method: "POST",
      }),
    getBudget: (id: string) =>
      request<{ catId: string; budget: Record<string, number> }>(`/api/cats/${id}/budget`),
    create: (data: {
      id: string;
      name: string;
      displayName?: string;
      provider: string;
      defaultModel?: string;
      personality?: string;
      mentionPatterns?: string[];
    }) =>
      request<CatDetailResponse>("/api/cats", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: {
      name?: string;
      displayName?: string;
      provider?: string;
      defaultModel?: string;
      personality?: string;
      mentionPatterns?: string[];
      capabilities?: string[];
      permissions?: string[];
    }) =>
      request<CatDetailResponse>(`/api/cats/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<{ success: boolean; deleted: string }>(`/api/cats/${id}`, {
        method: "DELETE",
      }),
  },

  connectors: {
    list: () => request<ConnectorListResponse>("/api/connectors"),
    test: (name: string, config: Record<string, string>) =>
      request<{ success: boolean; message: string }>(`/api/connectors/${name}/test`, {
        method: "POST",
        body: JSON.stringify({ config }),
      }),
    getBindingStatus: (name: string) =>
      request<ConnectorBindingStatus>(`/api/connectors/${name}/binding-status`),
    getQr: (name: string) =>
      request<ConnectorQrResponse>(`/api/connectors/${name}/qr`),
    bindCallback: (name: string, token: string, userName: string) =>
      request<{ success: boolean; name: string; bound: boolean; bound_user: string }>(
        `/api/connectors/${name}/bind-callback`,
        {
          method: "POST",
          body: JSON.stringify({ token, user_name: userName }),
        }
      ),
    unbind: (name: string) =>
      request<{ success: boolean; message: string }>(`/api/connectors/${name}/unbind`, {
        method: "POST",
      }),
    enable: (name: string) =>
      request<{ success: boolean; message: string }>(`/api/connectors/${name}/enable`, {
        method: "POST",
      }),
    disable: (name: string) =>
      request<{ success: boolean; message: string }>(`/api/connectors/${name}/disable`, {
        method: "POST",
      }),
  },

  config: {
    listEnvVars: () => request<EnvVarListResponse>("/api/config/env"),
    updateEnvVar: (name: string, value: string) =>
      request<{ success: boolean }>(`/api/config/env/${name}`, {
        method: "POST",
        body: JSON.stringify({ value }),
      }),
    accounts: {
      list: () => request<AccountListResponse>("/api/config/accounts"),
      create: (data: {
        id: string; displayName: string; protocol: string; authType: string;
        baseUrl?: string; models?: string[]; apiKey?: string;
      }) => request<AccountResponse>("/api/config/accounts", {
        method: "POST", body: JSON.stringify(data),
      }),
      get: (id: string) => request<AccountResponse>(`/api/config/accounts/${id}`),
      update: (id: string, data: Record<string, unknown>) =>
        request<AccountResponse>(`/api/config/accounts/${id}`, {
          method: "PATCH", body: JSON.stringify(data),
        }),
      delete: (id: string) => request<{ success: boolean }>(`/api/config/accounts/${id}`, {
        method: "DELETE",
      }),
      testKey: (accountId: string, apiKey: string, protocol: string, baseUrl?: string) =>
        request<TestKeyResponse>(`/api/config/accounts/${accountId}/test-key`, {
          method: "POST", body: JSON.stringify({ apiKey, protocol, baseUrl }),
        }),
      bindCat: (catId: string, accountRef: string) =>
        request<{ success: boolean }>("/api/config/accounts/bind-cat", {
          method: "PATCH", body: JSON.stringify({ catId, accountRef }),
        }),
    },
  },

  metrics: {
    cat: (catId: string, days?: number) =>
      request<{ cat_id: string; days: number; data: any[] }>(`/api/metrics/cats?cat_id=${catId}&days=${days ?? 7}`),
    leaderboard: (days?: number) =>
      request<{ days: number; leaderboard: any[] }>(`/api/metrics/leaderboard?days=${days ?? 7}`),
  },

  governance: {
    listProjects: () => request<{ projects: any[] }>("/api/governance/projects"),
    addProject: (data: { project_path: string; status?: string; version?: string; findings?: any[]; confirmed?: boolean }) =>
      request<{ success: boolean }>("/api/governance/projects", { method: "POST", body: JSON.stringify(data) }),
    deleteProject: (projectPath: string) =>
      request<{ success: boolean }>(`/api/governance/projects/${encodeURIComponent(projectPath)}`, { method: "DELETE" }),
    confirmProject: (projectPath: string) =>
      request<{ success: boolean }>("/api/governance/confirm", { method: "POST", body: JSON.stringify({ project_path: projectPath }) }),
    syncProject: (projectPath: string) =>
      request<{ success: boolean }>("/api/governance/sync", { method: "POST", body: JSON.stringify({ project_path: projectPath }) }),
  },

  capabilities: {
    get: (projectPath: string, probe?: boolean) =>
      request<CapabilityBoardResponse>(`/api/capabilities?project_path=${encodeURIComponent(projectPath)}${probe ? "&probe=true" : ""}`),
    patch: (data: CapabilityPatchRequest) =>
      request<{ ok: boolean; capability: any }>("/api/capabilities", { method: "PATCH", body: JSON.stringify(data) }),
  },

  auth: {
    login: (username: string, password: string) =>
      request<TokenResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    register: (username: string, password: string, role = "member") =>
      request<AuthUserResponse>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password, role }),
      }),
    me: () => request<AuthUserResponse>("/api/auth/me"),
  },

  missions: {
    listTasks: (priority?: Priority | "all") =>
      request<{ tasks: MissionTask[]; total: number }>(
        `/api/missions/tasks${priority && priority !== "all" ? `?priority=${priority}` : ""}`
      ),
    createTask: (task: Omit<MissionTask, "id" | "createdAt">) =>
      request<MissionTask>("/api/missions/tasks", { method: "POST", body: JSON.stringify(task) }),
    updateTask: (taskId: string, updates: Partial<Omit<MissionTask, "id">>) =>
      request<MissionTask>(`/api/missions/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(updates) }),
    updateTaskStatus: (taskId: string, status: TaskStatus) =>
      request<{ success: boolean; id: string; status: string }>(`/api/missions/tasks/${taskId}/status`, {
        method: "POST", body: JSON.stringify({ status }),
      }),
    deleteTask: (taskId: string) =>
      request<{ success: boolean }>(`/api/missions/tasks/${taskId}`, { method: "DELETE" }),
    getStats: () => request<TaskStats>("/api/missions/stats"),
  },

  workspace: {
    listWorktrees: () => request<{ worktrees: WorktreeEntry[] }>("/api/workspace/worktrees"),
    getTree: (worktreeId: string, path?: string, depth = 3) =>
      request<{ tree: TreeNode[] }>(`/api/workspace/tree?worktreeId=${worktreeId}&depth=${depth}${path ? `&path=${encodeURIComponent(path)}` : ""}`),
    getFile: (worktreeId: string, path: string) =>
      request<FileData>(`/api/workspace/file?worktreeId=${worktreeId}&path=${encodeURIComponent(path)}`),
    search: (worktreeId: string, query: string, type: "content" | "filename" | "all" = "content") =>
      request<{ results: SearchResult[] }>("/api/workspace/search", {
        method: "POST",
        body: JSON.stringify({ worktreeId, query, type }),
      }),
    runCommand: (worktreeId: string, command: string) =>
      request<TerminalResult>("/api/workspace/terminal", {
        method: "POST",
        body: JSON.stringify({ worktreeId, command }),
      }),
    gitStatus: (worktreeId: string) =>
      request<GitStatus>(`/api/workspace/git-status?worktreeId=${worktreeId}`),
    gitDiff: (worktreeId: string, path?: string) =>
      request<{ diff: string }>(`/api/workspace/git-diff?worktreeId=${worktreeId}${path ? `&path=${encodeURIComponent(path)}` : ""}`),
    reveal: (worktreeId: string, path: string) =>
      request<{ success: boolean }>("/api/workspace/reveal", {
        method: "POST",
        body: JSON.stringify({ worktreeId, path }),
      }),
  },

  workflow: {
    listTemplates: () => request<WorkflowTemplate[]>("/api/workflow/templates"),
    listActive: () => request<{ workflows: ActiveWorkflow[] }>("/api/workflow/active"),
  },

  voice: {
    tts: async (text: string, catId: string, threadId: string): Promise<Blob> => {
      const token = getToken();
      const formData = new FormData();
      formData.append("text", text);
      formData.append("cat_id", catId);
      formData.append("thread_id", threadId);

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(`${BASE_URL}/api/voice/tts`, {
        method: "POST",
        body: formData,
        headers,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || body.error || `HTTP ${res.status}`);
      }
      return res.blob();
    },

    asr: (audio: Blob, language = "zh"): Promise<{ text: string; language: string }> => {
      const formData = new FormData();
      formData.append("audio", audio, "recording.webm");
      formData.append("language", language);
      return request<{ text: string; language: string }>("/api/voice/asr", {
        method: "POST",
        body: formData,
      });
    },
  },
};
