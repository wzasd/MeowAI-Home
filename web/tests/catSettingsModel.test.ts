import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCatMutationPayload,
  buildCatSettingsModel,
} from "../src/components/settings/catSettingsModel.ts";

test("buildCatMutationPayload uses displayName as the persisted name and trims mentions", () => {
  const payload = buildCatMutationPayload({
    displayName: " 烁烁 ",
    provider: "openai",
    defaultModel: " gpt-5.4 ",
    personality: " 视觉设计师 ",
    mentionPatterns: "@gemini, @烁烁,  , gemini ",
  });

  assert.deepEqual(payload, {
    name: "烁烁",
    displayName: "烁烁",
    provider: "openai",
    defaultModel: "gpt-5.4",
    personality: "视觉设计师",
    mentionPatterns: ["@gemini", "@烁烁", "gemini"],
  });
});

test("buildCatSettingsModel highlights default cat, missing metadata, and availability", () => {
  const model = buildCatSettingsModel({
    defaultCatId: "gemini",
    cats: [
      {
        id: "tabby",
        name: "Tabby",
        displayName: "狸花猫",
        provider: "anthropic",
        defaultModel: "",
        mentionPatterns: [],
        isAvailable: false,
      },
      {
        id: "gemini",
        name: "烁烁",
        displayName: "烁烁",
        provider: "openai",
        defaultModel: "gpt-5.4",
        mentionPatterns: ["@gemini", "@烁烁"],
        personality: "视觉设计师和创意顾问",
        roles: ["视觉设计师", "创意顾问"],
        isAvailable: true,
      },
      {
        id: "opus",
        name: "宪宪",
        displayName: "宪宪",
        provider: "anthropic",
        defaultModel: "claude-opus-4.6",
        mentionPatterns: ["@opus"],
        isAvailable: true,
      },
    ],
  });

  assert.equal(model.summaryCards[0]?.value, "3");
  assert.equal(model.summaryCards[1]?.value, "2/3");
  assert.equal(model.summaryCards[2]?.value, "烁烁");
  assert.equal(model.summaryCards[3]?.value, "1");
  assert.deepEqual(
    model.entries.map((entry) => entry.id),
    ["gemini", "opus", "tabby"]
  );
  assert.equal(model.entries[0]?.isDefault, true);
  assert.equal(model.entries[0]?.metaLabel, "gemini · OpenAI");
  assert.equal(model.entries[0]?.mentionSummary, "@gemini · @烁烁");
  assert.equal(model.entries[0]?.mentionCountLabel, "2 个提及入口");
  assert.equal(model.entries[0]?.roleSummary, "视觉设计师 / 创意顾问");
  assert.equal(model.entries[2]?.needsAttention, true);
  assert.equal(model.entries[2]?.metaLabel, "tabby · Anthropic");
  assert.equal(model.entries[2]?.mentionSummary, "暂未配置");
  assert.equal(model.entries[2]?.mentionCountLabel, "未配置提及入口");
  assert.equal(
    model.entries[2]?.attentionSummary,
    "待补资料：未配置默认模型，未配置 @ 提及别名"
  );
  assert.deepEqual(model.entries[2]?.attentionReasons, ["未配置默认模型", "未配置 @ 提及别名"]);
});
