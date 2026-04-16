# Phase A 完成日记：Capability Orchestrator（能力编排器）

**日期:** 2026-04-14

## 已完成内容

### 1. 后端模型与基础设施
- 新增 `src/capabilities/models.py`
  - `McpServerConfig` / `CatOverride` / `CapabilityEntry` / `CapabilitiesConfig` Pydantic v2 模型
  - API 模型：`CapabilityBoardItem`、`CapabilityBoardResponse`、`CapabilityPatchRequest`
- 新增 `src/capabilities/io.py`
  - `read_capabilities_config()` / `write_capabilities_config()` 原子读写 `.neowai/capabilities.json`

### 2. MCP 发现与 Bootstrap
- 新增 `src/capabilities/discovery.py`
  - 从 `.mcp.json`（Anthropic）、`.codex/config.toml`（OpenAI）、`.gemini/settings.json`（Google）读取 MCP 配置
  - 同时扫描项目级和用户级（`~/`）配置
  - `deduplicate_discovered_mcp_servers()` 按名称合并，先发现者优先
- 新增 `src/capabilities/bootstrap.py`
  - `bootstrap_capabilities()` 自动生成初始 `capabilities.json`
  - 包含内置 MeowAI MCP 占位条目（`meowai-collab`、`meowai-memory`、`meowai-signals`）

### 3. 解析器与 CLI 配置生成
- 新增 `src/capabilities/resolver.py`
  - `resolve_servers_for_cat()`：应用 global enabled → per-cat override → provider transport 兼容性过滤
  - `streamableHttp` 仅对 `anthropic` provider 启用
- 新增 `src/capabilities/cli_adapters.py`
  - `write_claude_mcp_config()` → `.mcp.json`
  - `write_codex_mcp_config()` → `.codex/config.toml`（使用 `tomli-w`）
  - `write_gemini_mcp_config()` → `.gemini/settings.json`
- 新增 `src/capabilities/orchestrator.py`
  - `get_or_bootstrap()` / `toggle_capability()` / `regenerate_cli_configs()` / `build_board_response()`

### 4. Web API
- 新增 `src/web/routes/capabilities.py`
  - `GET /api/capabilities?project_path=` — 自动 bootstrap 并返回能力看板
  - `PATCH /api/capabilities` — 全局/ per-cat 开关能力，持久化后自动重生成 CLI 配置
- 修改 `src/web/app.py` — 注册 capabilities router

### 5. 前端 CapabilityBoard
- 修改 `web/src/types/index.ts` — 新增 `CapabilityBoardItem`、`CapabilityBoardResponse`、`CapabilityPatchRequest`，并为 `ThreadDetailResponse` 补上 `project_path`
- 修改 `web/src/api/client.ts` — 新增 `api.capabilities.get()` 和 `api.capabilities.patch()`
- 新增 `web/src/components/settings/CapabilityBoard.tsx`
  - 从当前 Thread 的 `project_path` 默认填充项目路径
  - 展示 MCP / Skill 列表，支持全局开关和每只猫的 per-cat 开关
  - 参考 `GovernanceSettings` 的表格样式
- 修改 `web/src/components/settings/SettingsPanel.tsx` — `capabilities` tab 渲染 `CapabilityBoard`

### 6. 依赖与类型修复
- `pyproject.toml` 新增 `tomli>=2.0.0` 和 `tomli-w>=1.0.0`
- 顺手修复了历史遗留 TypeScript 错误：
  - `App.tsx` 移除传给 `ThreadSidebar` 的多余 `onOpenSettings`
  - `catStore.ts` 为 `Cat` 类型添加 `accountRef`
  - `GovernanceSettings.tsx` 清理未使用 import、修复 `style` 可能 undefined
  - `ConnectorSettings.tsx`、`useWebSocket.ts`、`WorkspacePanel.tsx` 清理未使用 import
  - `SignalInboxPage.tsx` 修复 `articles[0]` 类型断言

### 7. 测试
- 新增 `tests/capabilities/test_orchestrator.py` — 15 项全部通过
  - I/O 往返、MCP 发现、去重、bootstrap、resolver（global/override/transport过滤）、CLI adapters、orchestrator facade
- 新增 `tests/web/test_capabilities_api.py` — 6 项全部通过
  - GET bootstrap、GET existing、PATCH global、PATCH per-cat、404、400
- 运行 `tests/web/` + `tests/capabilities/` 联合套件：43 passed
- `tsc --noEmit` 零错误
- `py_compile` 全部通过

## 提交记录
- （当前待提交）Phase A: Capability Orchestrator 完整实现

## 下一步

按 cankao 对齐计划继续 Phase B：Skill 自动发现与挂载检查。
