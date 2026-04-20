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
  CatMetricsRow,
  TestKeyResponse,
  CapabilityBoardResponse,
  CapabilityPatchRequest,
  Attachment,
  MetricsLeaderboardEntry,
  AuthUserResponse,
  TokenResponse,
} from "../types";
import { buildApiUrl } from "./runtimeConfig";

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
  thread_ids?: string[];
  workflow_id?: string;
  session_ids?: string[];
  pr_url?: string;
  branch?: string;
  commit_hash?: string;
  worktree_path?: string;
  last_activity_at?: number;
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

export interface ThreadTaskEntry {
  id: string;
  title: string;
  status: "todo" | "doing" | "blocked" | "done";
  ownerCat?: string;
  description?: string;
  threadId?: string;
  createdAt: string;
}

export interface QueueEntry {
  id: string;
  content: string;
  targetCats: string[];
  status: "queued" | "processing" | "paused";
  createdAt: string;
  threadId?: string;
}

export interface TokenUsageSnapshot {
  promptTokens: number;
  completionTokens: number;
  cacheHitRate: number;
  totalCost: number;
}

export interface GovernanceFinding {
  rule: string;
  severity: string;
  message: string;
}

export interface GovernanceProject {
  project_path: string;
  status: "healthy" | "stale" | "missing" | "never-synced" | "error";
  pack_version: string | null;
  last_synced_at: string | null;
  findings: GovernanceFinding[];
  confirmed: boolean;
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

export interface TerminalJob {
  id: string;
  worktree_id: string;
  command: string;
  status: string;
  returncode: number | null;
  stdout_tail: string[];
  stderr_tail: string[];
  stdout_line_count: number;
  stderr_line_count: number;
  created_at: number;
  updated_at: number;
  elapsed_ms: number;
}

export type TerminalJobEvent =
  | { type: "status"; status: string; command: string }
  | { type: "started"; command: string }
  | { type: "stdout"; text: string }
  | { type: "stderr"; text: string }
  | { type: "progress"; parser: string; stage?: string; percent?: number; detail: string }
  | { type: "waiting_input"; text: string }
  | { type: "heartbeat"; elapsed_since_output_ms: number; state: string }
  | { type: "exited"; returncode: number; status: string }
  | { type: "timeout"; status: string }
  | { type: "error"; message: string }
  | { type: "heartbeat"; silent: true };

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

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;

  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (options?.headers) {
    const extra = options.headers as Record<string, string>;
    Object.entries(extra).forEach(([k, v]) => {
      headers[k] = v;
    });
  }

  let res: Response;
  try {
    res = await fetch(buildApiUrl(path), {
      ...options,
      headers,
    });
  } catch {
    throw new ApiError("无法连接到服务，请确认前后端地址和服务状态");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || body.error || `HTTP ${res.status}`, res.status);
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

    delete: (id: string) => request<{ status: string }>(`/api/threads/${id}`, { method: "DELETE" }),

    archive: (id: string) =>
      request<ThreadDetailResponse>(`/api/threads/${id}/archive`, {
        method: "POST",
      }),

