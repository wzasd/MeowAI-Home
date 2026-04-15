---
doc_kind: diary
created: 2026-04-15
topics: [mission-hub, workspace, frontend, backend, git, terminal]
---

# Mission Hub & Workspace 增强

## 目标
推进 Phase 2, Plan 2.1：将 Mission Hub 从单一看板升级为多 tab 治理中枢，同时为 Workspace 补齐 Git 面板、终端面板和独立文件树组件。

## 实现内容

### 1. Workspace 后端 API 增强
- `src/web/routes/workspace.py`
  - 新增 `POST /api/workspace/terminal`：在 worktree 目录内执行 shell 命令，带 30s 超时、危险命令黑名单、输出截断保护
  - 新增 `GET /api/workspace/git-status`：返回分支名、ahead/behind、干净状态、变更文件列表
  - 新增 `GET /api/workspace/git-diff`：返回全局 diff 或指定文件 diff，带路径穿越防护

### 2. Workspace 前端组件拆分
- `web/src/components/workspace/FileTree.tsx`
  - 从 `WorkspacePanel.tsx` 中抽离出递归文件树组件，保持原有懒加载和图标映射能力
- `web/src/components/workspace/GitPanel.tsx`
  - 双栏布局：左侧显示 git status 文件列表，右侧显示 syntax-colored diff（按 diff 行前缀着色）
- `web/src/components/workspace/TerminalPanel.tsx`
  - 命令输入栏 + 执行历史，支持 stdout/stderr/returncode 展示，带加载状态和清空按钮
- `web/src/hooks/useWorkspace.ts`
  - 新增 `gitStatus()`、`gitDiff(path?)`、`runCommand(command)` 方法
- `web/src/components/workspace/WorkspacePanel.tsx`
  - 接入真实的 GitPanel 和 TerminalPanel，底部 tab 从 placeholder 切换为真实功能

### 3. Mission Hub 多 tab 重构
- `web/src/components/mission/MissionHubPage.tsx`
  - 将原有 `board | features | risks` 重构为 `Projects | Workflows | Features | Resolutions`
  - **Projects**：保留原有 kanban / list 视图和任务卡片
  - **Workflows**：新增工作流面板，调用 `/api/workflow/templates` 和 `/api/workflow/active`
  - **Features**：基于任务 tags 自动聚合成“功能模块”，展示每个模块的任务总数、完成数、进度条
  - **Resolutions**：展示阻塞项（blocked）、即将到期（dueDate ≤ 3 天）、待分配（unassigned）任务队列
- `web/src/hooks/useWorkflows.ts`
  - 新建 hook，封装 workflow templates 和 active workflows 的获取

### 4. 测试
- `tests/web/test_workspace_api.py`
  - 新增 8 个测试覆盖 terminal 和 git 端点：
    - `test_terminal_command_success`
    - `test_terminal_command_blocked`
    - `test_terminal_command_not_found`
    - `test_git_status_success`
    - `test_git_status_not_found`
    - `test_git_diff_success`
    - `test_git_diff_path_traversal`
- 后端测试：`tests/web/test_workspace_api.py` 20/20 passed，`tests/web/test_missions_api.py` 15/15 passed
- 前端类型检查：`tsc --noEmit` 0 错误

## 验证结果
- Workspace 底部 Git / Terminal / Preview / Health 四个 tab 中，Git 和 Terminal 已对接真实后端
- Mission Hub 四大 tab 均已可用，Workflows 能拉取后端模板，Features 按 tag 聚合，Resolutions 高亮风险项
- 所有新增后端 API 均带路径穿越防护和输出截断保护

## 下一步
- Plan 2.2: Scheduler 完整化 — API + Cron 模板 + 前端面板
