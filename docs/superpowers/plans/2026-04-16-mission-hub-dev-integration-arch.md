---
feature_ids: [mission-hub, workflow, a2a, session-chain]
topics: [architecture, mission-hub, workflow-integration, task-thread-binding]
doc_kind: architecture
created: 2026-04-16
---

# 猫窝任务墙与开发过程联动架构

> 任务墙不该是静态告示板，而是能感知开发脉搏的驾驶舱。每个任务卡片都是活的——它有对话上下文、有工作日志、能自动推进状态。

## 1. 核心愿景

将 **Mission Hub** 从「手动维护的看板」升级为「开发过程的自然映射层」：

- 创建一个任务 = 开启一个专属开发对话（Thread）
- @猫咪来工作 = 为该任务产出一笔 Session 工作日志
- Workflow 跑完 = 任务状态自动收敛
- 代码修改落地 = 任务自动关联 branch / commit

## 2. 核心概念：Task-Thread-Session 三元组

```
┌─────────────────────────────────────────────────────────────┐
│  MissionTask (任务卡片)                                      │
│  ├── title / priority / status / progress                   │
│  ├── thread_id  ───────►  Thread (专属对话上下文)            │
│  ├── session_ids  ─────►  [SessionRecord] (工作日志链)       │
│  └── workflow_id  ─────►  WorkflowDAG (执行模板)             │
└─────────────────────────────────────────────────────────────┘
```

- **Task**：开发目标的最小单元，带有优先级、负责人猫、标签。
- **Thread**：任务的对话上下文。所有关于这个任务的讨论、@猫、指令都在此发生。
- **Session**：猫咪的一次实际工作 invocation。包含模型、CLI、token、时延、轮次等完整运行时数据。

## 3. 数据模型扩展

### 3.1 MissionTask 增强

```python
class MissionTask(BaseModel):
    id: str
    title: str
    description: str = ""
    status: TaskStatus = "backlog"
    priority: Priority = "P2"
    ownerCat: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    createdAt: str = ""
    dueDate: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)

    # === 新增：开发联动字段 ===
    thread_id: Optional[str] = None          # 绑定的对话线程
    workflow_id: Optional[str] = None        # 绑定的 workflow 模板
    session_ids: List[str] = []              # 关联的 session 历史
    pr_url: Optional[str] = None             # 关联的 PR
    branch: Optional[str] = None             # 关联的分支
    commit_hash: Optional[str] = None        # 最新 commit
    worktree_path: Optional[str] = None      # 关联的 git worktree
    last_activity_at: Optional[float] = None # 最后活跃时间戳
```

### 3.2 Thread 增强

```python
class Thread:
    id: str
    name: str
    messages: List[Message] = field(default_factory=list)
    current_cat_id: str = "orange"
    project_path: str = "."

    # === 新增 ===
    active_task_id: Optional[str] = None     # 当前线程聚焦的任务
```

### 3.3 SessionRecord（已扩展）

`SessionRecord` 当前已包含 `cli_command`、`default_model`、`prompt_tokens`、`completion_tokens`、`cache_read_tokens`、`cache_creation_tokens`、`budget_max_prompt`、`budget_max_context`，足以支撑任务墙展示「谁在用什么模型、花了多少 token」。

## 4. 五种自动化联动机制

### 4.1 任务创建 → 自动开 Thread

新建任务时，后端自动调用 `ThreadManager.create_thread(name=task.title)`，并将返回的 `thread_id` 写回任务。前端任务卡片出现「进入猫窝讨论」按钮，一键跳转聊天页。

### 4.2 @猫工作 → Session 自动归集

`A2AController._call_cat()` 在创建/更新 `SessionRecord` 时，检查当前 `thread.active_task_id`：

```python
if thread.active_task_id:
    task = mission_store.get(thread.active_task_id)
    if task:
        task.session_ids.append(session_id)
        task.last_activity_at = time.time()
```

任务卡片实时获得最新 Session 数据，无需手动填写进度。

### 4.3 Workflow 执行 → 任务状态联动

Workflow DAG 的每个节点（猫咪执行步骤）完成后，通过 `NodeResult` 输出状态信号。`DAGExecutor` 在整体 Workflow 结束时：

- 若 quality_gate `test_pass` 为真 → 任务自动 `doing -> done`
- 若 quality_gate `test_exists` 为假 → 任务标记 `blocked`，并写入阻塞原因
- 若节点输出包含 `#task-status: doing` 等标签 → 解析并同步任务状态

