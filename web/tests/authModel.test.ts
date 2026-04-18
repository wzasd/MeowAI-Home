import assert from "node:assert/strict";
import test from "node:test";

import { getAuthInitErrorMessage, shouldResetStoredSession } from "../src/stores/authModel.ts";

test("auth session resets only on explicit unauthorized responses", () => {
  assert.equal(shouldResetStoredSession({ status: 401 }), true);
  assert.equal(shouldResetStoredSession({ status: 403 }), true);
  assert.equal(shouldResetStoredSession({ status: 500 }), false);
  assert.equal(shouldResetStoredSession(new Error("Network Error")), false);
});

test("auth init error keeps the original message when available", () => {
  assert.equal(getAuthInitErrorMessage(new Error("无法连接到服务")), "无法连接到服务");
  assert.equal(getAuthInitErrorMessage({}), "登录状态校验失败，请检查服务连接");
});
