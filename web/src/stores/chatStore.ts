/** Zustand store for chat messages and streaming state. */

import { create } from "zustand";
import { api } from "../api/client";
import type { MessageResponse, StreamingCatResponse } from "../types";

export type DeliveryMode = "queue" | "force" | undefined;

/** F097: CLI Output unified event stream (clowder-compatible) */
export type CliEventKind = "tool_use" | "tool_result" | "text" | "error";
export type CliStatus = "streaming" | "done" | "failed" | "interrupted";

export interface CliEvent {
  id: string;
  kind: CliEventKind;
  timestamp: number;
  label?: string;
  detail?: string;
  content?: string;
}

/** ToolEvent for toCliEvents conversion */
export interface ToolEvent {
  id: string;
  type: "tool_use" | "tool_result";
  label: string;
  detail?: string;
  timestamp: number;
}

export interface ToolCallState {
  callId: string;
  runId: string;
  toolName: string;
  summary: string;
  detail: string;
  status: "running" | "completed" | "failed" | "cancelled";
  startedAt: number;
  finishedAt?: number;
  durationMs?: number;
}

export interface QueueEntryResponse {
  id: string;
  thread_id: string;
  user_id: string;
  content: string;
  target_cats: string[];
  status: string;
  created_at: number;
  source: string;
  intent: string;
}

interface ChatState {
  messages: MessageResponse[];
  streamingResponses: Map<string, StreamingCatResponse>;
  streamingThinking: Map<string, string>; // catId -> thinking content
  streamingStatuses: Map<string, string>; // catId -> status text
  isStreaming: boolean;
  activeSkill: string | null;
  intentMode: string | null;
  targetCats: string[] | null;
  replyingTo: MessageResponse | null;
  wsConnected: boolean;
  queueEntries: QueueEntryResponse[];
  deliveryMode: DeliveryMode;
  streamingTools: Map<string, ToolCallState[]>; // catId -> tools

  fetchMessages: (threadId: string) => Promise<void>;
  addLocalMessage: (msg: MessageResponse) => void;
  updateMessage: (messageId: string, content: string) => void;
  deleteMessage: (messageId: string) => void;
  setReplyingTo: (msg: MessageResponse | null) => void;
  addStreamingResponse: (catId: string, response: StreamingCatResponse) => void;
  addStreamingThinking: (catId: string, content: string) => void;
  setStreamingStatus: (catId: string, content: string) => void;
  setSkill: (name: string | null) => void;
  setIntentMode: (mode: string | null, cats?: string[]) => void;
  setWsConnected: (connected: boolean) => void;
  startStreaming: () => void;
  stopStreaming: () => void;
  addSystemError: (content: string) => void;
  addSystemMessage: (content: string) => void;
  setQueueEntries: (entries: QueueEntryResponse[]) => void;
  addQueueEntry: (entry: QueueEntryResponse) => void;
  setDeliveryMode: (mode: DeliveryMode) => void;
  clearQueue: () => void;
  addToolEvent: (catId: string, tool: ToolCallState) => void;
  clearToolsForCat: (catId: string) => void;
  clearAll: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingResponses: new Map(),
  streamingThinking: new Map(),
  streamingStatuses: new Map(),
  isStreaming: false,
  activeSkill: null,
  intentMode: null,
  targetCats: null,
  replyingTo: null,
  wsConnected: false,
  queueEntries: [],
  deliveryMode: undefined,
  streamingTools: new Map(),

  fetchMessages: async (threadId: string) => {
    const data = await api.messages.list(threadId);
    set({ messages: data.messages });
  },

  addLocalMessage: (msg) => {
    set((state) => ({ messages: [...state.messages, msg] }));
  },

