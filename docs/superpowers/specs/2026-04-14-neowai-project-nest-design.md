---
feature_ids: []
topics: [nest, project, activation, capabilities, permissions, governance, metrics, upload]
doc_kind: spec
created: 2026-04-14
---

# NeowAI 项目激活、猫窝与执行层补齐设计

> **Status**: design-approved | **Owner**: NeowAI Core Team
> **Created**: 2026-04-14
> **Priority**: P0（项目级工作目录是后续所有功能的基础）

---

## Why

当前 MeowAI Home 存在几个相互关联的核心缺口：

1. **CLI 没有项目感**：所有 provider 子进程都跑在 server 启动目录，用户无法让猫在「目标项目」里工作。
2. **system prompt 靠临时文件/参数字符串传递**：没有利用项目本身的 `CLAUDE.md`，既不符合 Claude Code 生态习惯，也不优雅。
3. **能力/权限/治理只存不用**：UI 能切换、后端能存盘，但 A2AController 和 Provider 层完全不读取、不拦截、不执行。
4. **指标是 mock 数据**：QuotaBoard 和 Leaderboard 展示的是写死的假数据，没有真实采集管线。
5. **没有文件上传**：用户无法在对话中给猫发图片或文档，限制了使用场景。

这些缺口共同指向一个事实：**缺少「项目」这个上下文容器**。`Thread` 虽有 `project_path` 字段，但从未真正被用于驱动 CLI 的工作目录、配置隔离和文件管理。

本设计通过引入 **猫窝（Nest）** 概念，把 `.neowai/` 作为项目级工作空间，一次性补齐以上所有缺口。

---

## What

### 1. 猫窝（Nest）与项目激活

- 在项目目录下执行 `neowai`（无子命令），智能判断：
  - **未初始化** → 创建 `.neowai/` 猫窝目录，写入 `config.json`，修改/追加项目 `CLAUDE.md`
  - **已初始化** → 显示当前项目绑定的 cats 和最近状态，提示可用 `neowai web` 启动 Web UI 或 `neowai chat` 进入 CLI 对话
- Web UI 新增 **Projects** 设置 tab，可浏览、管理所有已激活的项目目录
- Thread 创建时必须选择（或默认继承上次使用的）项目目录
- 所有 provider 子进程通过 `spawn_cli(cwd=thread.project_path)` 在项目目录中运行

### 2. CLAUDE.md 改写策略

- **追加区块模式**：保留用户原有 `CLAUDE.md` 内容，在末尾追加一个 `## NeowAI Cats` 区块
- 该区块包含当前项目激活的所有 cat 的人设摘要（name、personality、role_description、capabilities、permissions）
- 后续更新只替换这个区块，不动用户其他内容
- 区块用固定的 HTML 注释标记包裹，便于精确替换：
  ```markdown
  <!-- NEOWAI-CATS-START -->
  ## NeowAI Cats
  ...
  <!-- NEOWAI-CATS-END -->
  ```

### 3. 能力/权限/治理真正生效（三层防御）

| 层级 | 机制 | 覆盖范围 |
|------|------|----------|
| **Prompt 层** | `build_system_prompt()` 注入 capabilities + permissions + iron_laws 列表 | 所有 provider |
| **Dispatch 层** | `A2AController._dispatch()` 根据任务类型匹配 cat 的 capabilities，不匹配则拒绝 | `@mention` 路由 |
| **Tool 层** | 高风险 MCP 工具执行前校验 permissions（delete_file、execute_command、git_push 等） | MCP/工具调用 |

- **Capability → 任务映射**：在 `src/collaboration/capability_map.py` 中维护映射表
- **Permission → 工具拦截**：在 `src/collaboration/permission_guard.py` 中定义高风险工具与 permission 的对应关系
- **Governance 持久化**：把 `governance.py` 的内存字典改为 SQLite 表 `governance_projects`，支持前端增删改查实际项目目录

