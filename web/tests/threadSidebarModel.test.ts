import assert from "node:assert/strict";
import test from "node:test";

import { buildThreadSidebarModel } from "../src/components/thread/threadSidebarModel.ts";

test("buildThreadSidebarModel builds compact summary and groups task/free/archive nests", () => {
  const model = buildThreadSidebarModel({
    search: "",
    threads: [
      {
        id: "thread-task-doing",
        name: "重构状态栏",
        created_at: "2026-04-17T09:00:00+08:00",
        updated_at: "2026-04-17T09:20:00+08:00",
        current_cat_id: "gemini",
        is_archived: false,
        message_count: 18,
        project_path: "/workspace/catwork",
      },
      {
        id: "thread-task-done",
        name: "收尾任务墙",
        created_at: "2026-04-17T08:40:00+08:00",
        updated_at: "2026-04-17T09:10:00+08:00",
        current_cat_id: "opus",
        is_archived: false,
        message_count: 9,
        project_path: "/workspace/catwork",
      },
      {
        id: "thread-free",
        name: "自由猫窝",
        created_at: "2026-04-17T08:30:00+08:00",
        updated_at: "2026-04-17T09:25:00+08:00",
        current_cat_id: "gemini",
        is_archived: false,
        message_count: 33,
      },
      {
        id: "thread-archived",
        name: "旧归档窝",
        created_at: "2026-04-16T20:30:00+08:00",
        updated_at: "2026-04-16T21:00:00+08:00",
        current_cat_id: "opus",
        is_archived: true,
        message_count: 41,
      },
    ],
    cats: [
      { id: "gemini", name: "gemini", displayName: "烁烁", provider: "openai", isAvailable: true },
      { id: "opus", name: "opus", displayName: "宪宪", provider: "anthropic", isAvailable: true },
      { id: "opencode", name: "opencode", displayName: "金渐层", provider: "opencode", isAvailable: false },
    ],
    tasks: [
      {
        id: "task-done",
        title: "任务墙联动",
        description: "",
        status: "done",
        priority: "P0",
        tags: [],
        createdAt: "2026-04-17T08:35:00+08:00",
        thread_ids: ["thread-task-done"],
      },
      {
        id: "task-doing",
        title: "状态台收口",
        description: "",
        status: "doing",
        priority: "P1",
        tags: [],
        createdAt: "2026-04-17T09:05:00+08:00",
        thread_ids: ["thread-task-doing"],
      },
    ],
  });

  assert.equal(model.summary.activeNestCount, 3);
  assert.equal(model.summary.freeNestCount, 1);
  assert.equal(model.summary.onDutyCatCount, 2);
  assert.equal(model.summary.activeTaskCount, 1);
  assert.equal(model.summary.blockedTaskCount, 0);
  assert.equal(model.summary.title, "流浪猫工作室");
  assert.equal(model.summary.compactLine, "今晚有 3 个在线猫窝，2 只猫值班");
  assert.equal(model.summary.supportLine, "自由窝 1 · 任务 1 · 归档 1");
  assert.equal("strips" in model.summary, false);
  assert.deepEqual(
    model.taskGroups.map((group) => group.task.id),
    ["task-doing", "task-done"]
  );
  assert.deepEqual(
    model.freeThreads.map((thread) => thread.id),
    ["thread-free"]
  );
  assert.deepEqual(
    model.archivedThreads.map((thread) => thread.id),
    ["thread-archived"]
  );
});

test("buildThreadSidebarModel keeps search local to the matching group and returns the right empty copy", () => {
  const model = buildThreadSidebarModel({
    search: "不存在",
    threads: [
      {
        id: "thread-free",
        name: "自由猫窝",
        created_at: "2026-04-17T08:30:00+08:00",
        updated_at: "2026-04-17T09:25:00+08:00",
        current_cat_id: "gemini",
        is_archived: false,
        message_count: 33,
      },
    ],
    cats: [],
    tasks: [],
  });

  assert.equal(model.isEmpty, true);
  assert.equal(model.emptyMessage, "没有匹配的猫窝");
  assert.equal(model.taskGroups.length, 0);
  assert.equal(model.freeThreads.length, 0);
  assert.equal(model.archivedThreads.length, 0);
});
