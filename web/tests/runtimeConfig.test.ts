import assert from "node:assert/strict";
import test from "node:test";

import { buildApiUrl, buildWsUrl, resolveApiBaseUrl, resolveWsBaseUrl } from "../src/api/runtimeConfig.ts";

test("api base falls back to current browser origin when env is absent", () => {
  assert.equal(resolveApiBaseUrl(undefined, "http://localhost:3003"), "http://localhost:3003");
});

test("api base trims configured env url", () => {
  assert.equal(resolveApiBaseUrl("http://localhost:3004/", "http://localhost:3003"), "http://localhost:3004");
});

test("ws base follows browser origin protocol when env is absent", () => {
  assert.equal(resolveWsBaseUrl(undefined, "https://nest.example.com"), "wss://nest.example.com");
});

test("helpers build resource urls without duplicate slashes", () => {
  assert.equal(buildApiUrl("/api/auth/me", "http://localhost:3004/"), "http://localhost:3004/api/auth/me");
  assert.equal(buildWsUrl("/ws/thread-1", "ws://localhost:3004/"), "ws://localhost:3004/ws/thread-1");
});
