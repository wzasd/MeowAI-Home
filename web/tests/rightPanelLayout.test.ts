import test from "node:test";
import assert from "node:assert/strict";

import { RIGHT_PANEL_TABS } from "../src/components/right-panel/panelLayout.ts";
import { getRightPanelSubtitle } from "../src/components/right-panel/rightPanelModel.ts";

test("right status panel includes metrics as a dedicated observation tab", () => {
  assert.deepEqual(
    RIGHT_PANEL_TABS.map((tab) => tab.key),
    ["status", "tasks", "metrics", "audit"]
  );
});

test("metrics tab subtitle is explicitly global instead of current-thread scoped", () => {
  assert.equal(getRightPanelSubtitle("metrics", "thread_abcdef12"), "全局指标与跨猫表现");
  assert.equal(getRightPanelSubtitle("status", "thread_abcdef12"), "当前线程 thread_a");
  assert.equal(getRightPanelSubtitle("audit", null), "系统审计与安全观察");
});
