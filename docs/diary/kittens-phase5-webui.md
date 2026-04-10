# Phase 5 开发日记 — Web UI (v0.5.0)

**日期**: 2026-04-09
**角色**: 阿橘（后端）、花花（前端设计）、墨点（测试）

---

## 架构决策

### 为什么选 FastAPI + React？

阿橘："Python 后端已经是我们的技术栈，FastAPI 原生支持 async，完美对接 A2AController 的 AsyncIterator。"

花花："React + Vite + Tailwind 是现代前端的标准组合，Zustand 比 Redux 轻量，适合我们的规模。"

### 流式策略

**CatResponse 级别流式**（而非 token 级别）。原因：
- A2AController.execute() 已按 CatResponse yield
- Token 级需要重写 subprocess 层（后续优化）
- 多猫场景下，每猫完整响应依次显示，体验足够好

---

## Sub-Phase 5.1: FastAPI 后端

### 新增依赖
```toml
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
websockets>=12.0
pydantic>=2.0.0
```

### REST API
- `POST /api/threads` — 创建
- `GET /api/threads` — 列表
- `GET /api/threads/{id}` — 详情
- `PATCH /api/threads/{id}` — 重命名
- `DELETE /api/threads/{id}` — 删除
- `POST /api/threads/{id}/archive` — 归档
- `GET /api/threads/{id}/messages` — 消息历史

### WebSocket 协议
端点：`ws://host:8000/ws/{thread_id}`

客户端 → 服务端：
```json
{"type": "send_message", "content": "@dev hello"}
```

服务端 → 客户端：
```json
{"type": "message_sent", "message": {...}}
{"type": "intent_mode", "mode": "ideate"}
{"type": "cat_response", "cat_id": "orange", "cat_name": "阿橘", "content": "..."}
{"type": "done"}
```

### 代码统计
- 9 个新文件
- 11 个 API 测试

---

## Sub-Phase 5.2: React 前端骨架

### 技术栈
- **框架**: React 18 + TypeScript
- **构建**: Vite 5
- **样式**: Tailwind CSS 3
- **状态**: Zustand 4
- **图标**: Lucide React

### 目录结构
```
web/
  src/
    api/
      client.ts       — REST API 客户端
      websocket.ts    — WebSocket 管理器（含重连）
    stores/
      threadStore.ts  — Thread 列表 + 当前选中
      chatStore.ts    — 消息 + 流式状态
    hooks/
      useWebSocket.ts — WebSocket 事件处理
    components/
      thread/
        ThreadSidebar.tsx
        ThreadItem.tsx
      chat/
        ChatArea.tsx
        MessageBubble.tsx
        AgentBadge.tsx
        InputBar.tsx
        StreamingIndicator.tsx
```

### Cat 信息映射
```typescript
const CAT_INFO = {
  orange: { name: "阿橘", emoji: "🐱", color: "orange" },
  inky:   { name: "墨点", emoji: "🐾", color: "purple" },
  patch:  { name: "花花", emoji: "🌸", color: "pink" },
};
```

---

## Sub-Phase 5.3: 聊天 UI + 流式集成

### 组件交互
1. **ThreadSidebar** — 左侧会话列表，点击切换
2. **ChatArea** — 右侧聊天区域
   - 消息气泡（用户蓝色右对齐，猫白色左对齐）
   - AgentBadge 显示猫头像
   - StreamingIndicator 显示思考中的猫
3. **InputBar** — 底部输入框
   - Textarea 自动增长
   - Enter 发送，Shift+Enter 换行
   - 流式中禁用

### 事件流
```
用户输入 → InputBar dispatchEvent → useWebSocket 监听 → WS send
WS message → useWebSocket 处理 → Zustand store update → 组件重渲染
```

---

## Sub-Phase 5.4: 打磨

### 生产准备
- **CORS**: 允许 localhost:5173
- **静态文件**: FastAPI 自动提供 web/dist/
- **Vite 代理**: 开发时 /api 和 /ws 自动代理到后端
- **WebSocket 重连**: 指数退避，最大 10 次

### 开发体验
```bash
./scripts/dev.sh  # 一键启动前后端
```

---

## 测试

| 类别 | 数量 | 状态 |
|------|------|------|
| 现有测试 | 180 | ✅ 通过 |
| 新增 API 测试 | 11 | ✅ 通过 |
| **总计** | **191** | **✅ 100%** |

---

## 运行方式

### 开发模式
```bash
# 方式 1: 一键启动
./scripts/dev.sh

# 方式 2: 分别启动
python3 -m uvicorn src.web.app:create_app --factory --reload --port 8000
cd web && npm run dev
```

访问 http://localhost:5173

### 生产构建
```bash
cd web && npm run build
python3 -m uvicorn src.web.app:create_app --factory --port 8000
```

访问 http://localhost:8000

---

*Phase 5 完成！MeowAI Home 现在拥有完整的 Web UI，支持多猫实时协作。* 🎉
