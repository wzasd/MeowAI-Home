# MeowAI Home

企业级多 Agent AI 协作平台 — 开源、可商用、功能完整。

---

## 功能一览

### 多 Agent 协作

多个 AI Agent 同时在线，通过 `@mention` 自由调度：

```
你: @orange 帮我实现一个排序函数
阿橘: 好的！我来写一个快速排序...

你: @inky @orange 审查一下这个实现 #ideate
墨点: 第 15 行有边界问题...
阿橘: 了解了，我修一下...
```

- **@mention 路由** — 输入 `@猫名` 即可指定 Agent 响应
- **并行模式** `#ideate` — 多个 Agent 同时给出独立意见
- **串行模式** `#execute` — Agent 按顺序接力完成任务
- **批判模式** `#critique` — 严格审查找出问题

### 三层记忆系统

Agent 拥有持久记忆，跨对话保留上下文：

| 记忆层 | 功能 | 示例 |
|--------|------|------|
| **Episodic** | 对话历史存储与检索 | "上次讨论的架构方案是什么？" |
| **Semantic** | 知识图谱，实体关系 | 记住你偏好 Python、团队用 FastAPI |
| **Procedural** | 工作流模式，经验积累 | 记住 TDD 流程的成功率 |

### 技能系统

25+ 内置技能，YAML 定义，可扩展：

| 类别 | 技能 | 说明 |
|------|------|------|
| 开发 | `#tdd` | 测试驱动开发全流程 |
| 开发 | `debugging` | 系统化排查 Bug |
| 开发 | `quality-gate` | 代码质量门禁 |
| 计划 | `writing-plans` | 结构化实施计划 |
| 协作 | `request-review` | 请求代码审查 |
| 协作 | `cross-cat-handoff` | 跨 Agent 任务交接 |
| 合并 | `merge-gate` | 合并前检查 |
| 调研 | `deep-research` | 深度调研与信息聚合 |
| MCP | `pencil-design` | 设计稿分析 |
| MCP | `browser-automation` | 浏览器自动化 |

### 多模型支持

复用已有订阅，无需额外 API Key 费用：

| Provider | 订阅模式 | 说明 |
|----------|----------|------|
| Claude (Anthropic) | Claude Max / API | 官方 CLI 子进程调用 |
| Codex (OpenAI) | ChatGPT Plus / API | 复用 Plus 订阅 |
| Gemini (Google) | Gemini Advanced / API | 复用 Advanced 订阅 |
| OpenCode | 本地模型 | 本地部署，零成本 |

### 工作流引擎

DAG 驱动的工作流，支持模板和自定义：

```
#brainstorm @orange @inky @patch 如何优化数据库查询？
→ 三只猫同时给出方案 → 汇总最佳建议

#parallel @orange 写前端 @inky 写后端
→ 两只猫并行工作 → 合并结果

@planner 设计一个完整的用户认证系统
→ 自动规划任务 → 分配给合适的 Agent
```

### 治理与安全

**铁律系统** — 4 条不可违反的规则：
- 数据安全：禁止删除非项目文件
- 进程保护：禁止执行危险系统命令
- 配置只读：核心配置不可被 Agent 修改
- 网络边界：禁止未授权的外部请求

**SOP 工作流**：
- `#tdd` — 测试驱动开发
- `#review` — 代码审查
- `#deploy` — 部署发布

### Web UI

React + FastAPI 构建，支持实时协作：

- **Thread 管理** — 多会话并行，快速切换
- **实时聊天** — WebSocket 流式输出，Markdown 渲染
- **Agent 浏览器** — 查看和配置 Agent
- **技能市场** — 浏览、安装技能
- **监控面板** — 系统状态、性能指标

### 监控与可观测性

| 能力 | 说明 |
|------|------|
| **结构化日志** | JSON 格式输出，支持查询聚合 |
| **审计日志** | 22 种事件类型，记录所有安全操作 |
| **Prometheus 指标** | 12 类指标，Grafana 直接对接 |
| **健康检查** | K8s 存活/就绪探针，自动故障恢复 |

### 多平台接入

支持通过多种平台与 Agent 对话：

| 平台 | 说明 |
|------|------|
| **飞书** | 企业办公场景 |
| **钉钉** | 企业办公场景 |
| **企业微信** | 企业办公场景 |
| **Telegram** | 国际团队 |

