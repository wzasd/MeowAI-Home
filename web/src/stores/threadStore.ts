/** Zustand store for thread list and current thread selection. */

import { create } from "zustand";
import { api } from "../api/client";
import type { ThreadResponse, ThreadDetailResponse } from "../types";

interface ThreadState {
  threads: ThreadResponse[];
  currentThreadId: string | null;
  currentThread: ThreadDetailResponse | null;
  loading: boolean;

  fetchThreads: () => Promise<void>;
  selectThread: (id: string) => Promise<void>;
  createThread: (name: string, catId?: string) => Promise<string | null>;
  deleteThread: (id: string) => Promise<void>;
  clearCurrent: () => void;
}

export const useThreadStore = create<ThreadState>((set, get) => ({
  threads: [],
  currentThreadId: null,
  currentThread: null,
  loading: false,

  fetchThreads: async () => {
    set({ loading: true });
    try {
      const data = await api.threads.list();
      set({ threads: data.threads });
    } finally {
      set({ loading: false });
    }
  },

  selectThread: async (id: string) => {
    set({ currentThreadId: id, loading: true });
    try {
      const thread = await api.threads.get(id);
      set({ currentThread: thread });
    } finally {
      set({ loading: false });
    }
  },

  createThread: async (name: string, catId?: string) => {
    const thread = await api.threads.create(name, catId);
    const threadSummary: ThreadResponse = {
      id: thread.id,
      name: thread.name,
      created_at: thread.created_at,
      updated_at: thread.updated_at,
      current_cat_id: thread.current_cat_id,
      is_archived: thread.is_archived,
      message_count: thread.messages.length,
    };
    set((state) => ({
      threads: [threadSummary, ...state.threads],
      currentThreadId: thread.id,
      currentThread: thread,
    }));
    return thread.id;
  },

  deleteThread: async (id: string) => {
    await api.threads.delete(id);
    const state = get();
    const newThreads = state.threads.filter((t) => t.id !== id);
    const isCurrent = state.currentThreadId === id;
    set({
      threads: newThreads,
      currentThreadId: isCurrent ? null : state.currentThreadId,
      currentThread: isCurrent ? null : state.currentThread,
    });
  },

  clearCurrent: () => {
    set({ currentThreadId: null, currentThread: null });
  },
}));
