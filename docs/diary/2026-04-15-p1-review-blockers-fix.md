---
date: 2026-04-15
doc_kind: diary
topics: ["review", "auth", "webhook", "limb", "tests"]
---

# P1 Review Blockers 修复完成

修复 @codex（缅因猫）在 Plan 2.4（Limb Control Plane）审查中标记的三个 P1 阻塞问题，并补充相关测试。

## 修复内容

### 1. Auth Middleware 白名单误拦截 SPA 根路径与 Review Webhook

**问题**：`AuthMiddleware` 的 `public_paths` 缺少 `"/"` 和 `"/api/review/webhook"`，导致未登录用户无法访问 SPA 登录页，GitHub webhook 投递失败。

**修复**（`src/auth/middleware.py`）：
- 将 `"/"` 与 `"/api/review/webhook"` 加入默认白名单。
- 关键调整：把 `path.startswith("/")` 改为**精确匹配** `"/"`，其余路径保持前缀匹配。避免 `"/"` 作为前缀吞掉所有受保护路由（如 `/api/threads` 等）。

### 2. Review Webhook 不支持 GitHub 原生格式

**问题**：`/api/review/webhook` 端点期望前端包装格式 `{event_type, payload, signature}`，与 GitHub 原生 webhook（`X-GitHub-Event` header + raw body）不兼容。

**修复**（`src/web/routes/review.py`）：
- 将 `receive_webhook` 改为直接读取 `Request` 对象：提取 `X-GitHub-Event`、`X-Hub-Signature-256` 和 raw body，再交给 `ReviewWatcher.handle_webhook` 处理。
- 同步更新测试（`tests/web/test_review_api.py`），按原生格式发送请求并校验 header。

### 3. 缺少 `edge-tts` 依赖导致导入失败

**问题**：`src/voice/tts_service.py` 在模块顶层 `import edge_tts`，该导入通过 `signals_router` 被 `src/web/app.py` 拉取，但 `pyproject.toml` 未声明此依赖，导致应用启动及测试收集阶段报错。

**修复**（`pyproject.toml`）：
- 在 `dependencies` 中新增 `"edge-tts>=6.1.0"`。

### 4. `review_requested` 动作未被解析

**问题**：`src/review/watcher.py` 的 `_parse_pr_event` 仅处理 `("opened", "synchronize", "closed", "reopened")`，丢弃了 `review_requested` 动作。

**修复**（`src/review/watcher.py`）：
- 在允许动作列表中增加 `"review_requested"`。
- 映射到 `PREventType.REVIEW_REQUESTED`。
- 新增测试用例 `test_webhook_review_requested` 覆盖该场景。

## 验证结果

- `tests/web/test_auth_api.py`：9/9 通过
- `tests/web/test_review_api.py`：15/15 通过（含新增 1 个）
- `tests/web/test_limbs_api.py`：17/17 通过
- 全量 web 测试（除 e2e）：265/267 通过，剩余 2 个失败为 `test_api_completion.py` 中 Workflow API 的预存在 404 问题，与本次修复无关。
- Python `py_compile` 通过。

## 下一步

请求 @codex 重新审查，确认 P1 阻塞问题已解除。
