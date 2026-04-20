---
feature_ids: [mission-hub, thread, a2a]
topics: [implementation, sqlite, websocket, session-binding]
doc_kind: diary
created: 2026-04-16
---

# 联动任务墙 P1 实现：Task-Thread-Session 绑定落地

## 完成内容

### 后端数据层
- 新建 `src/missions/store.py`：`MissionStore` 基于 SQLite 持久化任务数据，与 ThreadStore 共用 `~/.meowai/meowai.db`。
- 扩展 `Thread` 模型：新增 `active_task_id` 字段，支持双向绑定。
- 扩展 `SQLiteStore`：新增 `active_task_id` 列迁移，并在 save/get/list 中完整序列化/反序列化。
- `src/web/app.py` lifespan：初始化 `MissionStore` 并挂载到 `app.state.mission_store`。
- `src/web/dependencies.py`：新增 `get_mission_store` 依赖函数。

### 后端 API 改造
- 重写 `src/web/routes/missions.py`：
  - 全部接口从内存存储迁移到 `MissionStore`。
  - `POST /api/missions/tasks` 创建任务时**自动创建专属 Thread**，并设置 `thread.active_task_id = task.id`。
  - 任务更新/状态变更/删除时，自动向绑定 Thread 推送系统消息（`cat_id="system"`）。
  - 通过 WebSocket `ConnectionManager` 广播 `task_updated` / `task_deleted` 事件，让前端实时感知。
  - Pydantic 模型扩展：`thread_id`, `workflow_id`, `session_ids`, `pr_url`, `branch`, `commit_hash`, `worktree_path`, `last_activity_at`。

### A2A 会话自动归集
- `A2AController._call_cat`：当 Session 创建/更新完成后，若当前 `thread.active_task_id` 存在，则自动调用 `mission_store.bind_session()` 将会话挂到任务下。
- `ws.py`：实例化 `A2AController` 时传入 `mission_store`。
- 广播新增 `session_bound` 事件，前端可在任务卡片实时刷新会话数。

### 前端联动
- `web/src/api/client.ts`：
  - `MissionTask` 类型扩展新字段。
  - 新增 `api.missions.getTask(taskId)`。
- `web/src/hooks/useMissions.ts`：新增 `getTask` 方法。
- `web/src/components/mission/MissionHubPage.tsx`：
  - 任务卡片展示「会话数」和「进入对话」按钮。
  - 列表视图和看板视图均支持一键跳转任务 Thread。
- `web/src/App.tsx`：向 `MissionHubPage` 注入 `onOpenThread` 回调，实现从任务墙切到对话页。

### 测试
- 重写 `tests/web/test_missions_api.py`（16 例全部通过）：
  - 覆盖列表/创建/获取/更新/状态变更/删除/统计/过滤。
  - 新增断言：创建任务自动创建 Thread、系统消息推送、状态变更后 Thread 内有系统通知。

## 关键设计决策

1. **系统消息用 `assistant` 角色 + `cat_id="system"`**
   - 原因：`Message.VALID_ROLES` 只有 `user/assistant`，不引入新角色可减少存储层和前端适配成本。
   - 效果：猫咪读取 Thread 上下文时自然能看到任务变更历史。

2. **WebSocket 广播 + Thread 系统消息双通道**
   - 用户已在任务 Thread 内 → WS `task_updated` 实时刷新 UI。
   - 猫咪后续读取 Thread → 系统消息提供完整变更上下文。

3. **SQLite 同库共址**
   - Thread 和 Mission 存于同一数据库文件，保证事务一致性，避免分布式复杂度。

## 待办（P2）
- 任务卡片展示实时 Token/时延/模型标签（依赖 SessionChain API 聚合）。
- Workflow 执行完成后自动推进任务状态。
- git/worktree/PR 自动关联到任务 artifact 字段。
