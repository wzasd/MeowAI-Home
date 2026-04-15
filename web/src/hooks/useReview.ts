"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export interface ReviewTracking {
  pr_number: number;
  repository: string;
  pr_title: string;
  status: string;
  assigned_cat_id?: string;
  created_at: number;
  updated_at: number;
  review_count: number;
  comments_count: number;
}

export interface CICheck {
  name: string;
  status: string;
  conclusion?: string;
  url?: string;
}

export interface PRCIState {
  pr_number: number;
  repository: string;
  overall_status: string;
  checks: CICheck[];
  updated_at: number;
}

export interface ReviewDetail extends ReviewTracking {
  ci_state?: {
    overall_status: string;
    checks: CICheck[];
    updated_at: number;
  };
}

interface UseReviewReturn {
  pending: ReviewTracking[];
  ciPRs: PRCIState[];
  loading: boolean;
  error: string | null;
  fetchPending: () => Promise<void>;
  fetchCIStatus: () => Promise<void>;
  getTracking: (repository: string, prNumber: number) => Promise<ReviewDetail | null>;
  assignReviewer: (repository: string, prNumber: number, catId: string) => Promise<boolean>;
  deleteTracking: (repository: string, prNumber: number) => Promise<boolean>;
  createPR: (data: {
    repository: string;
    pr_number: number;
    pr_title: string;
    pr_body?: string;
    branch?: string;
    author?: string;
    labels?: string[];
    reviewers?: string[];
  }) => Promise<boolean>;
  pollCI: () => Promise<boolean>;
  suggestReviewers: (repository: string, files: string[]) => Promise<{ cat_id: string; score: number }[]>;
}

export function useReview(): UseReviewReturn {
  const [pending, setPending] = useState<ReviewTracking[]>([]);
  const [ciPRs, setCiPRs] = useState<PRCIState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPending = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/review/pending`);
      if (!res.ok) throw new Error(`Failed to fetch pending reviews: ${res.status}`);
      const data = await res.json();
      setPending(data.reviews || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch pending reviews");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchCIStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/review/ci/status`);
      if (!res.ok) throw new Error(`Failed to fetch CI status: ${res.status}`);
      const data = await res.json();
      setCiPRs(data.prs || []);
    } catch (err) {
      console.error("Failed to fetch CI status:", err);
    }
  }, []);

  const getTracking = useCallback(async (repository: string, prNumber: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/review/tracking/${encodeURIComponent(repository)}/${prNumber}`);
      if (!res.ok) return null;
      return (await res.json()) as ReviewDetail;
    } catch {
      return null;
    }
  }, []);

  const assignReviewer = useCallback(async (repository: string, prNumber: number, catId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/review/tracking/${encodeURIComponent(repository)}/${prNumber}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cat_id: catId }),
      });
      if (!res.ok) return false;
      setPending((prev) =>
        prev.map((p) =>
          p.repository === repository && p.pr_number === prNumber ? { ...p, assigned_cat_id: catId } : p
        )
      );
      return true;
    } catch {
      return false;
    }
  }, []);

  const deleteTracking = useCallback(async (repository: string, prNumber: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/review/tracking/${encodeURIComponent(repository)}/${prNumber}`, {
        method: "DELETE",
      });
      if (!res.ok) return false;
      setPending((prev) => prev.filter((p) => !(p.repository === repository && p.pr_number === prNumber)));
      return true;
    } catch {
      return false;
    }
  }, []);

  const createPR = useCallback(async (data) => {
    try {
      const res = await fetch(`${API_BASE}/api/review/pr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) return false;
      return true;
    } catch {
      return false;
    }
  }, []);

  const pollCI = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/review/ci/poll`, { method: "POST" });
      if (!res.ok) return false;
      await fetchCIStatus();
      return true;
    } catch {
      return false;
    }
  }, [fetchCIStatus]);

  const suggestReviewers = useCallback(async (repository: string, files: string[]) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/review/suggest-reviewers?repository=${encodeURIComponent(repository)}&files=${encodeURIComponent(files.join(","))}`
      );
      if (!res.ok) return [];
      const data = await res.json();
      return data.suggestions || [];
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    fetchPending();
    fetchCIStatus();
  }, [fetchPending, fetchCIStatus]);

  return {
    pending,
    ciPRs,
    loading,
    error,
    fetchPending,
    fetchCIStatus,
    getTracking,
    assignReviewer,
    deleteTracking,
    createPR,
    pollCI,
    suggestReviewers,
  };
}
