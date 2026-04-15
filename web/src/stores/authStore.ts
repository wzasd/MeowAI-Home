import { create } from "zustand";
import { api } from "../api/client";
import type { AuthUserResponse, TokenResponse } from "../types";

interface AuthState {
  token: string | null;
  user: AuthUserResponse | null;
  isLoading: boolean;
  error: string | null;

  init: () => Promise<void>;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string, role?: string) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

const STORAGE_KEY = "meowai:token";

export const useAuthStore = create<AuthState>((set, get) => ({
  token: null,
  user: null,
  isLoading: false,
  error: null,

  init: async () => {
    set({ isLoading: true });
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      set({ token: stored });
      try {
        const user = await api.auth.me();
        set({ user, isLoading: false });
      } catch {
        localStorage.removeItem(STORAGE_KEY);
        set({ token: null, user: null, isLoading: false });
      }
    } else {
      set({ isLoading: false });
    }
  },

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const data: TokenResponse = await api.auth.login(username, password);
      localStorage.setItem(STORAGE_KEY, data.access_token);
      set({ token: data.access_token, user: { username: data.username, role: data.role }, isLoading: false });
      return true;
    } catch (e: any) {
      set({ error: e.message || "登录失败", isLoading: false });
      return false;
    }
  },

  register: async (username, password, role = "member") => {
    set({ isLoading: true, error: null });
    try {
      await api.auth.register(username, password, role);
      return await get().login(username, password);
    } catch (e: any) {
      set({ error: e.message || "注册失败", isLoading: false });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY);
    set({ token: null, user: null, error: null });
  },

  clearError: () => set({ error: null }),
}));
