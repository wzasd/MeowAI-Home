# Send Dock 乐观更新 + 队列接力修复

## 变更

### Send Dock 合入 InputBar
- 删除 `InlineQueuePanel.tsx`，逻辑合并到 `InputBar.tsx`
- Send Dock（状态栏 + hero 卡 + 叠纸边）在 `nest-panel` 内部、标签栏上方渲染
- 队列非空时自动展示，空时消失
- dark mode 适配：所有硬编码白底改为 CSS 变量 + dark: 前缀

### 乐观 UI 更新
- `chatStore` 新增 `addQueueEntry` action，支持追加单条而不替换整个数组
- `InputBar.handleSend` 在 `deliveryMode === "queue"` 时，发送 WS 消息前立即插入本地条目
- 本地条目使用 `local-${Date.now()}` 临时 ID，后端 `queue_updated` 事件会替换整个列表
- 用户点击"放入发件夹"后 Send Dock 立即出现，无需等待后端确认

### 队列状态修复
- `queued` 过滤条件从 `status === "queued"` 改为 `status === "queued" || status === "processing"`
- hero 卡在 processing 状态显示"正在送达..."而非"等 X 回复后自动送达"

### 后端队列路由修复
- `deliveryMode == "queue"` 无条件入队（之前只在有活跃猫时才入队）
- 无活跃猫时立即出队执行（避免消息卡在队列里）
- 自动出队时广播 `streaming_start` 事件，前端保持 `isStreaming` 状态

### streaming_start 事件
- `ws.py` 在自动出队执行前广播 `streaming_start`
- `useWebSocket.ts` 新增 `streaming_start` handler，调用 `startStreaming()`
- 解决队列接力时前端不知道下一只猫已开始的问题

## 文件
- `web/src/components/chat/InputBar.tsx` — Send Dock UI + 乐观更新
- `web/src/components/chat/InlineQueuePanel.tsx` — 已删除
- `web/src/components/chat/ChatArea.tsx` — 移除 InlineQueuePanel 引用
- `web/src/stores/chatStore.ts` — 新增 addQueueEntry action
- `web/src/hooks/useWebSocket.ts` — streaming_start handler
- `src/web/routes/ws.py` — 队列路由修复 + streaming_start 广播