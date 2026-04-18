import assert from "node:assert/strict";
import test from "node:test";

import { buildTaskBoardModel } from "../src/components/right-panel/taskPanelModel.ts";

test("buildTaskBoardModel groups tasks by cat and hides empty cats", () => {
  const model = buildTaskBoardModel(
    [
      { id: "t1", title: "改状态台", status: "doing", ownerCat: "gemini" },
      { id: "t2", title: "修弹窗", status: "blocked", ownerCat: "sonnet" },
      { id: "t3", title: "补文案", status: "done" },
    ],
    [
      {
        id: "gemini",
        name: "gemini",
        displayName: "烁烁",
        provider: "openai",
        isAvailable: true,
        defaultModel: "gpt-5.4",
        colorPrimary: "#f97316",
      },
      {
        id: "sonnet",
        name: "sonnet",
        displayName: "Sonnet",
        provider: "anthropic",
        isAvailable: true,
        defaultModel: "claude-sonnet-4",
        colorPrimary: "#14b8a6",
      },
      {
        id: "idle",
        name: "idle",
        displayName: "阿橘",
        provider: "anthropic",
        isAvailable: true,
        defaultModel: "claude-opus-4-6",
      },
    ]
  );

  assert.equal(model.total, 3);
  assert.deepEqual(
    model.sections.map((section) => section.id),
    ["gemini", "sonnet", "unassigned"]
  );
  assert.equal(model.sections[0]?.counts.doing, 1);
  assert.equal(model.sections[1]?.counts.blocked, 1);
  assert.equal(model.sections[2]?.name, "未指派");
});
