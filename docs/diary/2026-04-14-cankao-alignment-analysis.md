# cankao 项目对齐分析：MeowAI Home 与 clowder-ai 架构差距

**日期:** 2026-04-14

## 分析目标

完成 Phase 2 后，团队需要与 cankao 项目（clowder-ai-main / happy-main）进行能力整理拉齐，识别架构差距并制定可执行的补齐计划。

## 双方现状对比

### 1. 配置模型

| 维度 | MeowAI Home | clowder-ai |
|------|-------------|------------|
| 猫配置 | `cat-config.json` 中 `breeds` 已支持 `variants` 字段（`CatRegistry.load_from_breeds` 已扁平化），但目前 breeds 均为扁平无 variants | `cat-config.json` 中 `breeds` 有明确的 `variants` 数组，每个 variant 有 `cli.command`、`defaultModel`、`provider`、`strengths`、`contextBudget`、`mcpSupport` |
| 能力编排 | 静态 `capabilities` / `permissions` 列表，通过 `capability_map` + `permission_guard` 三层拦截 | `.cat-cafe/capabilities.json` 作为唯一真相源，支持 MCP server + skill 双类型，自动从 CLI 配置发现外部 MCP，生成 per-provider 的 `.mcp.json` / `.codex/config.toml` / `.gemini/settings.json` |
| Skill 发现 | `skills/` 目录存 SKILL.md，但未扫描、未注册、未与猫绑定 | 扫描 `cat-cafe-skills/` 和 `~/.claude/skills/` 等目录，解析 SKILL.md frontmatter 和 `manifest.yaml`，自动同步进 capabilities.json，支持挂载健康检查 |
| MCP 探测 | 无 | `probeMcpCapability()` 调用 `tools/list`，返回 connectionStatus + 工具列表，支持动态描述 |
| 治理 | SQLite `governance_projects` 表 + CRUD API，手动添加/同步 | `GovernanceBootstrapService` 自动对确认过的外部项目执行 bootstrap，首次需用户确认 |
| CLI 包装 | 无（计划中是 `neowai` CLI） | `happy` CLI 包装 claude/codex/gemini/acp，支持 daemon、session resume、远程控制 |

### 2. 代码层面已具备的基础

MeowAI Home 并非从零开始，以下模块已经为对齐打下基础：

- **`CatRegistry`** (`src/models/cat_registry.py:20-132`) 已完整支持 breed + variant 扁平化加载
- **`Capability Map + Permission Guard`** 三层执行拦截已完成（Phase 2）
- **`NestRegistry + NestConfig`** 项目级 `.neowai/` 工作空间已落地（Phase 1）
- **`MetricsCollector + SQLite Store`** 真实指标采集已跑通（Phase 2）
- **`GovernanceSettings`** 前端已实现 CRUD 和同步（Phase 2）

## 差距清单（按优先级排序）

### Gap 1: 项目级能力编排器（最高优先级）

clowder-ai 的核心竞争力是 `.cat-cafe/capabilities.json` 编排器。MeowAI Home 目前的能力是静态写在 `cat-config.json` 里的，无法做到：
- 按项目动态启用/禁用 MCP
- 自动发现外部 MCP 配置
- 为不同 provider 生成对应的 CLI 配置文件
- per-cat override

**目标:** 在 `.neowai/` 中引入 `capabilities.json`，成为项目级能力真相源。

### Gap 2: Skill 自动发现与挂载检查

MeowAI Home 的 `skills/` 目录只是文档仓库，没有与运行时的能力系统打通。

**目标:** 
- 扫描 `skills/` 和 `~/.claude/skills/` 等目录
- 解析 SKILL.md frontmatter（description、triggers）
- 将 skill 作为 `type: "skill"` 写入 `capabilities.json`
- 前端 Capability Board 展示 skill 的启用状态和触发词

### Gap 3: MCP 健康探测

目前 MeowAI Home 对 MCP server 是否可用、有哪些工具一无所知。

**目标:** 
- 实现 MCP `tools/list` 探测
- Capability Board 展示每个 MCP 的连接状态和可用工具
- 对 `pencil` 等 resolver 做本地安装检测

### Gap 4: Governance Bootstrap 服务

当前治理是手动添加项目路径后手动同步。clowder-ai 支持对外部项目自动执行治理 bootstrap。

**目标:** 
- 新增 `GovernanceBootstrapService`
- 首次同步需用户确认（防止误操作）
- 已确认项目支持后台自动同步
- 与现有 SQLite governance 表打通

