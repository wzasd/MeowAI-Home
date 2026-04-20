---
feature_ids: [mission-hub, workflow, a2a]
topics: [architecture, mission-hub, dev-integration]
doc_kind: diary
created: 2026-04-16
---

# 猫窝任务墙开发联动架构设计

## 背景
铲屎官提出：猫窝任务墙需要和实际开发过程联动，而不是一个静态看板。

## 核心设计

### Task-Thread-Session 三元组
- **MissionTask** = 开发目标
- **Thread** = 任务的专属对话上下文（自动创建）
- **Session** = 猫咪实际工作的日志（自动归集到任务下）

### 五种自动化联动
1. **新建任务 → 自动开 Thread**
2. **@猫工作 → Session 自动挂到任务**
3. **Workflow 跑完 → 任务状态自动推进**
4. **代码产出 → 自动关联 branch/commit/PR**
5. **任务阻塞 → 自动在 Thread 广播告警**

### 数据模型改动
- `MissionTask` 新增：`thread_id`, `workflow_id`, `session_ids`, `pr_url`, `branch`, `commit_hash`, `worktree_path`
- `Thread` 新增：`active_task_id`
- `SessionRecord` 已有字段（model/cli/token/cache/budget）直接复用

### 前端增强
- 任务卡片展示：会话数、总 Token、平均时延、模型/CLI 标签
- 新增「进入讨论」按钮直达任务 Thread
- 看板新增「🔥 活跃中」泳道（5 分钟内有 Session 更新的任务）
- 任务详情页展示 Session 时间线

### 实现阶段
| 阶段 | 内容 |
|------|------|
| P1 | `MissionStore` SQLite 持久化 + Task-Thread 绑定 |
| P2 | Session 自动归集 + 任务卡片展示运行时数据 |
| P3 | Workflow 执行后自动同步任务状态 |
| P4 | 代码修改自动关联到任务（git/worktree/PR）|

## 文档
详细架构文档：`docs/superpowers/plans/2026-04-16-mission-hub-dev-integration-arch.md`
