import assert from "node:assert/strict";
import test from "node:test";

import {
  SETTINGS_GROUP_ORDER,
  buildSettingsOverviewCards,
  findSettingsPage,
  getSettingsPagesByGroup,
} from "../src/components/settings/settingsRegistry.ts";

test("settings registry groups pages by user intent instead of a flat tab list", () => {
  assert.deepEqual(
    SETTINGS_GROUP_ORDER.map((group) => group.id),
    ["identity", "runtime", "automation", "observability"]
  );

  assert.deepEqual(
    getSettingsPagesByGroup("identity").map((page) => page.id),
    ["cats", "accounts", "connectors"]
  );
  assert.deepEqual(
    getSettingsPagesByGroup("runtime").map((page) => page.id),
    ["capabilities", "permissions", "env", "appearance"]
  );
  assert.deepEqual(
    getSettingsPagesByGroup("automation").map((page) => page.id),
    ["scheduler", "review", "limbs"]
  );
  assert.deepEqual(
    getSettingsPagesByGroup("observability").map((page) => page.id),
    ["governance"]
  );
});

test("settings registry keeps save mode metadata in one place", () => {
  assert.equal(findSettingsPage("capabilities")?.saveMode, "auto");
  assert.equal(findSettingsPage("accounts")?.saveMode, "manual");
  assert.equal(findSettingsPage("governance")?.saveMode, "mixed");
});

test("quota and leaderboard are removed from settings registry", () => {
  assert.equal(findSettingsPage("quota"), undefined);
  assert.equal(findSettingsPage("leaderboard"), undefined);
});

test("overview cards stay static and mirror the grouped navigation model", () => {
  const cards = buildSettingsOverviewCards();

  assert.equal(cards.length, 4);
  assert.deepEqual(
    cards.map((card) => card.groupId),
    ["identity", "runtime", "automation", "observability"]
  );

  assert.equal(cards[0]?.targetPageId, "cats");
  assert.equal(cards[1]?.targetPageId, "capabilities");
  assert.equal(cards[2]?.targetPageId, "scheduler");
  assert.equal(cards[3]?.targetPageId, "governance");
  assert.equal(cards[3]?.flagLabel, undefined);
  assert.equal(cards[3]?.description, "查看治理状态，并通过右侧状态台观察运行指标。");
});
