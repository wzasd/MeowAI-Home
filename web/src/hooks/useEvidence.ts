/** Evidence hook — search and manage evidence documents. */

import { useState, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export type EvidenceConfidence = "high" | "mid" | "low";
export type EvidenceSourceType = "decision" | "phase" | "discussion" | "commit";
export type EvidenceStatus = "draft" | "pending" | "published" | "archived";

export interface EvidenceResult {
  id: number;
  title: string;
  anchor: string;
  snippet: string;
  confidence: EvidenceConfidence;
  source_type: EvidenceSourceType;
  status?: EvidenceStatus;
}

export interface EvidenceSearchResponse {
  results: EvidenceResult[];
  degraded: boolean;
  degrade_reason?: string;
}

export interface EvidenceStatusInfo {
  backend: string;
  healthy: boolean;
  total: number;
  by_kind: Record<string, number>;
  last_updated?: string;
}

interface UseEvidenceReturn {
  results: EvidenceResult[];
  loading: boolean;
  error: string | null;
  degraded: boolean;
  degradeReason: string | null;
  search: (query: string, limit?: number) => Promise<void>;
  fetchStatus: () => Promise<EvidenceStatusInfo | null>;
  createDoc: (doc: {
    title: string;
    anchor?: string;
    summary?: string;
    content?: string;
    kind?: EvidenceSourceType;
    confidence?: EvidenceConfidence;
  }) => Promise<boolean>;
}

export function useEvidence(): UseEvidenceReturn {
  const [results, setResults] = useState<EvidenceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [degraded, setDegraded] = useState(false);
  const [degradeReason, setDegradeReason] = useState<string | null>(null);

  const search = useCallback(async (query: string, limit: number = 5) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ q: query.trim(), limit: String(limit) });
      const res = await fetch(`${API_BASE}/api/evidence/search?${params}`);
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      const data: EvidenceSearchResponse = await res.json();
      setResults(data.results);
      setDegraded(data.degraded);
      setDegradeReason(data.degrade_reason ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchStatus = useCallback(async (): Promise<EvidenceStatusInfo | null> => {
    try {
      const res = await fetch(`${API_BASE}/api/evidence/status`);
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }, []);

  const createDoc = useCallback(
    async (doc: {
      title: string;
      anchor?: string;
      summary?: string;
      content?: string;
      kind?: EvidenceSourceType;
      confidence?: EvidenceConfidence;
    }): Promise<boolean> => {
      try {
        const res = await fetch(`${API_BASE}/api/evidence/docs`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(doc),
        });
        return res.ok;
      } catch {
        return false;
      }
    },
    []
  );

  return {
    results,
    loading,
    error,
    degraded,
    degradeReason,
    search,
    fetchStatus,
    createDoc,
  };
}
