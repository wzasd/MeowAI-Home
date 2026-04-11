# MeowAI Home 下一阶段规划

**日期:** 2026-04-11
**范围:** Phase C (MCP) + Phase D (配置) + Phase E (连接器) + UI 增强

---

## 当前状态

| 阶段 | 模块 | 测试 | 状态 |
|------|------|------|------|
| Phase A (Invocation) | 5 | 97 | ✅ 完成 |
| Phase B (Session) | 3 | 61 | ✅ 完成 |
| **累计** | **8** | **158** | **1148 行代码** |

---

## 下阶段规划

### Phase C: MCP 工具系统

| 任务 | 文件 | 代码预估 | 测试 |
|------|------|----------|------|
| C1 Callback 框架 | `src/mcp/callback.py` | 300 | 10 |
| C2 核心 MCP 工具 (10个) | `src/mcp/tools/*.py` | 1800 | 35 |
| C3 Session Chain 工具 (4个) | `src/mcp/tools/session_chain.py` | 400 | 10 |

**关键工具:**
- `post_message` — 主动发消息
- `get_thread_context` — 读对话上下文
- `search_evidence` — 统一搜索
- `create_rich_block` — 富文本块
- `multi_mention` — 并行调用多猫
- `list_session_chain` — Session 列表
- `read_session_digest` — 读摘要

---

### Phase D: 配置系统升级

| 任务 | 文件 | 代码预估 | 测试 |
|------|------|----------|------|
| D1 ConfigLoader 增强 | `src/models/cat_registry.py` | 200 | 8 |
| D2 EnvRegistry | `src/config/env_registry.py` | 200 | 6 |
| D3 RuntimeCatalog | `src/config/runtime_catalog.py` | 200 | 6 |

**功能:**
- roster (角色/评估/可用性)
- reviewPolicy (跨 family 审查)
- `~/.meowai/cat-catalog.json` 运行时覆盖
- Web UI 环境变量配置

---

### Phase E: 连接器做实

| 任务 | 文件 | 代码预估 | 测试 |
|------|------|----------|------|
| E1 Connector 接口升级 | `src/connectors/base.py` | 300 | 8 |
| E2 Feishu 适配器 | `src/connectors/feishu.py` | 800 | 15 |
| E3 DingTalk 适配器 | `src/connectors/dingtalk.py` | 600 | 12 |
| E4 Weixin 适配器 | `src/connectors/weixin.py` | 600 | 10 |
| E5 WeCom Bot 适配器 | `src/connectors/wecom_bot.py` | 500 | 8 |
| E6 ConnectorRouter | `src/connectors/router.py` | 400 | 10 |
| E7 OutboundDeliveryHook | `src/connectors/outbound.py` | 300 | 7 |

**覆盖平台:**
- 飞书 (Feishu) — AI Card + 富文本
- 钉钉 (DingTalk) — Stream SDK
- 微信个人号 (iLink Bot)
- 企业微信 (WeCom)

---

### UI 功能增强

| 功能 | 文件 | 说明 |
|------|------|------|
| 猫选择器 | `web/src/components/CatSelector.tsx` | 阿橘/墨点/花花头像卡片 |
| 对话管理 | `web/src/components/ThreadPanel.tsx` | Thread 列表/新建/搜索 |
| 富文本消息 | `web/src/components/RichMessage.tsx` | 代码高亮/文件/Tool call |
| Session 状态 | `web/src/components/SessionStatus.tsx` | 状态指示器/摘要 |
| 设置页面 | `web/src/pages/Settings.tsx` | 配置编辑/主题 |
| 实时监控 | `web/src/components/MonitorPanel.tsx` | 连接/队列/指标 |

**UI 技术栈:**
- React + TypeScript
- Tailwind CSS
- WebSocket 实时通信
- 现有 Vite 构建

---

## 执行顺序

```
Phase C (MCP 工具)
  ├── C1: Callback 框架
  ├── C2: 核心工具 (10个)
  └── C3: Session Chain 工具
         │
         ▼
Phase D (配置) ───────────────────┐
  ├── D1: ConfigLoader             │
  ├── D2: EnvRegistry              │ 可并行
  └── D3: RuntimeCatalog           │
         │                         │
         ▼                         ▼
Phase E (连接器) + UI 增强 (并行)
  ├── E1-E5: 适配器实现
  ├── E6-E7: Router + Delivery
  │
  └── UI: 猫选择器 + 对话管理
      └── UI: Session 状态 + 设置
```

---

## 预估总量

| 阶段 | 代码行 | 测试数 | 工时预估 |
|------|--------|--------|----------|
| Phase C (MCP) | 2500 | 55 | 6-8h |
| Phase D (配置) | 600 | 20 | 2-3h |
| Phase E (连接器) | 3500 | 70 | 10-12h |
| UI 增强 | 1500 | 20 | 4-6h |
| **总计** | **~8100** | **~165** | **3-4 天** |

---

## 建议执行策略

### 选项 1: 顺序执行 (推荐)
C → D → E → UI
- 风险低，依赖清晰
- 每阶段完成后可验证

### 选项 2: 并行执行
- C + D 同时进行
- E + UI 同时进行
- 需要更多上下文切换

---

## 决策点

1. **Connector 优先级?**
   - 飞书 (国内用户多)
   - 钉钉 (企业用户)
   - 微信 (个人用户)

2. **UI 优先功能?**
   - 猫选择器 (高)
   - 对话管理 (高)
   - Session 状态 (中)
   - 设置页面 (中)

3. **MCP 工具优先?**
   - `post_message` + `get_thread_context` (核心)
   - `search_evidence` (需要 DB)
   - `multi_mention` (高级)

---

*规划完成，等待执行决策。*
