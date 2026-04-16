/** Workflows hook — fetch workflow templates and active workflows. */

import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { WorkflowTemplate, ActiveWorkflow } from "../api/client";

export type { WorkflowTemplate, ActiveWorkflow } from "../api/client";

interface UseWorkflowsReturn {
  templates: WorkflowTemplate[];
  active: ActiveWorkflow[];
  loading: boolean;
  error: string | null;
  fetchWorkflows: () => Promise<void>;
}

export function useWorkflows(): UseWorkflowsReturn {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [active, setActive] = useState<ActiveWorkflow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkflows = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [templatesData, activeData] = await Promise.all([
        api.workflow.listTemplates(),
        api.workflow.listActive(),
      ]);

      setTemplates(templatesData || []);
      setActive(activeData.workflows || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  return { templates, active, loading, error, fetchWorkflows };
}
