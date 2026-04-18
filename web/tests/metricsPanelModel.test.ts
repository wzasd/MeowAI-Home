import assert from "node:assert/strict";
import test from "node:test";

import {
  buildQuotaSectionState,
  type QuotaSectionState,
} from "../src/components/right-panel/metricsPanelModel.ts";
import type { QuotaMetricSnapshot } from "../src/components/settings/settingsSummaryModels.ts";

const ACTIVE_METRIC: QuotaMetricSnapshot = {
  catId: "gemini",
  totalInvocations: 6,
  successRate: 1,
  avgLatencyMs: 900,
  totalTokens: 32000,
  trend: "up",
};

test("quota section treats full fetch failure as error instead of empty state", () => {
  const state = buildQuotaSectionState({
    metrics: [
      {
        catId: "gemini",
        totalInvocations: 0,
        successRate: 1,
        avgLatencyMs: 0,
        totalTokens: 0,
        trend: "stable",
      },
    ],
    error: "所有猫咪的配额数据拉取失败，请稍后刷新重试",
    partialFailure: false,
  });

  assert.deepEqual(state, {
    kind: "error",
    activeMetrics: [],
    message: "所有猫咪的配额数据拉取失败，请稍后刷新重试",
  } satisfies QuotaSectionState);
});

test("quota section keeps visible data and warning when only part of the fleet fails", () => {
  const state = buildQuotaSectionState({
    metrics: [
      ACTIVE_METRIC,
      {
        catId: "codex",
        totalInvocations: 0,
        successRate: 1,
        avgLatencyMs: 0,
        totalTokens: 0,
        trend: "stable",
      },
    ],
    error: null,
    partialFailure: true,
  });

  assert.deepEqual(state, {
    kind: "data",
    activeMetrics: [ACTIVE_METRIC],
    warning: "部分猫咪的数据拉取失败，当前先展示可用样本。",
  } satisfies QuotaSectionState);
});
