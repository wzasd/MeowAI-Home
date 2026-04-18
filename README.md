# MeowAI Home

> 一个猫咪团队，为你工作。
> *Build AI teams, not just chatbots. Soft power, hard quality, shared mission.*

MeowAI Home 是多 AI Agent 协作平台。像管理团队一样管理 AI——每只猫有专长、有个性、能互相协作，而你只需要说需求。

```
你: @阿橘 写个排序函数
阿橘: 好的，这是快速排序实现...

你: @墨点 审查一下
墨点: 第 15 行边界条件有问题...

你: @阿橘 修一下
阿橘: 已修复，添加了空数组保护...
```

---

## 为什么不是单模型聊天

| | 单模型聊天 | MeowAI Home |
|---|---|---|
| 能力范围 | 一个模型的知识面 | 多模型 + 工具 + 技能的组合 |
| 协作方式 | 你和一个 AI 对话 | 你指挥团队，猫之间自动接力 |
| 任务执行 | 给建议，不执行 | 写代码、跑测试、审代码、全链路 |
| 记忆 | 当前会话 | 三层持久记忆，跨项目保留 |
| 成本 | 每个任务单独付费 | 复用已有订阅，零平台费用 |

---

## 核心能力

| 能力 | 说明 |
|------|------|
| **多猫编排** | @mention 路由，串行/并行/批判多种协作模式 |
| **A2A 通信** | 猫之间异步对话、任务交接、结构化 handoff |
| **持久身份** | 每只猫保留角色、记忆、工作风格，跨会话不换猫 |
| **跨模型 Review** | Claude 写代码，Codex 审代码，Gemini 出设计——自动闭环 |
| **技能即 SOP** | `#tdd`、`#review`、`#deploy` 触发完整工作流，不是标签 |
| **三层记忆** | Episodic（对话历史）→ Semantic（知识图谱）→ Procedural（经验模式） |
| **Mission Hub** | 功能全生命周期看板：idea → spec → 开发 → review → 发布 |
| **Signals** | AI 前沿信息流自动采集、分级、多猫协作分析 |
| **多平台接入** | Web / CLI / 飞书 / Telegram，同一团队多端同步 |
| **MCP 集成** | 工具共享、回调桥接，非 Claude 模型也能用 MCP |

---

## 四种工作模式

### 1. 直接对话
```
@阿橘 用 Python 写个 LRU Cache
```
阿橘（Claude）直接实现，带测试。

### 2. 多猫并行
```
@阿橘 @墨点 看看这个架构设计 #ideate
```
两只猫同时给出独立意见，自动汇总对比。

### 3. 串行接力
```
@阿橘 实现登录接口 → @墨点 审查 → @阿橘 修复
```
像真正的开发流程一样推进。

### 4. 技能触发
```
#tdd 写一个 URL 解析器
```
自动执行：写测试 → 写实现 → 跑测试 → 修复 → 通过。

---

## 猫团队默认成员

| 猫 | 角色 | 擅长 | 来源 |
|---|---|---|---|
| **阿橘** @dev | 开发实现 | 写代码、Debug、架构设计 | Claude |
| **墨点** @review | 代码审查 | 找 Bug、质量把关、根因分析 | Codex |
| **花花** @research | 调研设计 | 技术调研、方案对比、审美 | Gemini |

你可以添加更多猫，每只绑定不同的 Provider 和模型。

---

## 架构

三层设计：**模型层** 负责推理，**Agent 层** 负责工具与文件操作，**平台层** 负责身份、协作与审计。

```
用户 (Web / CLI / 飞书 / Telegram)
    │
    ▼
FastAPI + WebSocket ─── 实时流式输出
    │
    ▼
A2A 协作引擎 ─── Intent 解析 → 任务分发 → 猫调度
    │
    ├─→ 阿橘 (Claude)  ──→  CLI 子进程
    ├─→ 墨点 (Codex)   ──→  CLI 子进程
    └─→ 花花 (Gemini)  ──→  CLI 子进程
    │
    ▼
三层记忆 ── SQLite + FTS5
    ├─ Episodic   对话历史
    ├─ Semantic   知识图谱
    └─ Procedural 工作流模式
```

**技术栈：** Python 3.10+ / FastAPI / React 19 / SQLite + FTS5 / WebSocket

---

## 快速开始

### 前提
- Python 3.10+
- Node.js 18+
- 已有 Claude / ChatGPT / Gemini 订阅（或 API Key）

### 安装
```bash
git clone https://github.com/wzasd/MeowAI-Home.git
cd MeowAI-Home
bash scripts/install.sh
```

### 配置
```bash
cp config/cat-config.example.json config/cat-config.json
# 填入你的订阅信息
```

### 启动
```bash
meowai start
```

打开 http://localhost:3003，开始和你的猫团队协作。

---

## 项目结构

```
MeowAI-Home/
├── src/                    # Python 后端
│   ├── collaboration/      # A2A 协作引擎
│   ├── connectors/         # 多平台接入
│   ├── providers/          # 模型适配器
│   ├── memory/             # 三层记忆系统
│   ├── skills/             # 技能框架
│   ├── thread/             # Thread 管理
│   └── web/                # FastAPI + WebSocket
├── web/                    # React 19 前端
├── tests/                  # 测试
├── skills/                 # 技能定义 (YAML)
├── config/                 # 猫配置、环境配置
└── docs/                   # 文档
```

---

## License

MIT