### 权限与认证

| 能力 | 说明 |
|------|------|
| **JWT 认证** | Token 登录，安全可靠 |
| **RBAC 权限** | admin / member / viewer 三级角色 |
| **操作审计** | 记录所有敏感操作 |

---

## 快速开始

### Homebrew（推荐）

```bash
brew tap wzasd/meowai https://github.com/wzasd/MeowAI-Home
brew install meowai
meowai start
```

打开 http://localhost:5173

### 源码安装

```bash
git clone https://github.com/wzasd/MeowAI-Home.git
cd MeowAI-Home
bash scripts/install.sh
meowai start
```

### 常用命令

```bash
meowai start          # 启动 API + Web UI
meowai dev            # 开发模式（热重载）
meowai check          # 环境检查
meowai chat           # CLI 对话模式
meowai chat --cat @sonnet  # 指定 Agent
```

启动后可用服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| Web UI | http://localhost:5173 | 前端界面 |
| API | http://localhost:8000 | 后端接口 |

---

## 使用方式

### CLI

```bash
# 启动对话
meowai chat

# 指定 Agent
meowai chat --cat @review

# Thread 管理
meowai thread list
meowai thread create "新项目"
meowai thread switch <id>
```

### Web UI

1. 打开 http://localhost:5173
2. 创建新 Thread
3. 输入消息，使用 `@猫名` 调度 Agent
4. 使用 `#标签` 触发技能或工作流

### API

```bash
# 创建 Thread
curl -X POST http://localhost:8000/api/threads \
  -H "Content-Type: application/json" \
  -d '{"name": "我的项目"}'

# 发送消息
curl -X POST http://localhost:8000/api/threads/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "@orange 你好", "role": "user"}'

# 健康检查
curl http://localhost:8000/api/monitoring/health
```

---

## 架构

```
用户 (Web/CLI/API)
    │
    ▼
FastAPI ─── WebSocket (实时推送)
    │
    ▼
A2AController ─── IntentParser ─── SkillInjector
    │
    ├─→ Agent (Claude)  ──→  CLI 子进程
    ├─→ Agent (Codex)   ──→  CLI 子进程
    └─→ Agent (Gemini)  ──→  CLI 子进程
    │
    ▼
MemoryDB ── SQLite + FTS5
    ├─ Episodic   (对话历史)
    ├─ Semantic    (知识图谱)
    └─ Procedural  (工作流模式)
```

**技术栈**：Python 3.10+ / FastAPI / React 18 / SQLite + FTS5 / WebSocket / Prometheus

---

## 项目结构

```
MeowAI-Home/
├── src/                    # Python 后端
│   ├── cli/                # CLI 命令
│   ├── collaboration/      # A2A 协作控制器
│   ├── connectors/         # 多平台接入 (飞书/钉钉/企微/Telegram)
│   ├── evolution/          # 自我进化系统
│   ├── governance/         # 铁律与治理
│   ├── memory/             # 三层记忆系统
│   ├── monitoring/         # 日志/审计/指标/健康检查
│   ├── packs/              # Pack 预配置组
│   ├── providers/          # 多模型适配器
│   ├── router/             # Agent 路由
│   ├── search/             # 向量搜索 + Hybrid RRF
│   ├── skills/             # 技能框架
│   ├── thread/             # Thread 管理
│   ├── web/                # FastAPI + WebSocket
│   └── workflow/           # DAG 工作流引擎
├── tests/                  # 测试 (721 tests)
├── skills/                 # 25 个 SKILL.md 定义
├── web/                    # React 前端
├── docs/                   # 文档与开发日记
├── ops/                    # Prometheus/Grafana 配置
├── scripts/                # 工具脚本 (install.sh)
├── Formula/                # Homebrew Formula
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MEOWAI_ENV` | 运行环境 | `development` |
| `MEOWAI_SECRET_KEY` | JWT 密钥 | 随机生成 |
| `MEOWAI_DB_PATH` | SQLite 路径 | `./meowai.db` |
| `MEOWAI_LOG_LEVEL` | 日志级别 | `INFO` |
| `MEOWAI_PORT` | API 端口 | `8000` |

---

## License

MIT
