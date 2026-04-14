/** Zustand store for cat management — full CRUD. */

import { create } from "zustand";
import { api } from "../api/client";

export interface Cat {
  id: string;
  name: string;
  displayName?: string;
  provider: string;
  defaultModel?: string;
  personality?: string;
  avatar?: string;
  colorPrimary?: string;
  colorSecondary?: string;
  mentionPatterns?: string[];
  cliCommand?: string;
  cliArgs?: string[];
  isAvailable: boolean;
  roles?: string[];
  evaluation?: string;
  capabilities?: string[];
  permissions?: string[];
  accountRef?: string;
}

interface CatState {
  cats: Cat[];
  defaultCatId: string | null;
  loading: boolean;

  fetchCats: () => Promise<void>;
  getCat: (id: string) => Cat | undefined;
  createCat: (data: {
    id: string;
    name: string;
    displayName?: string;
    provider: string;
    defaultModel?: string;
    personality?: string;
    mentionPatterns?: string[];
  }) => Promise<Cat>;
  updateCat: (
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
  ) => Promise<Cat>;
  deleteCat: (id: string) => Promise<void>;
}

export const useCatStore = create<CatState>((set, get) => ({
  cats: [],
  defaultCatId: null,
  loading: false,

  fetchCats: async () => {
    set({ loading: true });
    try {
      const data = await api.cats.list();
      set({
        cats: data.cats,
        defaultCatId: data.defaultCat,
      });
    } finally {
      set({ loading: false });
    }
  },

  getCat: (id: string) => {
    return get().cats.find((c) => c.id === id);
  },

  createCat: async (data) => {
    const cat = await api.cats.create(data);
    // Refresh the list
    await get().fetchCats();
    return cat;
  },

  updateCat: async (id, data) => {
    const cat = await api.cats.update(id, data);
    // Refresh the list
    await get().fetchCats();
    return cat;
  },

  deleteCat: async (id) => {
    await api.cats.delete(id);
    // Refresh the list
    await get().fetchCats();
  },
}));