### 4. 真实指标采集管线

- 在 `A2AController._call_cat()` 和 `_dispatch()` 的成功/失败路径插入 `MetricsCollector.record()`
- 新建 SQLite 表 `invocation_metrics`，记录：`timestamp`、`cat_id`、`thread_id`、`project_path`、`prompt_tokens`、`completion_tokens`、`success`、`duration_ms`
- Token 优先读取 CLI 返回中的 `usage`，缺失时用字节长度 `/ 4` 近似估算
- `GET /api/metrics/cats` 和 `GET /api/metrics/leaderboard` 从 SQLite 聚合真实数据
- 前端 QuotaBoard / Leaderboard 从 mock 切换为 API 数据，支持 `7d`/`30d`/`all` 筛选

### 5. 文件上传

- 文件存储路径：`.neowai/uploads/{thread_id}/{filename}`
- 单文件限制 10MB，总存储超过 100MB 时按时间淘汰旧文件
- API：
  - `POST /api/threads/{thread_id}/upload`
  - `GET /api/threads/{thread_id}/files`
  - `DELETE /api/threads/{thread_id}/files/{file_id}`
- `ThreadMessage` 新增 `attachments: List[Attachment]`，SQLite `messages` 表新增 `attachments` JSON 列
- 调用猫时，按 mime 类型处理附件：
  - 文本文件：直接读取追加到 prompt
  - 图片：支持 vision 的 provider 走 base64，不支持的先做 OCR 提取描述
  - PDF/Office：提取纯文本（优先用已有的轻量库，不引入大依赖）

### 6. Nest Config 校验与错误处理

- `.neowai/config.json` 用 Pydantic `NestConfig` model 严格校验
- **错误不阻塞启动**：当 `config.json` 存在但字段错误时，`neowai` CLI 输出错误列表 + 建议修正方案，让用户二选一：
  1. `自动修复并继续 (f)`
  2. `以默认配置继续 (d)` — 本次运行忽略坏 config，用安全默认值，不修改文件
- Web UI 读取到可修正项时，在 Projects tab 显示黄色警告 + 「一键修复」按钮，用户主动点击后才写回磁盘
- 自动修正规则：
  - `default_cat` 不在 `cats` 中 → 修正为 `cats[0]`
  - `cats` 含不存在的 cat_id → 过滤掉
  - 缺少 `version` → 填充 `1`
  - 缺少 `settings` → 填充默认值

---

## Acceptance Criteria

### 猫窝与项目激活
- [ ] 在任意项目目录执行 `neowai`，未初始化时自动生成 `.neowai/` 和 `CLAUDE.md` 区块
- [ ] 已初始化时显示项目状态，不破坏已有目录结构
- [ ] Web UI 能列出所有已激活的项目目录
- [ ] Thread 创建/切换时可选项目目录
- [ ] 调用任意猫时，`cwd` 等于该 Thread 绑定的项目目录

### CLAUDE.md
- [ ] 原有 `CLAUDE.md` 用户内容被完整保留
- [ ] `neowai` 更新 cat 配置后，只替换 `<!-- NEOWAI-CATS-START -->...<!-- NEOWAI-CATS-END -->` 区块
- [ ] 区块内包含准确的 cat 人设、capabilities、permissions

### 能力/权限/治理
- [ ] `build_system_prompt()` 输出的 prompt 中包含 capabilities 和 permissions 约束文本
- [ ] 没有 `code_review` capability 的猫被 @ 来 review 时，A2AController 直接返回拒绝消息
- [ ] 没有 `shell_exec` permission 的猫尝试调用 `execute_command` 等工具时被硬拦截
- [ ] GovernanceSettings 中的项目列表来自 SQLite，增删改查持久化，重启不丢失

