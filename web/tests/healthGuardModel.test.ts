import assert from "node:assert/strict";
import test from "node:test";

import {
  getAlertLevel,
  getSnoozeUntil,
  isHealthGuardSnoozed,
} from "../src/components/ui/healthGuardModel.ts";

test("getAlertLevel escalates by elapsed usage time", () => {
  const now = Date.UTC(2026, 3, 18, 4, 0, 0);

  assert.equal(getAlertLevel(null, now), "none");
  assert.equal(getAlertLevel(now - 29 * 60 * 1000, now), "none");
  assert.equal(getAlertLevel(now - 30 * 60 * 1000, now), "l1");
  assert.equal(getAlertLevel(now - 60 * 60 * 1000, now), "l2");
  assert.equal(getAlertLevel(now - 120 * 60 * 1000, now), "l3");
});

test("l3 alerts can be snoozed across refresh", () => {
  const now = Date.UTC(2026, 3, 18, 4, 0, 0);
  const snoozeUntil = getSnoozeUntil("l3", now);

  assert.equal(isHealthGuardSnoozed(snoozeUntil, now), true);
  assert.equal(isHealthGuardSnoozed(snoozeUntil, now + 10 * 60 * 1000), true);
  assert.equal(isHealthGuardSnoozed(snoozeUntil, now + 16 * 60 * 1000), false);
});

