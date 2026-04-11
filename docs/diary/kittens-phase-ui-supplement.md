# Kittens 开发日记 — UI 功能补齐 (2026-04-11)

## 目标
补齐 MeowAI Home 前端与 Clowder AI 参考项目的功能差距。

## 代码量变化
- 前端代码: 3,745 行 → 6,304 行 (+68.6%)
- 新增组件: 25+ 个
- 新增页面: 3 个完整页面

## 新增模块

### 1. 富文本块系统 (Rich Blocks)
**文件**: `web/src/components/rich/`
- `CardBlock.tsx` — 信息/成功/警告/危险卡片，支持字段和按钮
- `DiffBlock.tsx` — 代码 diff 查看器，语法高亮
- `ChecklistBlock.tsx` — 交互式检查列表
- `MediaBlock.tsx` — 图片/媒体画廊
- `InteractiveBlock.tsx` — 选择/确认/按钮组交互块
- `RichBlocks.tsx` — 统一渲染入口
- `types/rich.ts` — TypeScript 类型定义

**集成**: MessageBubble 自动解析并渲染 richBlocks

### 2. 右侧面板 (Right Status Panel)
**文件**: `web/src/components/right-panel/`
- `RightStatusPanel.tsx` — 可拖拽调整宽度的右侧边栏
- `SessionChainPanel.tsx` — Session 链历史展示 (active/sealing/sealed)
- `TaskPanel.tsx` — 任务面板 (todo/doing/blocked/done)
- `TokenUsagePanel.tsx` — Token 用量统计、缓存命中率
- `QueuePanel.tsx` — 消息队列管理 (拖拽排序、暂停/恢复)

**特性**: 5 个标签页切换、实时宽度调整

### 3. Signal 收件箱
**文件**: `web/src/components/signals/SignalInboxPage.tsx`
- 文章列表 (S/A/B/C 分级、未读/已读/收藏状态)
- 文章详情 (摘要、关键词、学习模式)
- 来源管理
- 学习模式: 笔记、播客生成

### 4. Mission Hub 任务看板
**文件**: `web/src/components/mission/MissionHubPage.tsx`
- 5 列看板: Backlog/Todo/Doing/Blocked/Done
- 优先级标签: P0/P1/P2/P3
- 进度条、负责人分配
- 列表视图切换
- 功能/风险标签页 (占位)

### 5. Workspace IDE 面板
**文件**: `web/src/components/workspace/WorkspacePanel.tsx`
- 文件树浏览器 (可折叠、图标区分)
- 代码查看器 (语法高亮模拟)
- 底部面板: 终端/预览/Git/健康状态
- 可拖拽调整面板宽度

### 6. 聊天核心升级
**文件**: `web/src/components/chat/`
- `HistorySearchModal.tsx` — 历史对话搜索 (Ctrl+K)
- `ScrollToBottomButton.tsx` — 滚动到底部按钮
- `ReplyPill.tsx` — 回复引用指示器
- `ParallelStatusBar.tsx` — 多猫并行状态条
- `MessageBubble.tsx` — 新增回复/编辑/删除/分支按钮

### 7. CatCafe Hub 深度设置
**文件**: `web/src/components/settings/`
- `SettingsPanel.tsx` — 扩展为 8 个标签页
- `CapabilitySettings.tsx` — 猫咪能力配置 (代码生成/审查/对话/Git)
- `QuotaBoard.tsx` — 配额看板 (Token 消耗、调用次数)
- `LeaderboardTab.tsx` — 排行榜 (综合评分、成功率、延迟)
- `PermissionsSettings.tsx` — 权限矩阵 (按风险等级分级)

### 8. 侧边栏升级
**文件**: `web/src/components/thread/ThreadSidebar.tsx`
- 置顶区域
- 最近对话区域 (可折叠)
- 已归档区域 (可折叠)
- 未读/收藏计数徽章

### 9. 路由与布局
**文件**: `web/src/App.tsx`
- 4 个主要页面路由: Chat / Signal / Mission / Workspace
- 侧边栏顶部导航标签
- 右侧面板开关 (仅聊天页)

## 布局修复

### 修复内容 (2026-04-11)
1. **右侧面板标签** — 全部改为中文: 状态/用量/会话/任务/队列
2. **顶部导航** — 全部改为中文: 对话/收件箱/任务/工作区
3. **按钮重叠问题** — 将右侧面板开关从 App.tsx 的绝对定位工具栏移到 ChatArea 的头部，避免与 SessionStatus 和 ExportButton 重叠

## 界面预览

```
+-----------------------------------------------------------+
| Sidebar    | Main Content                | Right Panel   |
| +--------+ | +------------------------+ | +-----------+ |
| | 🐱Chat | | | ChatArea               | | | Status    | |
| | Signal | | |  - MessageBubble       | | | Token     | |
| | Mission| | |  - RichBlocks          | | | Session   | |
| | Worksp | | |  - ParallelStatusBar   | | | Task      | |
| +--------+ | |  - InputBar            | | | Queue     | |
|            | +------------------------+ | +-----------+ |
+-----------------------------------------------------------+
```

## 技术栈
- React 19 + TypeScript
- Tailwind CSS (dark mode)
- Zustand (state management)
- Lucide React (icons)

## 已完成的任务 (2026-04-11)

### Chat Core 升级 (#132)
**文件**: `web/src/components/chat/`
- `MessageBubble.tsx` — 内联编辑模式 (textarea + 保存/取消按钮)
- `MessageBubble.tsx` — 回复功能 (onReply 回调，回复指示器 UI)
- `MessageBubble.tsx` — 删除功能 (confirm 对话框 + API 调用)
- `MessageBubble.tsx` — 分支功能 (从消息创建新线程)
- `ChatArea.tsx` — Ctrl+K 历史搜索快捷键
- `api/client.ts` — 新增消息 API: edit/delete/reply/branch/search
- `chatStore.ts` — 新增 updateMessage/deleteMessage/setReplyingTo

### Split Pane + 语音 + 审计 + 刹车 (#134)
**文件**:
- `web/src/components/chat/SplitPaneView.tsx` — 2x2 多线程分屏视图
- `web/src/components/chat/VoiceInput.tsx` — Web Speech API 语音输入
- `web/src/components/audit/AuditPanel.tsx` — 审计日志面板 (按级别/类别筛选)
- `web/src/components/brake/BrakeSystem.tsx` — 紧急刹车系统 (确认对话框 + 状态显示)

**集成**:
- 右侧面板新增「审计」标签
- InputBar 添加语音输入按钮
- 状态标签页集成刹车系统组件

## 代码量
- 前端: ~7,200 行 (+92% from baseline)
- 组件: 30+ 个

## 下一步
- 对接真实后端 API (当前大部分为 mock 数据)
- 后端实现消息编辑/删除/回复/分支 API
- 语音输出 (TTS) 集成
