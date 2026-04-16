# Phase C: MCP 健康探测

## 完成内容

### 后端
- 新建 `src/capabilities/mcp_probe.py`
  - `McpProbeResult` dataclass：记录 `capabilityId`、`connectionStatus`、`tools`、`error`
  - `_probe_server_stdio()`：通过 stdio 启动 MCP server，执行完整 JSON-RPC 握手
    1. 发送 `initialize` 请求（protocolVersion: 2024-11-05）
    2. 读取 initialize 响应
    3. 发送 `notifications/initialized`
    4. 发送 `tools/list` 请求
    5. 读取 tools 列表
  - 超时处理（默认 10s）
  - 错误分类：`connected`、`error`、`timeout`、`unsupported`
- `src/capabilities/models.py`
  - `CapabilityBoardItem` 新增 `connectionStatus`、`tools`、`probeError` 字段
- `src/capabilities/orchestrator.py`
  - `build_board_response()` 接受可选的 `probe_results` 参数，将探测结果合并到 MCP 条目中
- `src/web/routes/capabilities.py`
  - `GET /api/capabilities` 新增 `probe: bool = False` 查询参数
  - 当 `probe=true` 时调用 `probe_mcp_capabilities()` 并注入响应

### 前端
- `web/src/types/index.ts`
  - `CapabilityBoardItem` 扩展探测字段
- `web/src/api/client.ts`
  - `api.capabilities.get(projectPath, probe?)` 支持 `probe` 参数
- `web/src/components/settings/CapabilityBoard.tsx`
  - 新增"探测"按钮（绿色 `Activity` 图标）
  - MCP 表格行展示探测状态：
    - `connected` — 绿色圆点 + 工具数量（如"已连接 · 3 工具"）
    - `timeout` — 橙色圆点 + "探测超时"
    - `error` — 红色圆点 + 错误信息
    - `unsupported` — 灰色圆点 + "不支持探测"

### 测试
- 新建 `tests/capabilities/test_mcp_probe.py`
  - `test_probe_server_connected` — mock MCP server 正常返回 tools
  - `test_probe_server_initialize_error` — initialize 返回错误
  - `test_probe_server_timeout` — 探测超时
  - `test_probe_server_missing_command` — 缺少 command 字段
  - `test_probe_mcp_capabilities_skips_non_mcp` — 跳过 skill 类型
  - `test_probe_mcp_capabilities_filters_disabled` — 正常探测 MCP 条目
- `tests/web/test_capabilities_api.py`
  - 新增 `test_get_capabilities_with_probe` — 验证 API `probe=true` 响应包含 `connectionStatus`

## 验证结果
- Python 测试：38/38 通过（orchestrator 24 + mcp_probe 6 + web API 8）
- 前端 TypeScript：`tsc --noEmit` 零错误
