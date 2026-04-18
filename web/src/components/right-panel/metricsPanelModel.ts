import type { QuotaMetricSnapshot } from "../settings/settingsSummaryModels";

interface BuildQuotaSectionStateArgs {
  metrics: QuotaMetricSnapshot[];
  error: string | null;
  partialFailure: boolean;
}

type QuotaSectionErrorState = {
  kind: "error";
  activeMetrics: QuotaMetricSnapshot[];
  message: string;
};

type QuotaSectionEmptyState = {
  kind: "empty";
  activeMetrics: QuotaMetricSnapshot[];
};

type QuotaSectionDataState = {
  kind: "data";
  activeMetrics: QuotaMetricSnapshot[];
  warning?: string;
};

export type QuotaSectionState =
  | QuotaSectionErrorState
  | QuotaSectionEmptyState
  | QuotaSectionDataState;

export function buildQuotaSectionState({
  metrics,
  error,
  partialFailure,
}: BuildQuotaSectionStateArgs): QuotaSectionState {
  const activeMetrics = metrics.filter((metric) => metric.totalInvocations > 0);

  if (error && activeMetrics.length === 0) {
    return {
      kind: "error",
      activeMetrics,
      message: error,
    };
  }

  if (activeMetrics.length === 0) {
    return {
      kind: "empty",
      activeMetrics,
    };
  }

  return {
    kind: "data",
    activeMetrics,
    warning: partialFailure ? "部分猫咪的数据拉取失败，当前先展示可用样本。" : undefined,
  };
}
