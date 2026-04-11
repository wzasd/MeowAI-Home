# 对标 Clowder AI UI 完整实现计划

> **Goal:** 实现 Clowder AI 参考项目的 P1/P2 优先级功能，包含前端 UI 和后端 API。

**Scope:** P1/P2 功能（不含 P3 低优先级）

---

## Phase 1: ConnectorBubble + 连接器消息系统

### 后端 (Backend)

**Files:**
- Create: `src/web/routes/connectors_messages.py`
- Modify: `src/web/app.py`

**API Endpoints:**
- `POST /api/connectors/messages` — 接收连接器消息（飞书、微信等）
- `GET /api/connectors/messages` — 获取连接器消息列表
- `WebSocket /ws/connectors` — 实时推送连接器消息

**Data Model:**
```python
class ConnectorMessage(BaseModel):
    id: str
    connector: str  # feishu, dingtalk, weixin, etc.
    connector_type: str  # group, private
    sender: dict  # {id, name, avatar}
    content: str
    content_blocks: list[MessageBlock]  # text, image
    timestamp: int
    source_url: str | None
    icon: str  # emoji or URL
```

### 前端 (Frontend)

**Files:**
- Create: `web/src/components/chat/ConnectorBubble.tsx`
- Create: `web/src/hooks/useConnectorMessages.ts`
- Modify: `web/src/components/chat/MessageBubble.tsx` — 集成 ConnectorBubble

**ConnectorBubble 组件:**
- 连接器图标（飞书、微信、钉钉、GitHub 等）
- 消息主题色（每个连接器不同）
- 发送者信息
- 外部链接跳转
- Markdown 内容渲染
- 图片附件支持

---

## Phase 2: EvidencePanel (Hindsight) 证据检索系统

### 后端 (Backend)

**Files:**
- Create: `src/evidence/__init__.py`
- Create: `src/evidence/store.py` — SQLite 证据存储
- Create: `src/evidence/search.py` — 全文搜索
- Create: `src/web/routes/evidence.py`

**API Endpoints:**
- `GET /api/evidence/search?q={query}&limit=5` — 证据搜索
- `GET /api/evidence/status` — 证据库状态
- `POST /api/evidence/index` — 触发索引更新

**Evidence Store Schema:**
```sql
CREATE TABLE evidence_docs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    anchor TEXT,  -- 文件路径或链接
    summary TEXT,
    content TEXT,
    kind TEXT,  -- decision, plan, discussion, commit
    source TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- FTS5 虚拟表用于全文搜索
CREATE VIRTUAL TABLE evidence_fts USING fts5(title, content, content_row_id);
```

### 前端 (Frontend)

**Files:**
- Create: `web/src/components/evidence/EvidencePanel.tsx`
- Create: `web/src/components/evidence/EvidenceCard.tsx`
- Create: `web/src/hooks/useEvidence.ts`

**EvidencePanel 组件:**
- 深色主题面板
- 检索结果数量
- 降级模式提示
- EvidenceCard 列表

**EvidenceCard 组件:**
- 来源类型图标（决策、阶段、讨论、提交）
- 标题和锚点链接
- 内容摘要
- 置信度标签（高/中/低）
- 状态标签（草稿/待审/正式/归档）

---

## Phase 3: HubGovernanceTab 治理面板

### 后端 (Backend)

**Files:**
- Create: `src/governance/__init__.py`
- Create: `src/governance/pack.py` — 治理包管理
- Create: `src/web/routes/governance.py`

**API Endpoints:**
- `GET /api/governance/health` — 项目治理健康状态
- `POST /api/governance/discover` — 发现外部项目
- `POST /api/governance/confirm` — 同步治理规则

**Data Model:**
```python
class GovernanceProject(BaseModel):
    project_path: str
    status: str  # healthy, stale, missing, never-synced
    pack_version: str | None
    last_synced_at: str | None
    findings: list[GovernanceFinding]

class GovernanceFinding(BaseModel):
    rule: str
    severity: str  # error, warning, info
    message: str
```

### 前端 (Frontend)

**Files:**
- Create: `web/src/components/settings/GovernanceSettings.tsx`
- Modify: `web/src/components/settings/SettingsPanel.tsx` — 添加治理标签

**GovernanceSettings 组件:**
- 外部项目列表表格
- 状态显示（正常/过期/缺失/未同步）
- 版本信息
- 上次同步时间
- 同步操作按钮

---

## Phase 4: Mission Control 高级任务控制

### 后端 (Backend)

**Files:**
- Create: `src/web/routes/mission_control.py`

**API Endpoints:**
- `GET /api/mission-control/dispatch` — 调度状态
- `GET /api/mission-control/reflux` — Reflux 捕获队列
- `GET /api/mission-control/resolution` — 决议队列

### 前端 (Frontend)

**Files:**
- Create: `web/src/components/mission/MissionControlPage.tsx`
- Modify: `web/src/App.tsx` — 添加路由

**MissionControlPage 组件:**
- DispatchProgress — 调度进度
- RefluxCapture — Reflux 捕获
- ResolutionQueue — 决议队列

---

## Phase 5: 连接器前端面板（飞书/微信）

### 后端 (Backend)

**Files:**
- Modify: `src/web/routes/connectors.py` — 添加二维码生成端点

**API Endpoints:**
- `GET /api/connectors/{connector}/qr` — 获取绑定二维码
- `GET /api/connectors/{connector}/status` — 连接状态
- `POST /api/connectors/{connector}/unbind` — 解绑

### 前端 (Frontend)

**Files:**
- Create: `web/src/components/connectors/FeishuQrPanel.tsx`
- Create: `web/src/components/connectors/WeixinQrPanel.tsx`
- Create: `web/src/components/settings/ConnectorSettings.tsx`
- Modify: `web/src/components/settings/SettingsPanel.tsx`

**ConnectorSettings 组件:**
- 连接器列表
- 绑定状态
- 二维码展示
- 解绑按钮

---

## 实现顺序

```
Phase 1: ConnectorBubble (连接器消息系统)
  ↓
Phase 2: EvidencePanel (证据检索系统)
  ↓
Phase 3: HubGovernanceTab (治理面板)
  ↓
Phase 4: 连接器前端面板
  ↓
Phase 5: Mission Control (可选，复杂度较高)
```

---

## 预估代码量

| Phase | 后端代码 | 前端代码 | 测试 | 累计 |
|-------|---------|---------|------|------|
| Phase 1: ConnectorBubble | 400 | 350 | 20 | 750 |
| Phase 2: EvidencePanel | 600 | 400 | 25 | 1750 |
| Phase 3: Governance | 400 | 300 | 20 | 2450 |
| Phase 4: 连接器前端 | 300 | 350 | 15 | 3100 |
| Phase 5: Mission Control | 500 | 450 | 20 | 4050 |

**总计预估:** ~4000 行代码

---

## 验证清单

每个 Phase 完成后:
1. 该 Phase 的 API 测试全部通过
2. TypeScript 编译无错误
3. 前端功能在浏览器中验证
4. 端到端流程测试
