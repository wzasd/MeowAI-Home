# Kittens 开发日记 — Phase 4: Signal 与 Mission 真实数据 (2026-04-11)

## 目标
完成 MeowAI Home 前端所有 Mock 数据替换为真实后端 API。

## 已完成任务

### Task #166: SignalInboxPage 真实数据

**新增后端模块:**
- `src/web/routes/signals.py` — 7 个 API 端点:
  - `GET /api/signals/articles` — 文章列表（支持 status/tier 过滤）
  - `GET /api/signals/articles/search` — 全文搜索
  - `GET /api/signals/articles/{id}` — 获取单篇文章
  - `PATCH /api/signals/articles/{id}/status` — 更新状态
  - `POST /api/signals/articles/{id}/star` — 收藏文章
  - `GET /api/signals/sources` — 来源列表
  - `POST /api/signals/sources/{id}/refresh` — 刷新来源

**前端更新:**
- `web/src/hooks/useSignals.ts` — 新增 hook，支持:
  - 文章列表获取与搜索
  - 状态更新、收藏
  - 来源刷新
  - 自动错误处理
- `web/src/components/signals/SignalInboxPage.tsx` — 完全重写:
  - 使用真实 API 数据
  - 添加加载状态
  - 未读文章自动标记
  - 错误提示与重试

### Task #165: MissionHubPage 真实数据

**新增后端模块:**
- `src/web/routes/missions.py` — 6 个 API 端点:
  - `GET /api/missions/tasks` — 任务列表（支持 priority/status 过滤）
  - `POST /api/missions/tasks` — 创建任务
  - `GET /api/missions/tasks/{id}` — 获取单个任务
  - `PATCH /api/missions/tasks/{id}` — 更新任务
  - `POST /api/missions/tasks/{id}/status` — 更新状态
  - `DELETE /api/missions/tasks/{id}` — 删除任务
  - `GET /api/missions/stats` — 任务统计

**前端更新:**
- `web/src/hooks/useMissions.ts` — 新增 hook，支持:
  - 任务 CRUD 操作
  - 状态快速切换
  - 统计信息获取
  - 优先级过滤
- `web/src/components/mission/MissionHubPage.tsx` — 完全重写:
  - 真实数据驱动看板
  - 新建任务模态框
  - 状态快捷操作（点击图标切换）
  - 实时统计条
  - 加载与错误处理

**路由注册:**
- `src/web/app.py` — 添加 missions 和 signals 路由

## 代码量变化
- 新增后端代码: ~500 行
- 新增前端 hook: ~400 行
- 重写组件: ~700 行
- 删除 mock 数据: ~150 行

## Mock 数据清理状态
所有 10 个组件的 mock 数据已替换完成:

| 组件 | 状态 |
|------|------|
| WorkspacePanel | 真实数据 (Git Worktree) |
| QueuePanel | 真实数据 |
| TaskPanel | 真实数据 |
| TokenUsagePanel | 真实数据 |
| AuditPanel | 真实数据 |
| QuotaBoard | 真实数据 |
| LeaderboardTab | 真实数据 |
| HistorySearchModal | 真实数据 |
| SignalInboxPage | 真实数据 |
| MissionHubPage | 真实数据 |

## 下一步
Phase 4 完成，可考虑进入 Phase 5:
- 连接器做实 (Feishu/DingTalk/WeChat)
- 调度系统 (定时任务)
- Limb 远程控制