### 指标
- [ ] 每次猫调用后 `invocation_metrics` 表新增一条记录
- [ ] QuotaBoard 展示真实累计 token / 调用次数 / 成功率（非 mock）
- [ ] Leaderboard 按真实数据计算排名，支持时间范围切换

### 文件上传
- [ ] 前端支持拖拽/点击上传文件到当前 Thread
- [ ] 上传文件保存在 `.neowai/uploads/{thread_id}/`
- [ ] 带附件的消息能被 cat 正确读取内容并回复
- [ ] 总存储超限时自动清理最旧的文件

### Config 健壮性
- [ ] `.neowai/config.json` 字段错误时，`neowai` CLI 能启动并给出明确的修复提示
- [ ] Web UI 对错误 config 显示警告横幅和一键修复按钮
- [ ] 用户未确认前，不静默修改 config 文件

---

## Architecture

### 新增/修改模块

```
src/
├── cli/
│   ├── nest_init.py           # neowai 无参数时的智能初始化/状态显示
│   └── claude_md_writer.py    # CLAUDE.md 区块读写
├── config/
│   ├── nest_config.py         # NestConfig Pydantic model + 读写 + 校验 + 自动修正
│   └── nest_registry.py       # 全局已激活项目目录索引（~/.meowai/nest-index.json）
├── collaboration/
│   ├── capability_map.py      # capability -> 任务类型映射
│   ├── permission_guard.py    # 高风险工具 permission 硬拦截
│   └── a2a_controller.py      # 注入 capability 检查 + metrics 采集点
├── providers/
│   ├── base.py                # build_system_prompt() 注入 capabilities/permissions
│   ├── claude_provider.py     # 传入 cwd
│   ├── codex_provider.py      # 传入 cwd
│   ├── gemini_provider.py     # 传入 cwd
│   └── opencode_provider.py   # 传入 cwd
├── metrics/
│   ├── collector.py           # MetricsCollector 接口
│   └── sqlite_store.py        # invocation_metrics 表操作
├── web/
│   └── routes/
│       ├── projects.py        # 项目列表、NestConfig 读写
│       ├── uploads.py         # 文件上传 API
│       └── governance.py      # 改为 SQLite 持久化
└── utils/
    └── cli_spawn.py           # 所有 provider 传入 cwd

web/src/components/settings/
├── ProjectSettings.tsx        # Projects tab
└── (existing files)           # QuotaBoard/Leaderboard/Governance 切换真实数据
```

### 核心数据流：Thread → Project → CLI Spawn

```
User sends message in Thread
    │
    ▼
A2AController receives message
    │
    ├── read thread.project_path  ──►  NestRegistry validates project is active
    │
    ├── check cat capabilities against task type
    │       (reject if mismatch)
    │
    ├── build system prompt (inject caps/perms/iron laws)
    │
    ├── read attachments from .neowai/uploads/{thread_id}/
    │       (append to prompt)
    │
    ├── MetricsCollector.record_start()
    │
    ▼
Provider.invoke(cwd=thread.project_path)
    │
    ▼
spawn_cli(..., cwd=project_path)
    │
    ▼
Claude/Codex/Gemini runs inside the project directory
```

### 数据模型

#### `invocation_metrics` (SQLite)
```sql
CREATE TABLE invocation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    cat_id TEXT NOT NULL,
    thread_id TEXT,
    project_path TEXT,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    success INTEGER DEFAULT 1,
    duration_ms INTEGER DEFAULT 0
);
CREATE INDEX idx_metrics_cat ON invocation_metrics(cat_id);
CREATE INDEX idx_metrics_project ON invocation_metrics(project_path);
CREATE INDEX idx_metrics_time ON invocation_metrics(timestamp);
```

#### `governance_projects` (SQLite)
```sql
CREATE TABLE governance_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'healthy',
    version TEXT,
    findings TEXT,          -- JSON array
    synced_at REAL,
    confirmed INTEGER DEFAULT 0
);
```

