---
date: 2026-04-21
doc_kind: diary
topics: ["tool", "chat", "streaming", "ui", "ux"]
---

# Tool Visibility Rail 设计交付

今天把“Tool 使用时要可见”这件事收成了一版独立设计稿，重点不是给聊天区再塞一个状态面板，而是把 Tool 过程做成贴着回复气泡长出来的工具轨。

这版定义了三件关键事：

- **Primary Tool Card**：当前正在跑的 Tool 单独成卡，展示工具名、参数摘要、运行状态和结果文案
- **Recent Chips**：最近完成的 Tool 压缩成胶囊，不把界面拉回调试日志
- **Final Audit Stub**：回复完成后保留“本轮用了几个工具”的折叠摘要，方便回看

同时把实现边界也一并写清了：

- 前端需要新增 `streamingTools`
- 后端需要补结构化 `tool_event`
- `ThinkingPanel` 在 Tool Rail 存在时退到第二层

产物：

- `docs/design/2026-04-21-tool-visibility-rail.md`
- `docs/design/tool-visibility-rail.html`
- `docs/design/assets/tool-visibility-rail.png`

---

## 实现记录（2026-04-21 晚）

### 后端

**`src/collaboration/mcp_executor.py`**
- 新增 `_build_summary()`：从工具参数中提取人类可读摘要（优先 `file_path`/`path`/`query`/`content`）
- 新增 `_emit_tool_event()`：fire-and-forget 广播 `tool_event`
- `execute_callbacks()` 现在接受 `cat_id`, `run_id`, `broadcast` 参数
- 每个工具调用前后各 emit 一次（start → finish），finish 携带 `duration_ms`

**`src/collaboration/a2a_controller.py`**
- 调用 `execute_callbacks` 时传入 `cat_id=breed_id`, `run_id=invocation_id`, `broadcast=self.broadcast_callback`

### 前端状态

**`web/src/stores/chatStore.ts`**
- 新增 `ToolCallState` interface
- 新增 `streamingTools: Map<string, ToolCallState[]>`
- 新增 `addToolEvent(catId, tool)`：按 `callId` 更新/追加，`runId` 变化时清空旧列表
- `stopStreaming()` 清空 `streamingTools`

**`web/src/hooks/useWebSocket.ts`**
- 新增 `ws.on("tool_event", ...)` handler，构造 `ToolCallState` 并调用 `addToolEvent`

### UI 组件

**`web/src/components/chat/ToolRail.tsx`**（新增）
- Primary card：当前运行中的工具（或最近完成的）
  - 左侧 wrench 图标 + 状态指示器
  - 工具名 + 摘要 + detail
  - 右侧状态 badge + 耗时
  - 顶部脉冲进度条（仅 running）
- Recent chips：最近 2 个已完成/失败的工具
- Overflow：+N 指示

**`web/src/components/chat/ChatArea.tsx`**
- 导入 `ToolRail`，读取 `streamingTools`
- 在 streaming response 的 status badge 下方、thinking panel 上方插入 `<ToolRail />`
- 在 status-only 区域同样插入（处理无内容但有工具运行的情况）

### 验证

- `cd web && npx tsc --noEmit` — 类型检查通过，无错误

### 问题与修复

**问题：消息不响应（"不会反馈消息了"）**

根因：`_emit_tool_event()` 使用 `asyncio.create_task()` 并发发送 tool_event，与主消息流竞争同一 WebSocket，导致消息顺序错乱甚至阻塞。

修复：
1. 改为 `await` 顺序发送，避免并发竞争
2. 新增 `_stringify_detail()` 防御性序列化，防止非字符串值导致前端解析失败
3. 前端 `useWebSocket.ts` 增加 `toText()` 防御函数，将所有字段强制转为字符串

### 持久化工具展示（CliOutputBlock）

ToolRail 是流式瞬态展示（streaming 结束后清空）。参考 cankao 模式，增加持久化展示：工具事件保存到 message metadata，在历史消息中可折叠查看。

**`src/collaboration/mcp_executor.py`**
- 新增 `ToolEvent` dataclass：`call_id`, `tool_name`, `summary`, `detail`, `status`, `duration_ms`
- `to_dict()` 序列化为 JSON-safe dict，用于持久化
- `execute_callbacks()` 收集所有 tool 事件到 `tool_events` list，赋值给 `parsed.tool_events`

