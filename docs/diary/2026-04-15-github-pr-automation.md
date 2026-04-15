---
doc_kind: diary
created: 2026-04-15
topics: [review, github, pr, ci, imap, thread-routing]
---

# GitHub PR 自动化补齐

## 目标
补齐 Clowder 对齐计划中的 Plan 2.3：将 GitHub PR 事件自动路由到 Thread，支持审阅者分配与 CI 状态追踪。

## 实现内容

### 后端
- `src/review/thread_router.py`
  - `ThreadRouter`：将 `PREvent` 映射到现有 Thread（按 repo 名称或 `project_path` 匹配）
  - 无匹配 Thread 时自动创建，命名为 `PR Review: {repo}`
  - 根据事件类型生成格式化的系统消息（新 PR / Review / 评论 / 合并 / 关闭）

- `src/review/imap_poller.py`
  - `IMAPPoller`：轮询 IMAP 收件箱中的 GitHub 通知邮件
  - 解析邮件主题与正文，提取 PR 编号、仓库、事件类型
  - 支持启停控制与状态查询

- `src/review/ci_tracker.py`
  - `CITracker`：轮询 GitHub PR 的 CI/check 状态
  - 使用 GitHub Checks API（带 GitHub token）
  - 跟踪 `pending/success/failure/error/skipped` 五种状态
  - 状态变化时触发 handler 回调

- `src/web/routes/review.py`
  - `GET /api/review/pending` — 列出待审 PR
  - `GET /api/review/tracking/{repository:path}/{pr_number}` — 获取 PR 跟踪详情（含 CI 状态）
  - `POST /api/review/tracking/{repository:path}/{pr_number}/assign` — 分配审阅者
  - `DELETE /api/review/tracking/{repository:path}/{pr_number}` — 删除跟踪
  - `POST /api/review/webhook` — 接收 GitHub webhook 并自动路由到 Thread
  - `POST /api/review/pr` — 手动创建 PR 跟踪
  - `GET /api/review/ci/status` + `POST /api/review/ci/poll` — CI 状态与手动轮询
  - `GET/POST /api/review/imap/status|start|stop` — IMAP 控制
  - `GET /api/review/suggest-reviewers` — 根据文件路径推荐审阅者

- `src/web/app.py`
  - 初始化 `ReviewWatcher`、`ReviewRouter`、`ThreadRouter`、`CITracker`
  - 注册 `review_router`
  - lifespan 退出时停止 `ci_tracker` 与 `imap_poller`

### 前端
- `web/src/hooks/useReview.ts`
  - 封装 Review API：获取待审列表、CI 状态、分配审阅者、创建 PR、删除跟踪、轮询 CI、推荐审阅者

- `web/src/components/settings/ReviewPanel.tsx`
  - 待审 PR 列表（含状态徽章、分配、删除操作）
  - CI 状态面板（可展开查看各检查项详情与链接）
  - 刷新与手动 CI 轮询按钮
  - 分配审阅者弹窗

- `web/src/components/settings/SettingsPanel.tsx`
  - 新增 "PR 审阅" Tab（图标 `GitPullRequest`）

### 测试
- `tests/web/test_review_api.py` — 14 项断言，覆盖：
  - 空列表、创建 PR、获取跟踪、分配审阅者、删除跟踪
  - Webhook 接收、审阅者推荐、CI 状态与轮询、IMAP 状态

## 验证结果
- 后端测试：`tests/web/test_review_api.py` 14/14 passed
- Python 编译：`py_compile` 通过（无 `|` union 语法等兼容性问题）
- 前端类型检查：`tsc --noEmit` 0 错误

## 遗留/下一步
- IMAP 配置持久化（当前仅内存中生效）
- GitHub PR 自动创建（通过 GitHub API 直接发 PR）待实现
- 前端 Vitest 单元测试（ReviewPanel、useReview）待补充
