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
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
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
};
