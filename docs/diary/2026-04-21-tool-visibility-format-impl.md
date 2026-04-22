---
date: 2026-04-21
doc_kind: diary
topics: ["tool", "chat", "ui", "ux", "copywriting"]
---

# Tool 展示格式 V2 实现

基于 @gemini 的设计稿（`docs/design/2026-04-21-tool-visibility-format-v2.md`）完成前端展示层改造。

## 改动

### `web/src/components/chat/ToolRail.tsx`

从工程感卡片改造成轻量 **Action Strip**（动作条）：

- 主区域是一条横向动作条：状态点 + 自然语言动作句 + 进度/耗时
  - `正在读 README.md`（不是 `read_file(read)`）
  - `正在搜索最近的 session 记录`（不是 `search_evidence`）
  - `正在执行命令`（不是 `execute_command`）
- 底部挂一排 breadcrumb（已完成步骤，最多 2 条），超出显示 `+N 步`
  - `已读 design.md` · `已搜索 ws.py` · `+1 步`
- 底边只有 1px 细线进度条（仅 running 时），不再整条 gradient bar
- 去掉 wrench 图标、状态英文标签、重复的状态 pill
- 新增 `TOOL_NAME_MAP` 把技术名映射到中文动作动词
- 新增 `extractFileName()` 从路径提取文件名用于展示

### `web/src/components/chat/CliOutputBlock.tsx`

从 CLI 日志块改造成 **Action Receipt**（动作回执）：

- 默认折叠态像消息脚注：
  - `本轮动作 3 步 · 2 完成 · 总耗时 2.4s`
- 展开后是整洁行项目（不用 monospace）：
  - 动作中文名 · 摘要对象 · 结果标签（苔绿/深朱）· 耗时
- 原始 detail 只在失败时默认展开，或用户主动展开时才可见
- 去掉 `font-mono`、深色日志底、整块 CLI 输出感

### `web/src/components/chat/ChatArea.tsx`

- ToolRail 调用处加上 `mb-2` 容器，和下方消息气泡保持适当间距

## 格式映射表

| Raw tool name | 中文动作 | 句式示例 |
|---|---|---|
| `read_file` / `read` | 读 | 正在读 README.md |
| `write_file` / `edit` | 写 | 正在写 config.py |
| `execute_command` / `bash` | 执行 | 正在执行命令 |
| `search_files` / `grep` | 搜索 | 正在搜索 ws.py |
| `list_files` / `glob` | 查找 | 正在查找文件 |
| `post_message` | 发 | 正在发送消息 |
| `read_session_events` | 读 | 正在读取会话记录 |

## 验证

- `web/node_modules/.bin/tsc -p web/tsconfig.json --noEmit` — 类型检查通过，无错误

## 改动文件

- `web/src/components/chat/ToolRail.tsx`
- `web/src/components/chat/CliOutputBlock.tsx`
- `web/src/components/chat/ChatArea.tsx`
