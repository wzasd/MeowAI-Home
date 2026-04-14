import { create } from "zustand";
import { api } from "../api/client";
import type { AccountResponse, AuthType, Protocol } from "../types";

interface AccountState {
  accounts: AccountResponse[];
  loading: boolean;
  fetchAccounts: () => Promise<void>;
  createAccount: (data: {
    id: string; displayName: string; protocol: Protocol; authType: AuthType;
    baseUrl?: string; models?: string[]; apiKey?: string;
  }) => Promise<AccountResponse>;
  updateAccount: (id: string, data: Record<string, unknown>) => Promise<void>;
  deleteAccount: (id: string) => Promise<void>;
  testKey: (accountId: string, apiKey: string, protocol: Protocol, baseUrl?: string) => Promise<boolean>;
  bindCat: (catId: string, accountRef: string) => Promise<void>;
}

export const useAccountStore = create<AccountState>((set, get) => ({
  accounts: [],
  loading: false,

  fetchAccounts: async () => {
    set({ loading: true });
    try {
      const data = await api.config.accounts.list();
      set({ accounts: data.accounts, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  createAccount: async (data) => {
    const acc = await api.config.accounts.create(data);
    await get().fetchAccounts();
    return acc;
  },

  updateAccount: async (id, data) => {
    await api.config.accounts.update(id, data);
    await get().fetchAccounts();
  },

  deleteAccount: async (id) => {
    await api.config.accounts.delete(id);
    await get().fetchAccounts();
  },

  testKey: async (accountId, apiKey, protocol, baseUrl) => {
    const result = await api.config.accounts.testKey(accountId, apiKey, protocol, baseUrl);
    return result.valid;
  },

  bindCat: async (catId, accountRef) => {
    await api.config.accounts.bindCat(catId, accountRef);
    await get().fetchAccounts();
  },
}));
