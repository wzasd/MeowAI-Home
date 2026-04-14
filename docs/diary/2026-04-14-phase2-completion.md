# Phase 2 完成日记：执行层补齐 + 真实指标采集 + 治理持久化

**日期:** 2026-04-14

## 已完成内容

### 1. Capability Map + Permission Guard (Task 1)
- 新增 `src/collaboration/capability_map.py`
  - `CAPABILITY_TASK_MAP` 定义 capability → 任务类型映射
  - `get_task_type()` 根据 intent 推断任务类型
  - `cat_can_handle()` 检查猫咪 capabilities 是否覆盖任务
- 新增 `src/collaboration/permission_guard.py`
  - `HIGH_RISK_TOOLS` 定义高风险工具列表
  - `check_permission()` 拦截未授权的工具调用
- 测试覆盖: `tests/collaboration/test_capability_map.py` (8 项), `tests/collaboration/test_permission_guard.py` (5 项)

### 2. Provider System Prompt 注入 (Task 2)
- 修改 `src/providers/base.py` 的 `build_system_prompt()`
  - 自动注入 `capabilities` 和 `permissions` 到 system prompt
  - 让模型在 prompt 层就能感知自己的能力边界和操作权限

### 3. A2AController 集成 Capability 检查 (Task 3)
- 修改 `src/collaboration/a2a_controller.py`
  - 在 `_call_cat()` 开头插入 capability 校验
  - 若猫咪不具备对应能力，直接返回拒绝消息，不调用模型

### 4. MetricsCollector + SQLite Store (Task 4)
- 新增 `src/metrics/collector.py`
  - `InvocationRecord` dataclass 记录调用元数据
  - `MetricsCollector` 提供 `record_start()` / `record_finish()`
- 新增 `src/metrics/sqlite_store.py`
  - `MetricsSQLiteStore` 使用 `aiosqlite`
  - `invocation_metrics` 表 + 索引
  - 支持 `save()`, `list_by_cat()`, `leaderboard()`
- 测试覆盖: `tests/metrics/test_collector.py` (3 项)

### 5. A2AController 插桩 Metrics (Task 5)
- 在 `A2AController.__init__` 中初始化 `MetricsCollector`
- 在 `_call_cat()` 中:
  - 生成唯一 `invocation_id`
  - `record_start()` 在调用前记录
  - 调用结束后计算 token usage（优先从 `AgentMessage.usage` 读取，fallback 按内容字节 / 4 估算）
  - `record_finish()` 异步写入 SQLite
- metrics 失败永不阻断主流程

### 6. Metrics API (Task 6)
- 修改 `src/web/routes/metrics.py`
  - `GET /api/metrics/cats?cat_id=&days=`
  - `GET /api/metrics/leaderboard?days=`
- 新增 `tests/web/test_metrics.py` (8 项)

### 7. Governance SQLite 持久化 (Task 7)
- 修改 `src/web/routes/governance.py`
  - `GET /api/governance/projects` → 从 SQLite 读取
  - `POST /api/governance/projects` → upsert
  - `DELETE /api/governance/projects/{project_path:path}` → 删除
  - `governance_projects` 表替代内存字典
- 新增 `tests/web/test_governance.py` (10 项)

### 8. 前端 QuotaBoard / Leaderboard 真实数据 (Task 8)
- 修改 `web/src/api/client.ts`
  - 新增 `api.metrics.cat()` 和 `api.metrics.leaderboard()`
- 修改 `web/src/components/settings/QuotaBoard.tsx`
  - 按每只猫咪并行调用真实 API 聚合数据
- 修改 `web/src/components/settings/LeaderboardTab.tsx`
  - 调用真实 leaderboard API
  - 支持 7 天 / 30 天 / 全部 切换

### 9. GovernanceSettings 对接 SQLite (Task 9)
- 修改 `web/src/components/settings/GovernanceSettings.tsx`
  - 从 `api.governance.listProjects()` 加载
  - 支持新增项目 (`POST`)
  - 支持删除项目 (`DELETE`)
  - 保留"立即同步"操作

### 10. 集成验证 (Task 10)
- Phase 2 新增测试全部通过: 34 passed
- 修复 `tests/web/test_api.py` 中 Thread 创建缺少 `project_path` 的问题: 11 passed
- TypeScript 前端 `tsc --noEmit` 无错误
- 存在 7 个历史遗留 collection error（integration/scheduler/unit 中引用已移除代码）和 3 个 pre-existing A2A memory 测试失败，与 Phase 2 无关

## 提交记录
- `fc0cda2` feat: capability map + permission guard
- `72a297b` feat: real metrics collection pipeline
- `4b58868` feat: governance project list backed by SQLite
- (当前待提交) Phase 2 剩余集成: provider prompt 注入、A2A capability 拦截、前端真实数据对接
