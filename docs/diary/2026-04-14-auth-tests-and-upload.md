# 2026-04-14 Auth 测试修复与文件上传功能收尾

## 今日工作

### 1. Web 测试套件修复 (AuthMiddleware 回归)

全局 `AuthMiddleware` 引入后，大量 Web 测试因 401 未认证或 SQLite database lock 而失败。经过排查和修复：

**问题根因:**
- `TestClient` 触发生命周期，但 `AsyncClient` + `ASGITransport` 默认不触发生命周期，导致 `app.state.auth_store` 缺失
- 多个 `TestClient` fixture 共用默认 SQLite 路径 `~/.meowai/meowai.db`，且 `AuthStore` 持有持久连接，造成 `sqlite3.OperationalError: database is locked`
- 历史会话中残留大量僵尸 pytest 进程，进一步加剧锁竞争

**修复措施:**
- 为 6 个 Web 测试文件（signals、missions、connectors_binding、connectors_messages、evidence 等）的 `client` fixture 增加自动注册/登录逻辑，注入 `Authorization: Bearer <token>`
- `test_account_e2e.py` 的 async 测试手动初始化 `AuthStore` 并注入 `app.state`
- `test_account_e2e.py::test_cat_response_includes_account_ref` 改用同步 `TestClient` 以触发 lifespan 初始化的 `cat_registry`
- `src/web/app.py` lifespan shutdown 中增加 `await app.state.auth_store.close()`，确保连接释放
- 清理了系统中累积的 40+ 僵尸 pytest 进程

**验证结果:**
- `tests/web/test_account_e2e.py` — 4 passed
- `tests/web/test_uploads.py` — 5 passed
- `tests/collaboration/test_mcp_tools.py` — 7 passed (含 `read_uploaded_file`)

### 2. 文件上传功能完整收尾

基于 `docs/superpowers/plans/agile-munching-firefly.md` 的计划，完成了端到端文件上传能力：

**后端:**
- `POST /api/threads/{thread_id}/uploads` — 接收 multipart，存储到 `{project_path}/.meowai/uploads/{thread_id}/{filename}`，限制 10MB，过滤路径穿越
- `GET /api/threads/{thread_id}/uploads/{filename}` — 提供文件下载，带路径安全检查
- WebSocket `send_message` 解析 `attachments` 数组并写入 `Message.metadata`
- MCP 工具 `read_uploaded_file` 注册到 `TOOL_REGISTRY`，Agent 可直接读取附件内容
- SQLite `messages` 表已支持 `metadata TEXT` 列

**前端:**
- 新建 `FileUpload.tsx` — 文件选择、上传进度、附件 chip 预览
- `InputBar.tsx` 集成文件上传按钮，支持发送前预览和删除附件
- `MessageBubble.tsx` 在用户消息气泡中渲染附件列表（可点击下载）
- `api/client.ts` 增加 `api.uploads.upload()`
- `websocket.ts` 与 `useWebSocket.ts` 支持传递 `attachments` 到 WebSocket

**测试:**
- `tests/web/test_uploads.py` — 覆盖正常上传、路径穿越、超大文件、下载成功、下载路径穿越
- `tests/collaboration/test_mcp_tools.py::test_read_uploaded_file` — 覆盖读取成功与路径 traversal 拦截
- 前端 `npm run typecheck` 通过

### 3. ROADMAP 更新

将 Phase 5.3 "文件上传" 从 ❌ 待实现 更新为 ✅ 已完成，以反映实际代码状态。

## 待办

- TTS 语音合成 (P2)
- Vision API 图片理解 (P2)