### Gap 5: 多 Provider CLI 配置生成

MeowAI Home 计划推出 `neowai` CLI，但目前没有为各 provider 生成 MCP 配置的能力。

**目标:** 
- 根据 `capabilities.json` 为 anthropic/openai/google 生成各自格式的 MCP 配置文件
- 支持 streamableHttp 等传输方式的 provider 兼容性检查

### Gap 6: happy 扩展（远期）

happy-main 是面向移动远程控制的 CLI + daemon 架构。MeowAI Home 的对齐重点不是复制 happy 的移动功能，而是把以下能力通过 MCP / SDK 形式暴露给 happy：
- NeowAI nest 激活协议（`.neowai/config.json` 识别）
- 项目级 capability orchestrator 接口
- Governance bootstrap 接口

## 补齐计划（Phase 3 后续）

### Phase A: Capability Orchestrator（2-3 天）
1. 设计 `.neowai/capabilities.json` schema（兼容 clowder-ai 的 `version: 1`，但适配 MeowAI Home 的 provider 枚举）
2. 实现 `src/capabilities/orchestrator.py`：
   - `read_capabilities_config()` / `write_capabilities_config()`
   - `discover_external_mcp_servers()` — 从 `.mcp.json`、`.codex/config.toml`、`.gemini/settings.json` 读取
   - `bootstrap_capabilities()` — 首次运行自动生成
   - `resolve_servers_for_cat()` — 应用 global enabled + per-cat override + provider 兼容性
   - `generate_cli_configs()` — 写回各 provider 的 MCP 配置
3. 新增 `src/web/routes/capabilities.py`：
   - `GET /api/capabilities?project_path=&probe=` — 返回 CapabilityBoardResponse
   - `PATCH /api/capabilities` — 开关能力（global / per-cat）
4. 前端新增 `CapabilityBoard` 组件替代/增强现有 SettingsPanel 中的 capability 展示

### Phase B: Skill Discovery（1-2 天）
1. 扫描逻辑加入 orchestrator：
   - `skills/`（项目级）
   - `~/.claude/skills/`、`~/.codex/skills/`、`~/.gemini/skills/`（用户级）
2. 解析 SKILL.md frontmatter（YAML）提取 description 和 triggers
3. 同步进 `capabilities.json`（`type: "skill"`）
4. 前端 Capability Board 展示 skill 分类和触发词

### Phase C: MCP Probe（1 天）
1. 实现 `src/capabilities/mcp_probe.py`：
   - 使用 stdio 启动 MCP server
   - 发送 `tools/list` JSON-RPC 请求
   - 超时处理、错误分类
2. 在 `GET /api/capabilities?probe=true` 中集成
3. 前端根据 probe 结果展示 connectionStatus 和工具列表

### Phase D: Governance Bootstrap（1 天）
1. 实现 `src/governance/bootstrap.py`：`GovernanceBootstrapService`
2. 复用现有 `governance_projects` SQLite 表
3. 新增 API：
   - `POST /api/governance/confirm` — 首次确认并 bootstrap
   - `GET /api/governance/health` — 批量健康检查
   - `POST /api/governance/discover` — 发现未同步外部项目
4. 更新前端 `GovernanceSettings`，支持"首次确认"和"自动同步"状态

### Phase E: happy 扩展（后续）
1. 将 MeowAI Home 的 capability orchestrator 封装为 MCP server 或 HTTP API
2. 在 happy-main 中通过 ACP 调用 MeowAI Home 的能力看板
3. 把 NeowAI nest 协议作为 skill 注入 happy 的项目识别流程

## 决策与反思

**团队讨论后决定：**
- 不照搬 clowder-ai 的 `cat-cafe-*` 拆分 MCP server 设计。MeowAI Home 目前的 Web + SQLite 架构更简洁，不需要为协作/记忆/信号分别开 MCP server。
- 不复制 happy 的 daemon + 移动远程架构。MeowAI Home 的定位是个人开发者的 Web 工作台，与 happy 的"CLI 远程控制"是互补关系而非竞争。
- **核心拉齐点是：项目级能力编排器**。这是 clowder-ai 最具工程价值的部分，也是 MeowAI Home 从"静态配置"升级为"动态项目感知"的关键一步。

## 下一步行动

等待用户确认上述 Phase A-E 计划后，开始实施 Phase A（Capability Orchestrator）。
