/** Zustand store for chat messages and streaming state. */

import { create } from "zustand";
import { api } from "../api/client";
import type { MessageResponse, StreamingCatResponse } from "../types";

interface ChatState {
  messages: MessageResponse[];
  streamingResponses: Map<string, StreamingCatResponse>;
  streamingThinking: Map<string, string>; // catId -> thinking content
  isStreaming: boolean;
  activeSkill: string | null;
  intentMode: string | null;
  replyingTo: MessageResponse | null;

  fetchMessages: (threadId: string) => Promise<void>;
  addLocalMessage: (msg: MessageResponse) => void;
  updateMessage: (messageId: string, content: string) => void;
  deleteMessage: (messageId: string) => void;
  setReplyingTo: (msg: MessageResponse | null) => void;
  addStreamingResponse: (catId: string, response: StreamingCatResponse) => void;
  addStreamingThinking: (catId: string, content: string) => void;
  setSkill: (name: string | null) => void;
  setIntentMode: (mode: string | null) => void;
  startStreaming: () => void;
  stopStreaming: () => void;
  clearAll: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingResponses: new Map(),
  streamingThinking: new Map(),
  isStreaming: false,
  activeSkill: null,
  intentMode: null,
  replyingTo: null,

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

  setSkill: (name) => set({ activeSkill: name }),
  setIntentMode: (mode) => set({ intentMode: mode }),

  startStreaming: () =>
    set({
      isStreaming: true,
      streamingResponses: new Map(),
      streamingThinking: new Map(),
    }),

  stopStreaming: () =>
    set({
      isStreaming: false,
      streamingResponses: new Map(),
      streamingThinking: new Map(),
      activeSkill: null,
    }),

  clearAll: () =>
    set({
      messages: [],
      streamingResponses: new Map(),
      streamingThinking: new Map(),
      isStreaming: false,
      activeSkill: null,
      intentMode: null,
      replyingTo: null,
    }),
}));