  updateMessage: (messageId, content) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, content, is_edited: true } : m
      ),
    }));
  },

  deleteMessage: (messageId) => {
    set((state) => ({
      messages: state.messages.filter((m) => m.id !== messageId),
    }));
  },

  setReplyingTo: (msg) => set({ replyingTo: msg }),

  addStreamingResponse: (catId, response) => {
    set((state) => {
      const next = new Map(state.streamingResponses);
      const existing = next.get(catId);
      if (existing) {
        // Accumulate streaming content from incremental chunks
        next.set(catId, {
          ...existing,
          content: existing.content + response.content,
          catName: response.catName || existing.catName,
        });
      } else {
        // First chunk - initialize with empty content base
        next.set(catId, {
          ...response,
          content: response.content,
        });
      }
      return { streamingResponses: next };
    });
  },

  addStreamingThinking: (catId, content) => {
    set((state) => {
      const next = new Map(state.streamingThinking);
      next.set(catId, content);
      return { streamingThinking: next };
    });
  },

  setStreamingStatus: (catId, content) => {
    set((state) => {
      const next = new Map(state.streamingStatuses);
      next.set(catId, content);
      return { streamingStatuses: next };
    });
  },

  setSkill: (name) => set({ activeSkill: name }),
  setIntentMode: (mode, cats) => set({ intentMode: mode, targetCats: cats || null }),
  setWsConnected: (connected) => set({ wsConnected: connected }),

  startStreaming: () =>
    set((state) => ({
      isStreaming: true,
      // Preserve existing streaming state so concurrent responses aren't wiped
      streamingResponses: state.streamingResponses,
      streamingThinking: state.streamingThinking,
      streamingStatuses: state.streamingStatuses,
      // Clear tools from previous session so new session starts fresh
      streamingTools: new Map(),
    })),

  stopStreaming: () =>
    set({
      isStreaming: false,
      streamingResponses: new Map(),
      streamingThinking: new Map(),
      streamingStatuses: new Map(),
      activeSkill: null,
      targetCats: null,
    }),

  addSystemError: (content: string) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content,
          cat_id: "system",
          timestamp: new Date().toISOString(),
          metadata: { is_error: true },
        } as MessageResponse,
      ],
    }));
  },

  addSystemMessage: (content: string) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          content,
          cat_id: "system",
          timestamp: new Date().toISOString(),
          metadata: { is_system: true },
        } as MessageResponse,
      ],
    }));
  },

  setQueueEntries: (entries) => set({ queueEntries: entries }),
  addQueueEntry: (entry) => set((s) => ({ queueEntries: [...s.queueEntries, entry] })),
  setDeliveryMode: (mode) => set({ deliveryMode: mode }),
  clearQueue: () => set({ queueEntries: [], deliveryMode: undefined }),

  addToolEvent: (catId, tool) =>
    set((state) => {
      console.log("[Store] addToolEvent called:", { catId, tool });
      const next = new Map(state.streamingTools);
      const existing = next.get(catId) ?? [];
      // If runId changed, clear old tools for this cat
      const first = existing[0];
      if (first && first.runId !== tool.runId) {
        console.log("[Store] runId changed, clearing old tools");
        next.set(catId, [tool]);
      } else {
        const idx = existing.findIndex((t) => t.callId === tool.callId);
        if (idx >= 0) {
          // Update existing
          console.log("[Store] updating existing tool at index", idx);
          const existingTool = existing[idx];
          const updated = [...existing];
          updated[idx] = {
            ...tool,
            startedAt: existingTool?.startedAt ?? tool.startedAt,
            finishedAt: tool.finishedAt ?? existingTool?.finishedAt,
            durationMs: tool.durationMs ?? existingTool?.durationMs,
          };
          next.set(catId, updated);
        } else {
          console.log("[Store] appending new tool, total:", existing.length + 1);
          next.set(catId, [...existing, tool]);
        }
      }
      console.log("[Store] streamingTools now has", next.size, "cats");
      return { streamingTools: next };
    }),

  clearToolsForCat: (catId) =>
    set((state) => {
      const next = new Map(state.streamingTools);
      next.delete(catId);
      return { streamingTools: next };
    }),

  clearAll: () =>
    set({
      messages: [],
      streamingResponses: new Map(),
      streamingThinking: new Map(),
      streamingStatuses: new Map(),
      isStreaming: false,
      activeSkill: null,
      intentMode: null,
      replyingTo: null,
      wsConnected: false,
      queueEntries: [],
      deliveryMode: undefined,
      streamingTools: new Map(),
    }),
}));