    sessions: (id: string) =>
      request<
        Array<{
          session_id: string;
          cat_id: string;
          cat_name: string;
          status: "active" | "sealed";
          created_at: number;
          consecutive_restore_failures: number;
          message_count: number;
          tokens_used: number;
          latency_ms: number;
          turn_count: number;
          cli_command: string;
          default_model: string;
          prompt_tokens: number;
          completion_tokens: number;
          cache_read_tokens: number;
          cache_creation_tokens: number;
          budget_max_prompt: number;
          budget_max_context: number;
        }>
      >(`/api/threads/${id}/sessions`),
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
        message_count: number;
        tokens_used: number;
        latency_ms: number;
        turn_count: number;
        cli_command: string;
        default_model: string;
        prompt_tokens: number;
        completion_tokens: number;
        cache_read_tokens: number;
        cache_creation_tokens: number;
        budget_max_prompt: number;
        budget_max_context: number;
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
      request<{
        results: Array<{ threadId: string; messageId: string; content: string; timestamp: string }>;
      }>(`/api/messages/search?q=${encodeURIComponent(query)}&limit=${limit}`),
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
    update: (
      id: string,
      data: {
        name?: string;
        displayName?: string;
        provider?: string;
        defaultModel?: string;
        personality?: string;
        mentionPatterns?: string[];
        capabilities?: string[];
        permissions?: string[];
      }
    ) =>
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
    getQr: (name: string) => request<ConnectorQrResponse>(`/api/connectors/${name}/qr`),
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
        id: string;
        displayName: string;
        protocol: string;
        authType: string;
        baseUrl?: string;
        models?: string[];
        apiKey?: string;
      }) =>
        request<AccountResponse>("/api/config/accounts", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      get: (id: string) => request<AccountResponse>(`/api/config/accounts/${id}`),
      update: (id: string, data: Record<string, unknown>) =>
        request<AccountResponse>(`/api/config/accounts/${id}`, {
          method: "PATCH",
          body: JSON.stringify(data),
        }),
      delete: (id: string) =>
        request<{ success: boolean }>(`/api/config/accounts/${id}`, {
          method: "DELETE",
        }),
      testKey: (accountId: string, apiKey: string, protocol: string, baseUrl?: string) =>
        request<TestKeyResponse>(`/api/config/accounts/${accountId}/test-key`, {
          method: "POST",
          body: JSON.stringify({ apiKey, protocol, baseUrl }),
        }),
      bindCat: (catId: string, accountRef: string) =>
        request<{ success: boolean }>("/api/config/accounts/bind-cat", {
          method: "PATCH",
          body: JSON.stringify({ catId, accountRef }),
        }),
    },
  },

  metrics: {
    tokenUsage: (threadId?: string) =>
      request<TokenUsageSnapshot>(
        `/api/metrics/token-usage${threadId ? `?threadId=${encodeURIComponent(threadId)}` : ""}`
      ),
    cat: (catId: string, days?: number) =>
      request<{ cat_id: string; days: number; data: CatMetricsRow[] }>(
        `/api/metrics/cats?cat_id=${catId}&days=${days ?? 7}`
      ),
    leaderboard: (days?: number) =>
      request<{ days: number; leaderboard: MetricsLeaderboardEntry[] }>(
        `/api/metrics/leaderboard?days=${days ?? 7}`
      ),
  },

  tasks: {
    entries: (threadId?: string) =>
      request<ThreadTaskEntry[]>(
        `/api/tasks/entries${threadId ? `?threadId=${encodeURIComponent(threadId)}` : ""}`
      ),
  },

  queue: {
    entries: (threadId?: string) =>
      request<QueueEntry[]>(
        `/api/queue/entries${threadId ? `?threadId=${encodeURIComponent(threadId)}` : ""}`
      ),
  },

  governance: {
    listProjects: () => request<{ projects: GovernanceProject[] }>("/api/governance/projects"),
    addProject: (data: {
      project_path: string;
      status?: string;
      version?: string;
      findings?: GovernanceFinding[];
      confirmed?: boolean;
    }) =>
      request<{ success: boolean }>("/api/governance/projects", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    deleteProject: (projectPath: string) =>
      request<{ success: boolean }>(`/api/governance/projects/${encodeURIComponent(projectPath)}`, {
        method: "DELETE",
      }),
    confirmProject: (projectPath: string) =>
      request<{ success: boolean }>("/api/governance/confirm", {
        method: "POST",
        body: JSON.stringify({ project_path: projectPath }),
      }),
    syncProject: (projectPath: string) =>
      request<{ success: boolean }>("/api/governance/sync", {
        method: "POST",
        body: JSON.stringify({ project_path: projectPath }),
      }),
  },

  capabilities: {
    get: (projectPath: string, probe?: boolean) =>
      request<CapabilityBoardResponse>(
        `/api/capabilities?project_path=${encodeURIComponent(projectPath)}${probe ? "&probe=true" : ""}`
      ),
    patch: (data: CapabilityPatchRequest) =>
      request<{ ok: boolean; capability: unknown }>("/api/capabilities", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
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
    getTask: (taskId: string) => request<MissionTask>(`/api/missions/tasks/${taskId}`),
    createTask: (task: Omit<MissionTask, "id" | "createdAt">) =>
      request<MissionTask>("/api/missions/tasks", { method: "POST", body: JSON.stringify(task) }),
    updateTask: (taskId: string, updates: Partial<Omit<MissionTask, "id">>) =>
      request<MissionTask>(`/api/missions/tasks/${taskId}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      }),
    updateTaskStatus: (taskId: string, status: TaskStatus) =>
      request<{ success: boolean; id: string; status: string }>(
        `/api/missions/tasks/${taskId}/status`,
        {
          method: "POST",
          body: JSON.stringify({ status }),
        }
      ),
    deleteTask: (taskId: string) =>
      request<{ success: boolean }>(`/api/missions/tasks/${taskId}`, { method: "DELETE" }),
    getStats: () => request<TaskStats>("/api/missions/stats"),
  },

  workspace: {
    listWorktrees: () => request<{ worktrees: WorktreeEntry[] }>("/api/workspace/worktrees"),
    getTree: (worktreeId: string, path?: string, depth = 3) =>
      request<{ tree: TreeNode[] }>(
        `/api/workspace/tree?worktreeId=${worktreeId}&depth=${depth}${path ? `&path=${encodeURIComponent(path)}` : ""}`
      ),
    getFile: (worktreeId: string, path: string) =>
      request<FileData>(
        `/api/workspace/file?worktreeId=${worktreeId}&path=${encodeURIComponent(path)}`
      ),
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
    createTerminalJob: (worktreeId: string, command: string) =>
      request<{ job_id: string; status: string }>("/api/workspace/terminal/jobs", {
        method: "POST",
        body: JSON.stringify({ worktreeId, command }),
      }),
    getTerminalJob: (jobId: string) =>
      request<TerminalJob>(`/api/workspace/terminal/jobs/${jobId}`),
    cancelTerminalJob: (jobId: string) =>
      request<{ success: boolean; status: string }>(
        `/api/workspace/terminal/jobs/${jobId}/cancel`,
        {
          method: "POST",
        }
      ),
    streamTerminalJob: (
      jobId: string,
      onEvent: (event: TerminalJobEvent) => void,
      onError?: () => void
    ) => {
      const url = buildApiUrl(`/api/workspace/terminal/jobs/${jobId}/stream`);
      const headers: Record<string, string> = {};

      const abortController = new AbortController();

      fetch(url, { headers, signal: abortController.signal })
        .then(async (res) => {
          if (!res.body) return;
          const reader = res.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";
            let eventData = "";
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                eventData = line.slice(6);
              } else if (line === "" && eventData) {
                try {
                  const data = JSON.parse(eventData) as TerminalJobEvent;
                  onEvent(data);
                } catch {
                  // ignore malformed events
                }
                eventData = "";
              }
            }
          }
        })
        .catch(() => {
          onError?.();
        });

      return abortController;
    },
    gitStatus: (worktreeId: string) =>
      request<GitStatus>(`/api/workspace/git-status?worktreeId=${worktreeId}`),
    gitDiff: (worktreeId: string, path?: string) =>
      request<{ diff: string }>(
        `/api/workspace/git-diff?worktreeId=${worktreeId}${path ? `&path=${encodeURIComponent(path)}` : ""}`
      ),
    reveal: (worktreeId: string, path: string) =>
      request<{ success: boolean }>("/api/workspace/reveal", {
        method: "POST",
        body: JSON.stringify({ worktreeId, path }),
      }),
    pickDirectory: () => request<{ path: string }>("/api/workspace/pick-directory"),
  },

  workflow: {
    listTemplates: () => request<WorkflowTemplate[]>("/api/workflow/templates"),
    listActive: () => request<{ workflows: ActiveWorkflow[] }>("/api/workflow/active"),
  },

  voice: {
    tts: async (text: string, catId: string, threadId: string): Promise<Blob> => {
      const formData = new FormData();
      formData.append("text", text);
      formData.append("cat_id", catId);
      formData.append("thread_id", threadId);

      const headers: Record<string, string> = {};

      let res: Response;
      try {
        res = await fetch(buildApiUrl("/api/voice/tts"), {
          method: "POST",
          body: formData,
          headers,
        });
      } catch {
        throw new ApiError("无法连接到服务，请确认前后端地址和服务状态");
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(body.detail || body.error || `HTTP ${res.status}`, res.status);
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