#### `messages` 表变更
```sql
ALTER TABLE messages ADD COLUMN attachments TEXT DEFAULT '[]';
-- 存储 JSON array of Attachment objects
```

#### `.neowai/config.json` 结构
```json
{
  "version": 1,
  "project_name": "my-app",
  "activated_at": "2026-04-14T10:00:00Z",
  "default_cat": "orange",
  "cats": ["orange", "inky", "patch"],
  "settings": {
    "auto_sync_claude_md": true,
    "collect_metrics": true
  }
}
```

#### `~/.meowai/nest-index.json` 结构
```json
{
  "version": 1,
  "projects": [
    {
      "path": "/Users/wangzhao/Documents/my-app",
      "activated_at": "2026-04-14T10:00:00Z",
      "last_used_at": "2026-04-14T12:00:00Z"
    }
  ]
}
```

---

## Error Handling & Resilience

### Config 错误（核心原则：不阻塞启动）

| 场景 | CLI 行为 | Web UI 行为 |
|------|----------|-------------|
| `config.json` 不存在 | 自动初始化 | 显示「未激活」状态 |
| `config.json` 存在但格式错误 | 打印诊断 + 提示 `(f)ix/(d)efault`，用户选择后继续 | 显示警告横幅 + 「一键修复」按钮 |
| `config.json` 中 cat_id 不存在于 registry | 过滤非法项并提示 | 修复后刷新猫列表 |

### CLAUDE.md 写入失败

- 若项目目录只读或 `CLAUDE.md` 被锁定，`neowai init` 给出警告但**不阻塞激活**
- 降级到临时文件传递 system prompt（保留旧路径作为 fallback）
- Web UI 显示「CLAUDE.md 写入失败，当前使用临时 system prompt」提示

### 文件上传超限

- 单文件 > 10MB → API 返回 `413 Payload Too Large`
- 总存储 > 100MB → 在上传新文件前自动删除最旧的 20% 文件，并返回 `warning: storage_pruned`

### 指标采集失败

- `MetricsCollector` 内部捕获所有异常并记录 warning log
- 采集失败**绝不**影响主调用流程和返回给前端的结果

---

## Dependencies

- 后端：现有 FastAPI + SQLite 基础设施
- 前端：现有 React + Zustand + Tailwind 组件体系
- 新增 Python 依赖：**无**（用标准库 `json` + `pathlib` + 现有 Pydantic/FastAPI）
- 可选依赖：`pymupdf` 用于 PDF 文本提取（如未来需要；第一阶段可用纯文本 fallback）

---

## Risk & Mitigation

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 改造 `A2AController` 引入 regression | 高 | 所有改动点增加单元测试；保留旧逻辑 fallback 开关 |
| `CLAUDE.md` 区块替换误伤用户内容 | 中 | 用固定注释标记包裹区块；写前备份原文件到 `.neowai/CLAUDE.md.bak` |
| 多项目并发时 `cwd` 切换引入竞态 | 低 | 每个 CLI spawn 独立传入 `cwd`，不修改全局 `os.chdir()` |
| 文件上传带来存储爆炸 | 中 | 单文件 10MB + 总存储 100MB + 自动淘汰 |

---

## Timeline

建议分 3 个实现阶段：

1. **Phase 1: 猫窝 + CLAUDE.md + cwd 切换**（1-2 天）
   - `neowai` 智能初始化、NestConfig、NestRegistry、CLAUDE.md 区块读写
   - provider `cwd` 透传、Thread `project_path` 必填

2. **Phase 2: 执行层 + 指标 + 治理持久化**（2-3 天）
   - capability_map、permission_guard、A2AController 三层防御
   - MetricsCollector + SQLite 表 + API 改造
   - Governance SQLite 持久化

3. **Phase 3: 文件上传 + 前端整合**（1-2 天）
   - 上传 API、前端拖拽组件、附件消息渲染
   - QuotaBoard / Leaderboard 切换真实数据
