# Phase D: Governance Bootstrap

## 完成内容

### 后端

- 新建 `src/governance/bootstrap.py`
  - `GovernanceBootstrapService`：执行真实项目激活与健康检查
    - `bootstrap(project_path)`：完整启动流程
      1. 检查项目路径是否存在
      2. 确保 `.neowai/config.json`（nest config）存在，通过 `load_nest_config` 自动创建/修复
      3. 将项目注册到 `NestRegistry`（`~/.meowai/nest-index.json`）
      4. 调用 `get_or_bootstrap_capabilities()` 生成/同步 `capabilities.json`
      5. 运行健康检查并生成 `GovernanceFinding` 列表
      6. 返回 `BootstrapResult`（含 `status`、`findings`、`confirmed`）
    - `health_check(project_path)`：轻量健康检查，不重新触发 capabilities bootstrap
    - 错误分类：`healthy`、`stale`、`missing`、`error`
- `src/web/routes/governance.py`
  - `POST /confirm` 现在执行真实 bootstrap（替代之前的仅写 DB 假数据）
  - `GET /health` 现在遍历所有项目，调用 `health_check()` 刷新状态并回写 SQLite
  - 新增 `POST /sync`：对已 confirmed 项目执行轻量同步，更新 findings 与状态

### 前端

- `web/src/api/client.ts`
  - `api.governance.syncProject(projectPath)` 调用 `POST /api/governance/sync`
- `web/src/components/settings/GovernanceSettings.tsx`
  - 表格移除单独的"版本"列，改为在状态列下方展示 findings 详情
  - 未激活项目（`confirmed: false`）显示"激活"按钮（绿色 `Zap` 图标）
  - 已激活项目显示"同步"按钮（蓝色 `RefreshCw` 图标）
  - Findings 按 severity 着色：error 红色、warning 琥珀色、info 灰色
  - 新增 `error` 状态的样式支持

### 测试

- 新建 `tests/governance/test_bootstrap.py`
  - `test_bootstrap_missing_project` — 缺失路径返回 `missing`
  - `test_bootstrap_creates_nest_config_and_capabilities` — 自动创建 `.neowai/` 下文件
  - `test_bootstrap_registers_in_nest_index` — nest registry 正确记录
  - `test_bootstrap_preserves_existing_capabilities` — 不覆盖已有配置
  - `test_health_check_missing_project` / `test_health_check_existing_project`
  - `test_bootstrap_findings_include_nest_info`
- `tests/web/test_governance.py`
  - `test_confirm_bootstraps_real_project` — 验证 `POST /confirm` 产生真实 findings
  - `test_sync_updates_existing_project` — 验证 `POST /sync` 成功刷新
  - `test_confirm_missing_project_returns_missing` — 缺失项目返回 missing 状态
  - `test_health_refreshes_all_projects` — `GET /health` 刷新项目状态

## 验证结果

- Python 测试：223/223 通过（capabilities 38 + governance 25 + web 其他 160）
- 前端 TypeScript：`tsc --noEmit` 零错误
