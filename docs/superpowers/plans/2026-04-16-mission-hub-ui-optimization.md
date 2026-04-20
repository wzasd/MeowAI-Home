---
feature_ids: []
topics:
  - mission-hub
  - task-wall
  - thread-session-linkage
doc_kind: plan
created: 2026-04-16
---

# Mission Hub 任务墙优化设计

## 现状判断

当前 [MissionHubPage](/Users/wangzhao/Documents/claude_projects/catwork/web/src/components/mission/MissionHubPage.tsx:498) 更像一个「静态任务看板 + 统计中心」：

- 顶部统计、项目、工作流、功能、决议队列分成四个 tab，信息切得太散
- [TaskCard](/Users/wangzhao/Documents/claude_projects/catwork/web/src/components/mission/MissionHubPage.tsx:46) 只能表达标题 / 优先级 / owner / tags，缺少 thread / session / runtime / 代码产出
- 创建任务弹窗只支持基础字段，没有“进入讨论”“指派猫咪”“创建 thread”的入口
- 当前 `MissionTask` 数据模型也只有静态字段，见 [missions.py](/Users/wangzhao/Documents/claude_projects/catwork/src/web/routes/missions.py:19)

这导致任务墙和开发过程是断开的。任务变更无法天然联动到 thread、session、workflow，也无法反向把运行时状态抬回卡片。

## 优化目标

把任务墙从「静态看板」收敛成「开发驾驶舱」：

1. 任务卡不只显示状态，还要显示它现在挂着哪个 thread / session
2. 铲屎官在任务墙上的编辑动作，要能转成对猫猫可执行的意图
3. 任务墙是总入口，thread 是讨论现场，session 是执行证据
4. 状态变化要能双向流动

## UI 重构建议

### 1. 顶部从大统计块改成单行任务态势带

保留最有决策价值的 5 项：

- 活跃任务数
- 阻塞任务数
- 待猫响应任务数
- 活跃 thread / session 数
- 今日完成数

不要再保留「全部任务 / 已完成 / 进行中 / 阻塞 + 完成热度」这种偏报表式布局。

### 2. 主体从“状态列”升级为“任务卡 + 执行上下文”

保留 kanban，但每张卡分成三层：

1. **任务层**
   标题 / 优先级 / owner / 截止时间

2. **开发上下文层**
   `Thread` 短 ID、最近 `Session`、模型、是否有 workflow、是否有关联 PR

3. **操作层**
   `进入讨论` / `指派猫咪` / `继续执行` / `标记阻塞` / `查看代码`

这样卡片本身就能回答“这个任务现在有没有在被谁推进”。

### 3. 右侧详情抽屉替代多 tab 分裂

现在 `projects / workflows / features / resolutions` 四个 tab 把同一个任务切散了。建议改成：

- 默认主视图：任务看板
- 点击任务卡：右侧抽屉打开

抽屉包含四段：

1. 概览：任务字段、风险、owner、优先级
2. 讨论：关联 thread、最近消息、进入讨论按钮
3. 运行时：session 数、token、latency、模型/CLI、workflow 状态
4. 交付：branch、commit、PR、质量门禁结果

这比全局 tab 更符合“围绕一个任务工作”的路径。

## 数据模型建议

在 `MissionTask` 上增加以下字段：

- `threadId`
- `activeSessionId`
- `sessionIds`
- `workflowId`
- `workflowStatus`
- `branch`
- `commitHash`
- `prUrl`
- `latestModel`
- `latestCli`
- `tokenTotal`
- `avgLatencyMs`
- `lastActor`
- `updatedAt`
- `intentState`

其中 `intentState` 不是显示字段，而是“任务墙如何联动猫猫”的核心。

## 铲屎官修改任务墙后，怎么联动猫猫

不要把任务墙编辑直接翻译成“立刻命令某只猫”。应该走 **Task Intent** 机制。

### Intent 类型

- `assign_owner`
- `request_plan`
- `resume_execution`
- `mark_blocked`
- `request_review`
- `close_task`

### 联动流程

1. 铲屎官在任务墙改动任务
2. 前端把改动保存成 `task update`
3. 同时系统根据动作生成 `task intent`
4. 如果任务已有 `threadId`
   系统在对应 thread 里发一条结构化系统消息，说明这次变更
5. 如果任务没有 `threadId`
   系统先创建 thread，再把 intent 投递进去
6. 猫咪在该 thread 中开始工作，新的 session 自动归集到任务
7. 任务卡更新为 `pending / accepted / active / blocked / done`

### 示例

**场景 1：铲屎官把任务 owner 改成 `@gemini`**

- 任务字段更新
- 生成 `assign_owner` intent
- thread 中自动追加一条系统消息：
  `任务《优化状态台》已指派给 @gemini，请确认是否接手`
- 当猫咪在该 thread 开始回复并产生 session，任务状态从 `pending` 变 `active`

**场景 2：铲屎官把任务拖到 `blocked`**

- 任务字段更新
- 生成 `mark_blocked` intent
- thread 中自动广播阻塞原因模板
- 右侧状态台和任务墙都亮起阻塞告警

**场景 3：铲屎官点“继续执行”**

- 如果任务已有 thread：跳转 thread 并预填一条 resume 指令
- 如果没有 thread：先创建 thread，再发起 resume intent

## 视觉方向建议

任务墙不要继续走“多模块仪表板”路线，建议改成：

1. 单行任务态势带
2. kanban 主墙
3. 卡片上的 thread/session/runtime 轻量信息
4. 右侧任务详情抽屉

也就是：**主视图看流动，详情看证据**。

## 分阶段落地

### Phase 1

- 扩充 `MissionTask` 模型
- 任务卡支持 thread / session 基础信息
- 新建任务时可自动创建 thread

### Phase 2

- 建立 `task intent` 机制
- 铲屎官编辑任务后可把意图投递到 thread
- session 自动回写任务卡

### Phase 3

- workflow / branch / PR 回链到任务
- 右侧详情抽屉接入运行时指标

### Phase 4

- 做成真正的「任务驾驶舱」
- 任务墙、thread、状态台三者联动

## 结论

任务墙的关键，不是把卡片画得更漂亮，而是让它成为：

- 开发入口
- 执行中枢
- 状态回流面板

任务墙编辑要通过 `task intent` 联动猫猫，而不是直接把 UI 当成遥控器。这样人和猫之间的协作才可追踪、可回放、可恢复。
