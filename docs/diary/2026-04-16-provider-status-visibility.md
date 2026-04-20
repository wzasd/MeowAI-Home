---
date: 2026-04-16
doc_kind: diary
topics: ["provider", "streaming", "cli", "websocket", "status"]
---

# Provider CLI 过程态可见性增强

在 Terminal 流式化改造完成后，继续解决"调用 CLI 时看不到中间状态"的问题：Claude/Codex 等 Provider 在调用 CLI 子进程时，前端只能看到最终生成的文本，看不到 `system` 过程事件。

## 问题根因

- `src/providers/claude_provider.py:55` 明确跳过 `type == "system"` 的 NDJSON 事件。
- `a2a_controller.py` 的 `_call_cat` 只处理 `TEXT`、`THINKING`、`DONE`、`USAGE`，没有状态透传通道。
- 前端 `ChatArea` 的流式响应区域只能展示 `content` 和 `thinking`，没有状态提示区。

## 改动内容

### 后端

1. **新增 `AgentMessageType.STATUS`**（`src/models/types.py`）
   - 专门用于承载 CLI 的过程态/系统提示。

2. **Provider 映射 `system` 事件为 `STATUS`**
   - `claude_provider.py`：不再丢弃 `system`，而是生成 `AgentMessageType.STATUS`。
   - `codex_provider.py` / `opencode_provider.py`：增加 `else` 兜底分支，把未知/过程事件也映射为 `STATUS`。

3. **A2AController 广播 `cat_status`**（`src/collaboration/a2a_controller.py`）
   - `_call_cat` 中消费 `STATUS` 消息后，通过已有的 `broadcast_callback` 向线程 websocket 广播：
     ```json
     {"type": "cat_status", "cat_id": "...", "cat_name": "...", "content": "..."}
     ```

### 前端

1. **chatStore 增加 `streamingStatuses`**（`web/src/stores/chatStore.ts`）
   - `Map<string, string>` 存储每个 cat 的当前状态文本。

2. **useWebSocket 订阅 `cat_status`**（`web/src/hooks/useWebSocket.ts`）
   - 收到事件后调用 `setStreamingStatus`。

3. **ChatArea 渲染状态提示**（`web/src/components/chat/ChatArea.tsx`）
   - 在流式消息气泡上方增加一条轻量状态条：琥珀色脉冲点 + 状态文本（如 "Starting..."、"tool_running" 等）。

## 验证结果

- Python `py_compile` 通过。
- 前端 `tsc --noEmit` 通过。
- `tests/web/test_workspace_api.py` 25 passed（原有回归未破坏）。
- 全量 pytest 中，与本次改动相关的 collaboration / web 测试全部通过；其余失败/错误为历史遗留（benchmark、e2e fixture 缺失、metrics 重复注册等）。

## 效果

用户在聊天窗口中 @猫 后，如果底层 Claude CLI 输出了 `system` 事件（如启动中、session 恢复、hook 执行等），前端流式区域会实时显示状态提示，不再像"突然想了很久然后一下子吐字"。
