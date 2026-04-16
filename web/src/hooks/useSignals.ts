/** Signals hook — fetch and manage signal articles and sources. */

import { useState, useEffect, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export type ArticleTier = "S" | "A" | "B" | "C";
export type ArticleStatus = "unread" | "reading" | "read" | "starred";

export interface SignalArticle {
  id: string;
  title: string;
  url: string;
  source: string;
  tier: ArticleTier;
  status: ArticleStatus;
  summary: string;
  keywords: string[];
  publishedAt: string;
  readTime?: number;
}

export interface SignalSource {
  id: string;
  name: string;
  tier: ArticleTier;
  fetchMethod: string;
  schedule: string;
  lastFetchedAt?: string;
  enabled: boolean;
}

export interface ResearchReport {
  title: string;
  sections: Array<{
    cat_id: string;
    cat_name: string;
    role: string;
    content: string;
  }>;
  summary: string;
}

interface UseSignalsReturn {
  articles: SignalArticle[];
  sources: SignalSource[];
  loading: boolean;
  error: string | null;
  filter: ArticleStatus | "all";
  setFilter: (filter: ArticleStatus | "all") => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedArticle: SignalArticle | null;
  setSelectedArticle: (article: SignalArticle | null) => void;
  fetchArticles: () => Promise<void>;
  fetchSources: () => Promise<void>;
  searchArticles: (query: string) => Promise<void>;
  updateArticleStatus: (articleId: string, status: ArticleStatus) => Promise<boolean>;
  starArticle: (articleId: string) => Promise<boolean>;
  refreshSource: (sourceId: string) => Promise<boolean>;
  getNotes: (articleId: string) => Promise<string>;
  saveNotes: (articleId: string, notes: string) => Promise<boolean>;
  generatePodcast: (articleId: string) => Promise<Blob>;
  generateResearch: (articleId: string) => Promise<ResearchReport>;
}

export function useSignals(): UseSignalsReturn {
  const [articles, setArticles] = useState<SignalArticle[]>([]);
  const [sources, setSources] = useState<SignalSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ArticleStatus | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedArticle, setSelectedArticle] = useState<SignalArticle | null>(null);

  // Fetch articles
  const fetchArticles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filter !== "all") {
        params.set("status", filter);
      }
      params.set("limit", "50");

      const res = await fetch(`${API_BASE}/api/signals/articles?${params}`);
      if (!res.ok) {
        throw new Error(`Failed to fetch articles: ${res.status}`);
      }
      const data = await res.json();
      setArticles(data.articles ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch articles");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  // Fetch sources
  const fetchSources = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/sources`);
      if (!res.ok) {
        throw new Error(`Failed to fetch sources: ${res.status}`);
      }
      const data = await res.json();
      setSources(data.sources ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch sources");
    }
  }, []);

  // Search articles
  const searchArticles = useCallback(async (query: string) => {
    if (!query.trim()) {
      await fetchArticles();
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: "20" });
      const res = await fetch(`${API_BASE}/api/signals/articles/search?${params}`);
      if (!res.ok) {
        throw new Error(`Failed to search articles: ${res.status}`);
      }
      const data = await res.json();
      setArticles(data.articles ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search articles");
    } finally {
      setLoading(false);
    }
  }, [fetchArticles]);

  // Update article status
  const updateArticleStatus = useCallback(async (articleId: string, status: ArticleStatus): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) {
        return false;
      }
      // Update local state
      setArticles((prev) =>
        prev.map((a) => (a.id === articleId ? { ...a, status } : a))
      );
      if (selectedArticle?.id === articleId) {
        setSelectedArticle((prev) => (prev ? { ...prev, status } : null));
      }
      return true;
    } catch {
      return false;
    }
  }, [selectedArticle]);

  // Star article
  const starArticle = useCallback(async (articleId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/star`, {
        method: "POST",
      });
      if (!res.ok) {
        return false;
      }
      // Update local state
      setArticles((prev) =>
        prev.map((a) => (a.id === articleId ? { ...a, status: "starred" } : a))
      );
      if (selectedArticle?.id === articleId) {
        setSelectedArticle((prev) => (prev ? { ...prev, status: "starred" } : null));
      }
      return true;
    } catch {
      return false;
    }
  }, [selectedArticle]);

  // Refresh source
  const refreshSource = useCallback(async (sourceId: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/sources/${sourceId}/refresh`, {
        method: "POST",
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  // Get notes
  const getNotes = useCallback(async (articleId: string): Promise<string> => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/notes`);
      if (!res.ok) return "";
      const data = await res.json();
      return data.notes || "";
    } catch {
      return "";
    }
  }, []);

  // Save notes
  const saveNotes = useCallback(async (articleId: string, notes: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  // Generate podcast
  const generatePodcast = useCallback(async (articleId: string): Promise<Blob> => {
    const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/podcast`, {
      method: "POST",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    return res.blob();
  }, []);

  // Generate research report
  const generateResearch = useCallback(async (articleId: string): Promise<ResearchReport> => {
    const res = await fetch(`${API_BASE}/api/signals/articles/${articleId}/research`, {
      method: "POST",
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchArticles();
    fetchSources();
  }, [fetchArticles, fetchSources]);

  return {
    articles,
    sources,
    loading,
    error,
    filter,
    setFilter,
    searchQuery,
    setSearchQuery,
    selectedArticle,
    setSelectedArticle,
    fetchArticles,
    fetchSources,
    searchArticles,
    updateArticleStatus,
    starArticle,
    refreshSource,
    getNotes,
    saveNotes,
    generatePodcast,
    generateResearch,
  };
}
