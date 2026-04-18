import assert from "node:assert/strict";
import test from "node:test";

import { buildCatMentionOptions } from "../src/components/chat/mentionOptions.ts";

test("buildCatMentionOptions uses real roster and mention patterns", () => {
  const options = buildCatMentionOptions([
    {
      id: "opencode",
      name: "opencode",
      displayName: "金渐层",
      provider: "opencode",
      defaultModel: "gpt-5",
      mentionPatterns: ["@opencode", "@金渐层"],
      isAvailable: true,
    },
    {
      id: "gemini25",
      name: "gemini25",
      displayName: "暹罗猫",
      provider: "google",
      mentionPatterns: ["gemini25", "@暹罗猫"],
      isAvailable: true,
    },
    {
      id: "co-creator",
      name: "co-creator",
      displayName: "铲屎官",
      provider: "human",
      isAvailable: true,
    },
    {
      id: "offline-cat",
      name: "offline-cat",
      displayName: "离线猫",
      provider: "anthropic",
      isAvailable: false,
    },
  ]);

  assert.equal(options.length, 2);

  const opencode = options.find((option) => option.id === "opencode");
  const gemini25 = options.find((option) => option.id === "gemini25");

  assert.ok(opencode);
  assert.ok(gemini25);
  assert.equal(opencode?.aliases[0], "@opencode");
  assert.ok(opencode?.aliases.includes("@金渐层"));
  assert.equal(gemini25?.aliases[0], "@gemini25");
  assert.ok(gemini25?.aliases.includes("@暹罗猫"));
  assert.equal(opencode?.desc, "gpt-5");
  assert.equal(gemini25?.desc, "google");
});