**`src/collaboration/a2a_controller.py`**
- `CatResponse` 新增 `tool_events: Optional[List[ToolEvent]]`
- 响应构造时 `tool_events=getattr(parsed, "tool_events", None)`

**`src/web/routes/ws.py`**
- 保存 assistant message 时，如果 `response.tool_events` 存在，序列化后存入 `msg_metadata["tool_events"]`

**`web/src/components/chat/CliOutputBlock.tsx`**（新增）
- `ToolEventRecord` interface：与后端 `ToolEvent.to_dict()` 对应
- 折叠式区块：header 显示工具总数/完成数/失败数/总耗时
- `ToolRow`：每行显示状态图标 + 工具名 + 摘要 + 耗时，可展开查看 detail
- 流式时自动展开，结束后自动折叠（除非用户手动展开过）

**`web/src/components/chat/MessageBubble.tsx`**
- 导入 `CliOutputBlock`
- 从 `message.metadata.tool_events` 读取工具事件
- 在 rich blocks 下方渲染 `CliOutputBlock`

### 验证

- `python3 -m py_compile` 通过：`mcp_executor.py`, `a2a_controller.py`, `ws.py`
- `tsc --noEmit` 通过，无类型错误

### 后续修复（ToolRail 仍未显示）

**根因分析：**

1. CLI 内置工具（Read/Edit/Bash/Glob/Grep）与 MCP 注册表名称不一致 — CLI 输出 `tool_use` 块时工具名是 `Read`，但注册表里是 `read_file`
2. `a2a_controller.py` 没有处理 `AgentMessageType.TOOL_CALL` — CLI 的 `content_block_start(tool_use)` 被丢弃
3. `chatStore.stopStreaming()` 立即清空 `streamingTools` — 工具事件还没来得及渲染就被抹掉
4. CLI 工具已被 CLI 内部执行，`execute_callbacks` 再次调用会造成重复执行

**修复：**

**`src/collaboration/mcp_tools.py`**
- 新增 `CLI_TOOL_ALIASES`：将 CLI 工具名映射到 MCP 注册表名（`read` → `read_file` 等）
- 新增 `CLI_PARAM_MAPPINGS`：CLI 参数名映射到 MCP 参数名（`file_path` → `path` 等）

**`src/collaboration/mcp_executor.py`**
- `execute_callbacks()` 使用 `CLI_TOOL_ALIASES` 映射工具名
- `execute_callbacks()` 使用 `CLI_PARAM_MAPPINGS` 映射参数
- **关键改动**：识别到 `original_name in CLI_TOOL_ALIASES` 时，跳过实际执行（CLI 已内部完成），只 emit `finish` 事件，call_id 与 TOOL_CALL handler 保持一致
- 普通 MCP 工具（非 CLI 内置）继续走原有 start → 执行 → finish 流程

**`src/collaboration/a2a_controller.py`**
- 新增 `AgentMessageType.TOOL_CALL` handler：实时广播 `tool_event` start 事件
- 使用确定性 call_id：`f"{invocation_id}:{tool_key}:cli"`，确保与 `execute_callbacks` 后续 finish 事件匹配

**`web/src/stores/chatStore.ts`**
- `stopStreaming()` 不再清空 `streamingTools` — 流式结束后工具状态继续可见
- `startStreaming()` 新增 `streamingTools: new Map()` — 新会话开始时清空旧工具，避免累积

### 验证

- `python3 -m py_compile` 通过：`mcp_tools.py`, `mcp_executor.py`, `a2a_controller.py`, `claude_provider.py`
- `tsc -p web/tsconfig.json --noEmit` 通过，无类型错误

### 改动文件清单

- `src/collaboration/mcp_tools.py`
- `src/collaboration/mcp_executor.py`
- `src/collaboration/a2a_controller.py`
- `src/providers/claude_provider.py`
- `web/src/stores/chatStore.ts`
- `web/src/hooks/useWebSocket.ts`
- `web/src/components/chat/ToolRail.tsx`（新增）
- `web/src/components/chat/CliOutputBlock.tsx`（新增）
- `web/src/components/chat/MessageBubble.tsx`
- `web/src/components/chat/ChatArea.tsx`