### 4.4 代码产出 → 任务自动关联

在 `A2AController` 或 `MCPExecutor` 执行代码修改（git commit / worktree create / PR create）后，通过回调将元数据写回当前任务的 `pr_url`、`branch`、`commit_hash`、`worktree_path`。

前端任务卡片可展示「已关联分支 `feature/xxx`」小标签。

### 4.5 任务状态 → 驱动开发上下文

任务被标记为 `blocked` 时：

1. 向任务绑定的 Thread 发送系统消息：「任务 `xxx` 已阻塞，原因：xxx」
2. 若阻塞原因是质量门禁失败，自动 @负责 review 的猫
3. 状态栏（RightStatusPanel）的「总览」页实时亮起阻塞告警

## 5. 前端交互设计

### 5.1 任务卡片增强

```
┌────────────────────────────────────────┐
│  P1  实现消息编辑功能        [进入讨论]  │
│  ─────────────────────────────────────  │
│  🐱 阿橘  |  claude-opus-4-6           │
│  3 次会话  ·  12.4k tok  ·  平均 320ms  │
│  ████████████████░░░░  80%             │
│  [doing]  [UI] [核心]                   │
└────────────────────────────────────────┘
```

- **进入讨论**：跳转到该任务的专属 Thread
- **模型/CLI 标签**：取自最新 Session 的 `default_model` / `cli_command`
- **会话数/Token/时延**：聚合 `session_ids` 关联的 SessionRecord
- **进度条**：可手动拖动，也可由 Workflow 质量门禁自动推进

### 5.2 看板视图新增「活跃中」泳道

在原有 `backlog/todo/doing/blocked/done` 五列基础上，增加一个横跨顶部的「🔥 活跃中」区域，展示当前 `last_activity_at` 在 5 分钟内的任务。这些任务卡片带有微光脉冲边框。

### 5.3 任务详情页 → Session 时间线

点击任务卡片进入详情页，右侧展示该任务关联的所有 Session：

- Session ID（可复制）
- 执行猫咪 + 模型
- 上传 / 下载 / 缓存 token
- 时延 + 轮次
- 状态（active / sealed）

## 6. 后端架构调整

### 6.1 新增 `MissionStore`

将 `src/web/routes/missions.py` 中的内存 dict 升级为 SQLite 持久化存储（复用 `src/thread/stores/sqlite_store.py` 的工厂模式），支持：

- `create_task(task) -> task_with_thread_id`
- `bind_session(task_id, session_id)`
- `update_artifact(task_id, branch, commit, pr_url)`
- `list_active_tasks()`

### 6.2 `A2AController` 挂载 Task 钩子

在 `_call_cat` 的 finally 块中（Session 已创建/更新后），调用 `MissionStore.bind_session()`。

### 6.3 `DAGExecutor` 挂载状态同步钩子

在 `execute()` 返回最终 `DAGResult` 后，检查绑定的 `task_id`，调用 `MissionStore.update_status_from_workflow()`。

## 7. 实现阶段

| 阶段 | 目标 | 关键文件 |
|------|------|----------|
| **P1** | 数据模型 + Task-Thread 绑定 | `missions.py`, `thread/models.py`, `MissionStore` |
| **P2** | Session 自动归集 + 任务卡片展示运行时数据 | `a2a_controller.py`, `MissionHubPage.tsx`, `SessionChainPanel` |
| **P3** | Workflow 状态联动 | `dag.py`, `dag_executor.py`, `missions.py` |
| **P4** | 代码产出关联（git branch / worktree / PR） | `mcp_executor.py`, `a2a_controller.py`, `missions.py` |

## 8. 设计取舍

- **不删除现有 missions 内存存储**：P1 先并行引入 SQLite `MissionStore`，保持 API 兼容；待验证稳定后再迁移。
- **不强求每个 Thread 都绑定任务**：普通闲聊 Thread 的 `active_task_id` 为空，不影响现有行为。
- **任务进度以手动为主、自动为辅**：Workflow 只能把任务推进到明确的门禁状态（如 done / blocked），中间进度仍允许用户手动拖拽，避免过度自动化带来的失控感。

---

**下一步建议**：从 P1 开始落地，先实现 `MissionStore` SQLite 持久化 + `MissionTask.thread_id` 绑定，然后让 gemini25 负责前端卡片增强，@opus 负责后端 Session 归集逻辑。
