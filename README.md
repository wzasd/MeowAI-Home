# MeowAI Home

> 一个猫咪团队，为你工作。

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

## 为什么用 MeowAI Home

**不是聊天机器人，是团队。**

| | 单模型聊天 | MeowAI Home |
|---|---|---|
| 能力范围 | 一个模型的知识面 | 多个模型 + 工具 + 技能的组合 |
| 协作方式 | 你和一个 AI 对话 | 你指挥一个团队，猫之间自动协作 |
| 任务执行 | 给建议，不执行 | 写代码、跑测试、审代码、全链路 |
| 记忆 | 当前会话 | 三层持久记忆，跨项目保留 |
| 成本 | 每个任务单独付费 | 复用已有订阅，零额外费用 |

**核心设计：**
- **猫是 Agent，不是 API** — 每只猫有角色、能力和记忆，不是简单的模型切换
- **@mention 路由** — 像 Slack 一样 @猫，猫之间也能互相 @ 接力
- **技能即工作流** — `#tdd`、`#review`、`#deploy` 不是标签，是完整 SOP

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

### 配置你的猫

```bash
# 编辑猫咪配置
cp config/cat-config.example.json config/cat-config.json
# 填入你的订阅信息
```

### 启动

```bash
meowai start
```

打开 http://localhost:5173，开始和你的猫团队协作。

---

## 怎么和猫团队工作

### 1. 直接对话

```
@阿橘 用 Python 写个 LRU Cache
```

阿橘（Claude）直接给你实现。

### 2. 多猫协作

```
@阿橘 @墨点 看看这个架构设计 #ideate
```

两只猫同时给出独立意见，自动汇总。

### 3. 串行接力

```
@阿橘 实现登录接口 → @墨点 审查 → @阿橘 修复
```

阿橘实现，墨点审查，阿橘修复——像真正的开发流程。

### 4. 触发技能

```
#tdd 写一个 URL 解析器
```

自动执行：写测试 → 写实现 → 跑测试 → 修复 → 通过。

---

## 猫团队默认成员

| 猫 | 角色 | 擅长 | 来源 |
|---|---|---|---|
| **阿橘** @dev | 开发实现 | 写代码、Debug、架构 | Claude |
| **墨点** @review | 代码审查 | 找 Bug、质量把关 | Codex |
| **花花** @research | 调研设计 | 技术调研、方案对比 | Gemini |

你可以添加更多猫，每只猫绑定不同的 Provider 和模型。

---

## 技术架构

```
用户 (Web / CLI / 飞书 / 钉钉 / Telegram)
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

## 项目结构

```
MeowAI-Home/
├── src/                    # Python 后端
│   ├── collaboration/      # A2A 协作引擎
│   ├── connectors/         # 多平台接入
│   ├── providers/          # 模型适配器 (Claude/Codex/Gemini/OpenCode)
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
