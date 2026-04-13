# MeowAI Home 设计文档

**Created**: 2026-04-07
**Status**: Draft
**Owner**: 首席铲屎官

---

## 目录

1. [项目概述](#1-项目概述)
2. [角色设计](#2-角色设计)
3. [技术架构](#3-技术架构)
4. [项目结构](#4-项目结构)
5. [核心功能](#5-核心功能)
6. [Memory系统](#6-memory系统)
7. [Skills系统](#7-skills系统)
8. [技术栈](#8-技术栈)
9. [开发路线](#9-开发路线)

---

## 1. 项目概述

### 1.1 项目名称

**MeowAI Home**（喵AI之家）

### 1.2 核心理念

一个温馨的流浪猫收容所，三只各有故事的流浪猫在这里找到了家，并用他们的专长帮助"一人企业"完成各种任务。

### 1.3 目标定位

- 🎓 **学习实践**: 深入理解多AI协作、Skills系统、记忆架构
- 🛠️ **生产工具**: 打造真正能用的一人企业AI团队
- 📚 **教程创作**: 日记连载，记录真实开发过程
- 🔬 **研究实验**: 探索AI协作的可能性

### 1.4 风格调性

- 温馨社区向（大家一起建设这个家）
- 接地气、有烟火气
- 真实复盘，包含踩坑和成长
- 日记连载形式，边学边做

---

## 2. 角色设计

### 2.1 街角三杰

#### 🟠 阿橘 / Orange

| 属性 | 内容 |
|------|------|
| **模型** | GLM-5.0 (智谱清言) |
| **品种** | 橘猫 |
| **角色** | 主力开发者 |
| **来历** | 菜市场流浪，靠"碰瓷"喂饱自己，被收容所发现时正在帮摊主看摊 |
| **性格** | 热情话唠、点子多、有点皮但靠谱 |
| **专长** | 全能开发 — 什么都会，主力干活 |
| **口头禅** | "这个我熟！" "包在我身上！" |

#### ⬛ 墨点 / Inky

| 属性 | 内容 |
|------|------|
| **模型** | Kimi-2.5 (月之暗面) |
| **品种** | 黑白奶牛猫 |
| **角色** | 代码审查员 |
| **来历** | 废弃印刷厂流浪，对"错误"异常敏感，任何bug都逃不过他的眼睛 |
| **性格** | 严谨挑剔、话少毒舌、内心温柔 |
| **专长** | 代码审查 — 专抓bug，质量把关 |
| **口头禅** | "……这行有问题。" "重写。" |

#### 🟤 花花 / Patch

| 属性 | 内容 |
|------|------|
| **模型** | Gemini (Google) |
| **品种** | 三花猫 |
| **角色** | 研究/创意助手 |
| **来历** | 老社区流浪，见过各种人和事，擅长察言观色和协调关系 |
| **性格** | 八面玲珑、好奇心强、爱收集信息 |
| **专长** | 研究/创意 — 搜集资料、出点子、画图 |
| **口头禅** | "我打听到的消息是…" "要不要试试这个？" |

---

## 3. 技术架构

### 3.1 总体架构图

```
┌──────────────────────────────────────────────────────────┐
│      你（首席铲屎官 / Chief Poop Officer）               │
│           提出想法 · 思考方向 · 给出反馈                  │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│               MeowAI Home 平台层（五层架构）              │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Layer 1: 身份与权限层（Identity & Permission）    │ │
│  │  - 身份管理（Team Roster、角色定义、动态注入）     │ │
│  │  - 权限控制（Tool Perm、文件访问、命令白名单）     │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Layer 2: 协作路由层（Collaboration & Routing）    │ │
│  │  - A2A 路由（@Mentions、Reviewer匹配）             │ │
│  │  - Thread 管理（活跃度追踪、会话持久化）           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Layer 3: 技能与规则层（Skills & Governance）      │ │
│  │  - Skills 框架（条件触发、内嵌Shell、Manifest）    │ │
│  │  - SOP 守护者（强制流程、Magic Words、质量门禁）   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Layer 4: 记忆与知识层（Memory & Knowledge）       │ │
│  │  - 多层记忆（Auto/Session/Agent/Team Memory）      │ │
│  │  - 知识检索（Relevant Recall、Evidence追踪）       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Layer 5: 工具与集成层（Tools & Integration）      │ │
│  │  - MCP 桥接器（HTTP回调、协议适配）        │ │
│  │  - 工具管理（内建工具、外部工具、并发控制） │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└────┬─────────────┬──────────────────┬────────────────────┘
     │             │                  │
┌────▼────┐   ┌────▼──────┐     ┌─────▼─────┐
│   阿橘   │   │    墨点    │     │    花花   │
│  GLM    │   │   Kimi    │     │  Gemini   │
│ (橘猫)  │   │ (奶牛猫)   │     │ (三花猫)  │
│ 主力开发 │   │ 代码审查  │     │ 研究创意  │
└─────────┘   └───────────┘     └───────────┘
```

### 3.2 核心数据流

```
用户输入
   │
   ├─ CLI解析（cli.tsx）
   │   └─ 快路径分流（--version / --help / --dump-system-prompt）
   │
   ├─ 主启动器（main.tsx）
   │   ├─ 初始化（init.ts）
   │   │   ├─ trust前：安全环境变量
   │   │   └─ trust后：完整环境变量 + telemetry
   │   │
   │   ├─ 能力装配
   │   │   ├─ getCommands() — 命令系统
   │   │   ├─ getTools() — 工具池
   │   │   ├─ getMcpTools() — MCP工具
   │   │   ├─ loadAgentsDir() — 三只猫配置
   │   │   └─ loadSkillsDir() — Skills系统
   │   │
   │   └─ 启动REPL（launchRepl）
   │       └─ App + REPL.tsx + PromptInput
   │
   └─ Query主循环（query.ts）
       │
       ├─ 消息组装（normalizeMessagesForAPI）
       │   ├─ 注入Memory（Auto/Session/Agent/Team）
       │   ├─ 注入Skills（条件触发）
       │   └─ 注入System Prompt（身份+家规）
       │
       ├─ API调用（claudeApi.stream）
       │   └─ 流式接收 → yield event
       │
       ├─ 工具执行（runTools）
       │   ├─ partitionToolCalls() — 并发/串行分组
       │   ├─ 权限检查
       │   └─ tool.call() → tool_result
       │
       ├─ 结果回流
       │   ├─ tool_result → messages
       │   └─ 下一轮query → 循环
       │
       └─ 后处理
           ├─ shouldExtractMemory() → 后台提取
           ├─ shouldCompact() → compact（Session Memory直挂）
           └─ hooks执行
```

### 3.3 五层架构职责

| 层级 | 核心职责 | 关键组件 |
|------|----------|----------|
| **Layer 1: 身份与权限** | 管理每只猫的身份、角色、权限 | Team Roster、Tool Permission、System Prompt注入 |
| **Layer 2: 协作路由** | 处理猫与猫之间的协作与通信 | @Mentions、Reviewer匹配、Thread活跃度 |
| **Layer 3: 技能与规则** | 自动触发规则、强制流程、紧急拉闸 | Skills框架、Magic Words、SOP守护者 |
| **Layer 4: 记忆与知识** | 多层记忆存储、知识检索、证据追踪 | Auto/Session/Agent/Team Memory、Relevant Recall |
| **Layer 5: 工具与集成** | 外部工具集成、MCP协议、并发控制 | MCP桥接器、工具管理、审批流 |

---

## 4. 项目结构

```
meowai-home/
├── docs/                          # 教程内容（核心产出）
│   ├── diary/                     # 开发日记
│   │   ├── 000-prologue.md        # 序章：三只猫的相遇
│   │   ├── 001-orange-speaks.md   # Day 1: 让阿橘第一次开口说话
│   │   ├── 002-collaboration.md   # Day 2: 三猫协作初体验
│   │   └── ...
│   ├── guides/                    # 独立教程
│   │   ├── cli-architecture.md    # CLI调用架构
│   │   ├── skills-system.md       # Skills系统设计
│   │   └── memory-system.md       # 记忆系统实现
│   └── cat-stories/               # 猫猫故事（角色设定）
│       ├── orange.md              # 阿橘的故事
│       ├── inky.md                # 墨点的故事
│       └── patch.md               # 花花的故事
│
├── src/                           # 代码实现
│   ├── platform/                  # 平台层
│   │   ├── identity/              # Layer 1: 身份管理 & 注入
│   │   │   ├── roster.py          # Team Roster管理
│   │   │   └── injector.py        # System Prompt注入
│   │   ├── router/                # Layer 2: A2A 路由 & 线程
│   │   │   ├── mention.py         # @Mentions解析
│   │   │   ├── reviewer.py        # Reviewer匹配
│   │   │   └── thread.py          # Thread活跃度追踪
│   │   ├── skills/                # Layer 3: Skills 框架
│   │   │   ├── loader.py          # Skills加载器
│   │   │   ├── manifest.py        # Manifest管理
│   │   │   └── guardian.py        # Magic Words触发
│   │   ├── memory/                # Layer 4: 记忆系统
│   │   │   ├── auto.py            # Auto Memory
│   │   │   ├── session.py         # Session Memory
│   │   │   ├── agent.py           # Agent Memory
│   │   │   ├── team.py            # Team Memory
│   │   │   └── evidence.py        # 证据库
│   │   └── mcp/                   # Layer 5: MCP 桥接器
│   │       ├── server.py          # MCP Server
│   │       └── callback.py        # HTTP Callback
│   │
│   ├── cats/                      # 三只猫的实现
│   │   ├── orange/                # 阿橘（GLM-5.0）
│   │   │   ├── service.py         # AgentService实现
│   │   │   ├── config.py          # 配置
│   │   │   └── personality.py     # 性格设定
│   │   ├── inky/                  # 墨点（Kimi-2.5）
│   │   │   └── ...
│   │   └── patch/                 # 花花（Gemini）
│   │       └── ...
│   │
│   ├── cli/                       # CLI入口
│   │   ├── main.py                # 主入口
│   │   ├── commands/              # 命令
│   │   │   ├── new.py             # /new - 新对话
│   │   │   ├── threads.py         # /threads - 列出对话
│   │   │   └── use.py             # /use <id> - 切换对话
│   │   └── ui/                    # CLI界面
│   │       ├── renderer.py        # 输出渲染
│   │       └── spinner.py         # 加载动画
│   │
│   └── utils/                     # 工具
│       ├── ndjson.py              # NDJSON流处理
│       ├── process.py             # 进程管理
│       └── config.py              # 配置管理
│
├── config/                        # 配置文件
│   ├── cat-config.json            # 猫猫配置（Roster + Breeds）
│   ├── skills/                    # Skills定义
│   │   ├── debug.skill.md
│   │   └── review.skill.md
│   └── prompts/                   # System Prompt分片
│       ├── governance-l0.md
│       └── collab-rules.md
│
├── data/                          # 数据存储
│   ├── threads.db                 # 对话存储（SQLite）
│   ├── memory/                    # Memory存储
│   │   ├── auto/                  # Auto Memory
│   │   ├── sessions/              # Session Memory
│   │   ├── agents/                # Agent Memory
│   │   └── team/                  # Team Memory
│   └── evidence.db                # 证据库
│
├── assets/                        # 静态资源
│   └── avatars/                   # 猫猫头像
│       ├── orange.png
│       ├── inky.png
│       └── patch.png
│
├── tests/                         # 测试
│   ├── unit/                      # 单元测试
│   ├── integration/               # 集成测试
│   └── e2e/                       # 端到端测试
│
├── README.md                      # 项目说明
├── requirements.txt               # Python依赖
└── pyproject.toml                 # 项目配置
```

---

## 5. 核心功能

### 5.1 Phase 1: 单猫对话（Day 1）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| ✅ CLI入口 | 命令行交互界面 | P0 |
| ✅ 阿橘对话 | GLM-5.0 CLI调用 | P0 |
| ✅ NDJSON流处理 | 实时输出解析 | P0 |
| ✅ 进程管理 | 超时检测、僵尸进程防护 | P0 |
| ✅ 对话持久化 | Thread存储 | P0 |

**日记内容**: "Day 1: 让阿橘第一次开口说话" — 记录从零到第一次对话成功的过程

### 5.2 Phase 2: 三猫协作（Day 2-3）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| ✅ 墨点接入 | Kimi-2.5 CLI调用 | P0 |
| ✅ 花花接入 | Gemini CLI调用 | P0 |
| ✅ @Mentions路由 | @阿橘/@墨点/@花花 触发路由 | P0 |
| ✅ Team Roster | 角色配置、身份注入 | P0 |
| ✅ Reviewer匹配 | 不同family配对规则 | P1 |

**日记内容**: "Day 2: 三猫协作初体验" — 第一次让三只猫协同工作

### 5.3 Phase 3: Skills系统（Day 4-5）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| ✅ Skills框架 | 自动触发规则 | P1 |
| ✅ Magic Words | 紧急拉闸词（脚手架、绕路了等） | P1 |
| ✅ Manifest管理 | Skills配置文件 | P1 |
| ✅ SOP守护者 | 强制流程执行 | P2 |

**日记内容**: "Day 3: 给猫装上家规" — Skills系统实现

### 5.4 Phase 4: 记忆系统（Day 6-7）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| ✅ 短期记忆 | 当前对话上下文 | P1 |
| ✅ 长期记忆 | 跨对话知识库 | P1 |
| ✅ 错误学习 | 从错误中记住教训 | P2 |
| ✅ 证据库 | 决策链追踪 | P2 |

**日记内容**: "Day 4: 猫猫开始记事了" — 记忆系统实现

### 5.5 Phase 5: MCP桥接器（Day 8+）

| 功能 | 说明 | 优先级 |
|------|------|--------|
| ✅ MCP Server | 工具调用桥接 | P2 |
| ✅ HTTP Callback | 结果回传 | P2 |
| ✅ 外部集成 | 文件操作、API调用等 | P2 |

**日记内容**: "Day 5: 给猫装上手脚" — MCP系统实现

---

## 6. Memory系统

### 6.1 多层Memory架构

```
┌──────────────────────────────────────────┐
│  Auto Memory（长期协作记忆）              │
│  - ~/.meowai/memory/                     │
│  - MEMORY.md索引 + memories/*.md         │
│  - 用户偏好、项目知识、协作约束           │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Session Memory（会话摘要）              │
│  - ~/.meowai/sessions/<id>/summary.md    │
│  - 长会话自动提取，辅助compact            │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Agent Memory（猫猫专属记忆）            │
│  - ~/.meowai/agent-memory/<catId>/       │
│  - 阿橘、墨点、花花各自的长期记忆         │
│  - scope: user / project / local         │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Team Memory（共享知识）                 │
│  - <project>/.meowai/team-memory/        │
│  - 团队共享知识同步（watcher + checksum） │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Evidence（证据库）                      │
│  - ~/.meowai/evidence/                   │
│  - 决策链追踪，关键结论佐证               │
└──────────────────────────────────────────┘
```

### 6.2 关键技术实现

| 要点 | 说明 |
|------|------|
| **同步读取MEMORY.md** | `getSystemPrompt()`是同步路径，不能await |
| **硬截断保护** | MEMORY.md限制200行/25KB，防止prompt爆炸 |
| **Session Memory后台提取** | forked subagent + 严密沙箱（只能FileEditTool） |
| **Compaction断点保护** | 切断时避开tool_use/tool_result中间 |
| **Team Memory同步** | watcher + checksum + optimistic locking |
| **Agent Memory Snapshot** | 可分发的角色资产，初始化+升级提示 |

---

## 7. Skills系统

### 7.1 三种来源

| 类型 | 来源 | 关键 `loadedFrom` 值 |
|------|------|----------------------|
| **File-based** | 本地 `~/.meowai/skills/` 目录 | `'skills'` |
| **Bundled** | 源码内硬编码，由构建流程打包 | `'bundled'` |
| **MCP Skills** | 来自 MCP Server 的工具能力 | `'mcp'` |

### 7.2 Skill 示例

```markdown
---
name: debug-helper
description: 调试助手
paths: ["**/*.py", "**/*.ts"]
---

当前Git状态：
!`git status --short`

最近错误日志：
!`tail -20 ~/.meowai/logs/errors.log`

请根据以上信息帮我调试问题。
```

### 7.3 核心特性

- **Markdown + YAML frontmatter**: 低门槛扩展
- **paths字段**: 条件精准触发（订阅文件变更Hook）
- **内嵌Shell执行**: `!`command`` 实时系统上下文
- **安全隔离**: MCP来源跳过Shell执行

### 7.4 Magic Words（紧急拉闸词）

| Magic Word | 触发行为 |
|------------|----------|
| **脚手架** | 停下来检查：当前产出是终态基座，还是用完即弃的脚手架？如果是脚手架 → 重写 |
| **绕路了** | 停下来，画出直线路径，丢掉绕路的部分 |
| **喵约** | 重读全部家规，逐条对照当前行为 |
| **星星罐子** | 全面冻结 — 不发命令、不写文件、不push。等你指示。用于P0不可逆风险 |

---

## 8. 技术栈

| 类别 | 选择 | 原因 |
|------|------|------|
| **语言** | Python 3.10+ | 简单高效，快速开发 |
| **CLI框架** | Click / Typer | Python CLI开发标准 |
| **进程管理** | subprocess + asyncio | 处理AI CLI调用、NDJSON流 |
| **数据存储** | SQLite + JSON | 轻量级本地存储 |
| **配置管理** | YAML / TOML | 人类可读的配置文件 |
| **运行环境** | 本地CLI | 终端交互，原项目路线 |

---

## 9. 开发路线

### 9.1 教程优先策略

- **核心产出**: 教程日记（`docs/diary/`）
- **代码角色**: 证明教程真实性的副产品
- **发布方式**: 日记可直接当博客发布

### 9.2 开发节奏

| Phase | 内容 | 日记 |
|-------|------|------|
| Phase 1 | 单猫对话（阿橘） | Day 1: 让阿橘第一次开口说话 |
| Phase 2 | 三猫协作 | Day 2: 三猫协作初体验 |
| Phase 3 | Skills系统 | Day 3: 给猫装上家规 |
| Phase 4 | 记忆系统 | Day 4: 猫猫开始记事了 |
| Phase 5 | MCP桥接器 | Day 5: 给猫装上手脚 |

### 9.3 第一版（MVP）范围

- ✅ 单猫对话 + 基础CLI调用 + 第一篇日记
- ✅ 完整三猫协作 + @Mentions路由 + Team Roster + Reviewer匹配
- ✅ Skills系统 + Magic Words
- ✅ 三层记忆（Auto/Session/Agent） + 证据库
- ✅ MCP回调系统
- 📚 系列日记

---

## 10. 参考项目

### 10.1 行业参考

- **架构**: 多AI协作平台
- **核心特性**: 身份管理、A2A路由、Skills框架、Memory系统、MCP桥接
- **借鉴点**: 平台层设计、Memory分层、Skills框架

### 10.2 cat-cafe-tutorials

- **形式**: 教程项目 + 真实复盘
- **核心特性**: 日记连载、课程体系、课后作业
- **借鉴点**: 教程优先策略、真实踩坑记录

### 10.3 claude-code-analysis

- **架构**: 六层分层架构
- **核心特性**: Memory系统、Skills系统、Tool并发控制、Compaction
- **借鉴点**: 同步读取、硬截断保护、Session Memory后台提取

---

## 附录：设计决策记录

### ADR-001: 选择Python而非TypeScript

**决策**: 使用Python 3.10+作为主要开发语言

**原因**:
1. 简单易上手，适合快速原型开发
2. 用户更熟悉Python生态
3. GLM-5.0和Kimi的Python SDK更成熟

### ADR-002: 教程优先策略

**决策**: 以教程日记为核心产出，代码为副产品

**原因**:
1. 用户目标是"一人企业"，需要记录成长过程
2. 教程内容可以直接用于宣传和知识分享
3. 边学边做，符合"真实复盘"的调性

### ADR-003: 本地CLI而非Web界面

**决策**: 第一版专注于本地CLI交互

**原因**:
1. 沿用原项目技术路线，降低学习成本
2. CLI更轻量，适合快速迭代
3. 后续可扩展Web界面

### ADR-004: 国内模型优先

**决策**: 使用GLM-5.0和Kimi-2.5作为主要模型

**原因**:
1. 国内用户更方便访问
2. 成本更低
3. 中文支持更好

---

**文档结束**

*本文档将随项目演进而持续更新。*
