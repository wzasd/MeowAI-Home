/** REST API client for MeowAI Home backend. */

import type { ThreadDetailResponse, ThreadListResponse, MessageListResponse } from "../types";

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

    create: (name: string, catId?: string) =>
      request<ThreadDetailResponse>("/api/threads", {
        method: "POST",
        body: JSON.stringify({ name, cat_id: catId }),
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
  },

  messages: {
    list: (threadId: string, limit = 50, offset = 0) =>
      request<MessageListResponse>(
        `/api/threads/${threadId}/messages?limit=${limit}&offset=${offset}`
      ),
  },
};
