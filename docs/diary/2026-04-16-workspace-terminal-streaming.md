---
date: 2026-04-16
doc_kind: diary
topics: ["workspace", "terminal", "sse", "streaming", "async"]
---

# Workspace Terminal 流式化改造完成

今日完成 Workspace Terminal 从同步阻塞到异步流式的完整改造，解决运行 `npm install`、`pytest` 等耗时命令时前端"卡住/没执行"的体验问题。

## 问题根因

旧实现使用 `subprocess.run`（`src/web/routes/workspace.py` 同步端点），命令执行期间 HTTP 请求完全阻塞，前端只能看到一个 spinner，用户无法感知命令是否正在运行。

## 改造方案

采用"job 状态机 + SSE 流式事件 + 心跳/静默检测"架构：

### 后端

1. **新增异步 Job 运行时**
   - `src/web/routes/workspace.py` 新增 `TerminalJob` dataclass，维护进程、状态、输出 buffer、listener queues。
   - 新增 4 个 REST 端点：
     - `POST /api/workspace/terminal/jobs` — 创建并启动 job
     - `GET /api/workspace/terminal/jobs/{job_id}` — 获取 job 快照
     - `GET /api/workspace/terminal/jobs/{job_id}/stream` — SSE 事件流
     - `POST /api/workspace/terminal/jobs/{job_id}/cancel` — 取消 job（SIGTERM → 3s 后 SIGKILL）
   - `_run_terminal_job` 协程使用 `asyncio.create_subprocess_exec` 启动子进程，并发读取 stdout/stderr，并通过 `asyncio.Queue` 广播给所有 SSE listener。

2. **心跳与状态检测**
   - `_heartbeat` 协程每 2s 检测一次 `last_output_at`：
     - 5s 无输出 → 状态标记为 `quiet`
     - 30s 无输出 → 状态标记为 `stalled`
   - 同时向客户端推送 `heartbeat` 事件。

3. **进度解析与输入等待检测**
   - 新增 `src/workspace/terminal_parsers.py`，对 npm/pnpm、pytest、git、docker 命令做轻量正则匹配，提取进度百分比与阶段信息。
   - 检测 `(?i)(y/n|yes/no|password:|continue\?|enter to continue)` 等交互式提示，推送 `waiting_input` 事件。

4. **保留旧端点兼容**
   - 同步 `POST /api/workspace/terminal` 继续保留，避免破坏既有调用。

### 前端

1. **API 层**
   - `web/src/api/client.ts` 新增 `TerminalJob` / `TerminalJobEvent` 类型，以及 `createTerminalJob`、`cancelTerminalJob`、`streamTerminalJob`。
   - SSE 使用 `fetch() + ReadableStream + TextDecoder` 手动解析（而非原生 `EventSource`），原因是需要携带 `Authorization` Bearer Token。

2. **Hook 层**
   - `web/src/hooks/useWorkspace.ts` 暴露 `createTerminalJob`、`cancelTerminalJob`、`streamTerminalJob`，旧 `runCommand` 保留兼容。

3. **TerminalPanel 重写**
   - `web/src/components/workspace/TerminalPanel.tsx` 全面重写：
     - 使用 `useWorkspace` 直接订阅 SSE 流。
     - `requestAnimationFrame` 批处理：stdout/stderr 事件先写入 `outputBufferRef`，每帧批量 flush 到 React state，避免高频渲染卡顿。
     - UI 新增状态指示灯（running / quiet / stalled / waiting_input / done / failed / cancelled）、进度条、`waiting_input` 横幅、取消按钮。

## 测试覆盖

- `tests/web/test_workspace_api.py` 新增 5 个用例：
  - `test_create_terminal_job` — 验证创建返回 `job_id` 与 `status`
  - `test_terminal_job_blocked` — 危险命令返回 400
  - `test_terminal_job_not_found` — 404 分支
  - `test_terminal_job_stream` — SSE 流消费，验证 `status`、`stdout`、`exited` 事件
  - `test_terminal_job_cancel` — 启动 `sleep 30` 后取消，验证状态为 `cancelled`

- 结果：25 passed（包含原有回归测试）。

## 质量检查

- Python `py_compile` 通过。
- 前端 `tsc --noEmit` 通过。
- ESLint 对本次修改的 4 个前端文件无报错（`client.ts` 中 `metrics`/`governance` 的既有 `any[]` 为历史遗留，未引入新错误）。

## 边界与限制

- job 存储在进程内存，后端重启会丢失（当前规模可接受）。
- 未引入 PTY，`vim`、`top` 等全屏交互命令仍不支持。
