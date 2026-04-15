# MeowAI Home: Clowder 对齐 + Happy 延伸 总体规划 v2

> **For agentic workers:** 本计划为**总体规划 (Master Plan)**，拆分为多个可独立执行的子计划。每个子计划产出可测试、可运行的软件。 REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each sub-plan.

**Goal:** 将 MeowAI Home 与 Clowder AI 核心功能对齐，然后向 Happy 的移动端/远程控制/加密/推送方向延伸。

**Architecture:** 采用"先清债务、再补缺口、后做延伸"的三阶段策略。基于对现有代码的审计，大量功能已有骨架实现，后续工作应聚焦于**补全 gap** 而非从零重建。

**Tech Stack:** Python 3.9+ / FastAPI / SQLite+FTS5 / React 19 / TypeScript / Tailwind / Zustand / WebSocket

---

## 现状审计结论（基于代码实测）

### 已扎实实现（可直接作为基座）
- **认证系统**: `src/web/routes/auth.py` 实现了注册/登录/me；`tests/web/test_auth_api.py` 已有完整覆盖（含重复注册、非法角色、未鉴权）。
- **文件上传**: `src/web/routes/uploads.py` + `tests/web/test_uploads.py` 已实现上传/下载/路径穿越防护/大小限制。
- **Rich Block 类型定义**: `web/src/types/rich.ts` 已定义 7 种 block（card / diff / checklist / file / media / interactive / audio）。
- **Signal 后端**: `src/signals/` 有 fetchers、processor、query、store；前端有 `SignalInboxPage.tsx` 和 `useSignals.ts`。
- **Scheduler 后端**: `src/scheduler/runner.py` 已实现 `TaskRunner`（SQLite 持久化、cron/interval 触发、 governance 暂停）。
- **Review Watcher**: `src/review/watcher.py` 已实现 GitHub webhook 解析和 PR tracking。
- **Limb 基础**: `src/limb/registry.py` + `lease.py` + `remote.py` 已有设备注册与租赁管理。

### 真实阻塞项（Phase 0 必须先行）
1. **`tests/invocation/test_worklist.py` 5 个失败** — `_call_cat` 的 `AsyncMock` 返回 coroutine，但 `_serial_execute` 期望 async generator。
2. **`python-multipart` 依赖缺失** — 导致 `tests/web/` 16 个文件收集时直接 ERROR（环境级阻塞，需在项目依赖中显式声明）。
3. **ROADMAP 多处自相矛盾** — 同一功能同时标记为"完整"和"未实现"，会误导后续计划。

### Gap Matrix: 核心功能域的"已实现 / 半实现 / 缺失"盘点

| 功能域 | 已有实现 | 缺失 / 待补齐 | 优先级 |
|--------|----------|---------------|--------|
| **Rich Blocks** | 7 种类型定义 + 5 种渲染组件 | **AudioBlock 渲染缺失**；interactive 无后端回调；diff 无 syntax highlight | P1 |
| **Signal Study** | 收件箱、来源管理、学习模式 UI 占位 | **Podcast 生成**、**多猫研究报告**、笔记持久化 | P1 |
| **Voice** | 前端 `VoiceInput.tsx` / `TTSButton.tsx`（浏览器原生 API） | **后端 TTS 服务**、per-cat voice 配置、ASR 上传处理、音频流式播放 | P1 |
| **Mission Hub** | `MissionHubPage.tsx` 单页 | Workflow SOP 面板、Feature bird-eye、Resolution queues、Baton 状态实时展示 | P2 |
| **Workspace** | `WorkspacePanel.tsx` 占位 | 文件树、Git diff 面板、嵌入终端 | P2 |
| **Scheduler** | `TaskRunner` 后端引擎 | **REST API 路由**、**cron 模板**（reminder / repo-activity / web-digest）、前端管理面板 | P2 |
| **GitHub PR 自动化** | Webhook 解析 + PR tracking | **IMAP/邮件路由**、PR 自动创建、CI 状态轮询、与 Thread 的自动关联 | P2 |
| **Limb Control Plane** | Registry + Lease 后端 | **REST API 路由**、设备配对 UI、远程调用网关 | P2 |
| **Game Engine** | 无 | 狼人杀规则引擎 + UI、像素格斗 demo | P3 |
| **Happy 加密** | 无 | E2EE 密钥协商、session data key、客户端加密层 | P3 |
| **Happy 推送** | 无 | Expo / Web Push、智能路由、通知模板 | P3 |
| **Happy 远程控制** | 无 | Daemon 模式、机器在线状态、session proxy、设备切换 | P3 |
| **Happy 移动端** | 无 | Expo 工程搭建、API 客户端适配 | P4 |

---

## Phase 0: Unblockers & Baseline Calibration

> **本阶段是唯一在 Master Plan 中完全展开的细节计划。** 完成后方可进入后续阶段。

### Task 1: 修复 worklist 测试失败

**Files:**
- Modify: `tests/invocation/test_worklist.py`

- [ ] **Step 1: 定位 mock 用法**

  当前失败根因：测试中对 `_call_cat` 使用了 `AsyncMock(return_value=[...])`，但 `src/collaboration/a2a_controller.py:174` 中对该方法使用了 `async for`，要求其返回 async generator。

- [ ] **Step 2: 将 mock 改为 async generator 函数**

  在 `tests/invocation/test_worklist.py` 中，把所有直接对 `ctrl._call_cat` 赋值为 `AsyncMock` 的地方，替换为返回 async generator 的 mock：
  ```python
  async def _mock_call_cat(*args, **kwargs):
      yield {"content": "mock response"}
  ctrl._call_cat = _mock_call_cat
  ```
  若测试需要模拟多段流式返回，使用多个 `yield`。

- [ ] **Step 3: 运行测试确认修复**

  ```bash
  pytest tests/invocation/test_worklist.py -v
  ```
  Expected: 16 tests all pass（当前 11 pass + 5 failed）。

- [ ] **Step 4: Commit**

  ```bash
  git add tests/invocation/test_worklist.py
  git commit -m "fix: worklist 测试中 async generator mock 不匹配"
  ```

---

### Task 2: 解除 Web 测试收集阻塞

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 确认依赖缺口**

  `tests/web/` 共 16 个测试文件因 `python-multipart` 缺失在收集阶段报错。需要在项目依赖中显式声明。

- [ ] **Step 2: 添加依赖并安装**

  在 `pyproject.toml` 的依赖列表中加入：
  ```toml
  python-multipart>=0.0.9
  ```
  然后安装：
  ```bash
  python3 -m pip install python-multipart
  ```

- [ ] **Step 3: 验证整个 web 测试套件可收集**

  ```bash
  pytest tests/web --collect-only
  ```
  Expected: `collected N items`，0 errors。

- [ ] **Step 4: Commit**

  ```bash
  git add pyproject.toml
  git commit -m "chore: 显式添加 python-multipart 依赖以解除 web 测试收集阻塞"
  ```

---

### Task 3: 系统性修正 ROADMAP 状态基线

**Files:**
- Modify: `docs/superpowers/ROADMAP.md`

**已确认的矛盾点清单：**

1. **文件上传**:
   - 第182行已标记为 ✅ 完成
   - 第623行"多模态支持"仍写"STT/TTS/文件上传缺失"
   - **修正**: 第623行改为"STT/TTS/Vision 缺失"，删除"文件上传"。

2. **多用户系统**:
   - 第330行标记为"部分完成"
   - 第336行写"OAuth/SSO 未实现"
   - 第616行功能矩阵写"多用户系统 = ✅ 完整 | RBAC + SSO"
   - **修正**: 第616行改为"多用户系统 | 🔨 部分完成 | 9 | JWT+RBAC 框架已完成，OAuth/SSO/ACL 待实现"。

3. **OAuth/SSO**:
   - 第336行正确标记为 ❌ 未实现
   - 功能矩阵中不应勾选。

- [ ] **Step 1: 逐条修正上述矛盾**

- [ ] **Step 2: Commit**

  ```bash
  git add docs/superpowers/ROADMAP.md
  git commit -m "docs: 校准 ROADMAP 状态标记，消除自相矛盾"
  ```

---

## Phase 1: 高优先级 Clowder 功能补齐 (P1)

### Plan 1.1: Rich Block 增强 — Audio + Interactive 回调 + Diff 高亮

**Goal:** 补齐当前 Rich Block 体系的渲染缺口和交互闭环。

**Gap 分析:**
- `RichBlocks.tsx` 已支持 card / diff / checklist / media / interactive，但 **audio 类型直接落入 `default` 返回 null**（无 `AudioBlock.tsx`）。
- `InteractiveBlock.tsx` 只有前端 UI 状态，无向后端提交选择的通道。
- `DiffBlock.tsx` 只是简单文本块，无 syntax highlight 和行号。

**核心交付:**
1. 新建 `AudioBlock.tsx`（支持 `<audio>` 标签和流式 URL）。
2. `InteractiveBlock.tsx` 增加 `onAction` 回调，通过 WebSocket 或 REST 将用户选择回传后端。
3. `DiffBlock.tsx` 接入代码高亮（可用 `react-syntax-highlighter` 或纯 CSS 行号）。
4. 后端增加 `interactive_action` MCP 工具或 API，支持 agent 读取用户选择结果。

**文件清单:**
- Create: `web/src/components/rich/AudioBlock.tsx`
- Modify: `web/src/components/rich/RichBlocks.tsx`
- Modify: `web/src/components/rich/InteractiveBlock.tsx`
- Modify: `web/src/components/rich/DiffBlock.tsx`
- Modify/Create: `src/web/routes/messages.py`（增加 interactive action 端点）

---

### Plan 1.2: Signal Study 深度 — Podcast + 研究报告 + 笔记持久化

**Goal:** 将 Signal 从"RSS 阅读器"升级为"AI 研究助手"。

**Gap 分析:**
- `SignalInboxPage.tsx` 已有"学习模式"UI，但"生成播客"和"讨论"按钮是空壳。
- 后端无 podcast 生成逻辑、无多猫协作研究报告逻辑、无笔记持久化。

**核心交付:**
1. **Podcast 生成**: 新增 `src/signals/podcast.py`，将文章摘要转为对话脚本，调用 TTS 服务生成音频文件。
2. **研究报告**: 新增 `src/signals/research.py`，通过 A2A 分发研究任务给多只猫，聚合输出结构化报告。
3. **笔记持久化**: 新增 `notes` 表（或复用 memory/semantic），前端学习模式中的 textarea 内容可保存/读取。
4. 前端在 `SignalInboxPage.tsx` 中接入真实 API。

**文件清单:**
- Create: `src/signals/podcast.py`
- Create: `src/signals/research.py`
- Modify: `src/signals/store.py`（增加 notes 支持）
- Modify: `web/src/components/signals/SignalInboxPage.tsx`

---

### Plan 1.3: Voice Companion 后端

**Goal:** 建立真正的 TTS/STT 后端，支持 per-cat voice。

**Gap 分析:**
- 前端有 `VoiceInput.tsx`（Web Speech API）和 `TTSButton.tsx`（浏览器 speechSynthesis）。
- 无后端服务：无法统一控制 voice 身份、无法生成可分享的音频文件、无法支持非浏览器客户端。

**核心交付:**
1. **TTS 服务抽象** `src/voice/tts_service.py`: 支持 Edge TTS（免费）和 ElevenLabs（高质量），按 cat ID 映射 voice ID。
2. **ASR 上传处理** `src/voice/asr_service.py`: 接收音频文件，调用 Whisper API 或本地模型转录。
3. **REST API** `src/web/routes/voice.py`: `/voice/tts` 返回音频 URL 或流；`/voice/asr` 接收文件返回文本。
4. **前端适配**: `AudioPlayer.tsx` 播放后端生成的音频；`VoiceInput.tsx` 支持上传录音到 ASR。

**文件清单:**
- Create: `src/voice/tts_service.py`
- Create: `src/voice/asr_service.py`
- Create: `src/web/routes/voice.py`
- Create: `web/src/components/chat/AudioPlayer.tsx`
- Modify: `web/src/components/chat/TTSButton.tsx`
- Modify: `web/src/components/chat/VoiceInput.tsx`

---

## Phase 2: 中优先级 Clowder 功能补齐 (P2)

### Plan 2.1: Mission Hub & Workspace 增强

**Goal:** Mission Hub 成为功能治理中枢，Workspace 能浏览文件和嵌入终端。

**Gap 分析:**
- Mission Hub 当前是单页；需要 workflow SOP 面板、baton 状态、feature 生命周期看板。
- Workspace 当前是占位；需要文件树、git diff 面板、终端输出。

**核心交付:**
1. `MissionHubPage.tsx` 重构为多 tab 布局：Projects / Workflows / Features / Resolution Queue。
2. 新增 `WorkspaceFileTree.tsx`（递归展示项目目录）。
3. 新增 `WorkspaceGitPanel.tsx`（调用 `git diff` / `git status` API）。
4. 新增 `WorkspaceTerminal.tsx`（WebSocket 连接到后端命令执行器，显示 stdout）。

**文件清单:**
- Modify: `web/src/pages/MissionHubPage.tsx`
- Create: `web/src/components/workspace/FileTree.tsx`
- Create: `web/src/components/workspace/GitPanel.tsx`
- Create: `web/src/components/workspace/TerminalPanel.tsx`
- Create/Modify: `src/web/routes/workspace.py`（git/terminal/filetree API）

---

### Plan 2.2: Scheduler 完整化 — API + Cron 模板 + 前端面板

**Goal:** 让 TaskRunner 可被用户通过 Web UI 管理。

**Gap 分析:**
- `src/scheduler/runner.py` 后端引擎完整，但无 REST API、无预置模板、无前端面板。

**核心交付:**
1. `src/web/routes/tasks.py`: CRUD + enable/disable + trigger now API。
2. `src/scheduler/templates.py`: reminder / repo-activity / web-digest 三个预置模板。
3. `web/src/components/settings/TaskScheduler.tsx`: 任务列表、新建/编辑表单、运行日志。

**文件清单:**
- Create: `src/web/routes/tasks.py`
- Create: `src/scheduler/templates.py`
- Create: `web/src/components/settings/TaskScheduler.tsx`

---

### Plan 2.3: GitHub PR 自动化补齐

**Goal:** PR 事件能自动路由到对应 Thread 并触发审查。

**Gap 分析:**
- `src/review/watcher.py` 能解析 webhook，但无 IMAP 邮件路由、无 Thread 自动关联、无自动创建 PR。

**核心交付:**
1. `src/review/router.py`: 将 `PREvent` 映射到现有 Thread（通过 repo 关联）或新建 Thread。
2. `src/review/imap_poller.py`: 可选的 IMAP 轮询，解析 GitHub 邮件通知。
3. `src/review/ci_tracker.py`: 轮询 PR 的 CI 状态并更新 tracking。
4. Web UI: 显示待审 PR 列表和分配 reviewer 的界面。

**文件清单:**
- Create: `src/review/router.py`
- Create: `src/review/imap_poller.py`
- Create: `src/review/ci_tracker.py`
- Modify: `src/web/routes/review.py`

---

### Plan 2.4: Limb Control Plane 补齐

**Goal:** 设备发现、配对、远程调用可从前端操作。

**Gap 分析:**
- `src/limb/` 后端有 registry/lease/remote，但无 REST API、无配对 UI。

**核心交付:**
1. `src/web/routes/limbs.py`: 设备列表、配对请求、调用 limb API。
2. `web/src/components/settings/LimbPanel.tsx`: 显示在线设备、发起配对、查看调用历史。

**文件清单:**
- Create: `src/web/routes/limbs.py`
- Create: `web/src/components/settings/LimbPanel.tsx`

---

## Phase 3: 低优先级与 Happy 延伸 (P3-P4)

### Plan 3.1: 游戏引擎

**Goal:** 狼人杀 + 像素格斗 demo。

**核心交付:**
1. `src/games/werewolf/` — 规则引擎（角色分配、日夜循环、投票、胜负判定）。
2. `src/games/brawl/` — 像素格斗简化版（回合制攻击/防御）。
3. `web/src/pages/GameLobbyPage.tsx` — 游戏大厅和房间管理。

---

### Plan 3.2: 端到端加密 (Happy 方向)

**Goal:** 服务端不持有明文内容。

**核心交付:**
1. 每会话生成 Curve25519 密钥对，客户端协商共享密钥。
2. 消息和上传文件在客户端加密为 NaCl secretbox / AES-256-GCM blob。
3. 服务端仅存储和转发密文。

---

### Plan 3.3: 推送通知系统

**Goal:** 跨设备推送（Expo + Web Push）。

**核心交付:**
1. 设备注册时存储 push token + 平台 + 最后活跃时间。
2. 根据 presence 智能路由：优先发送到最近活跃设备，抑制 originating 设备。
3. 支持通知类型：@mention、任务完成、权限请求、错误告警。

---

### Plan 3.4: 设备切换与远程会话控制

**Goal:** 手机 ↔ 桌面无缝切换。

**核心交付:**
1. 本地 CLI daemon 保持机器在线状态。
2. 移动端接管时，本地 session 进入 remote 模式，输出通过 WebSocket 同步。
3. 桌面任意键盘输入自动切回 local 模式。

---

### Plan 3.5: 移动端应用 (Expo)

**Goal:** iOS/Android 应用。

**核心交付:**
1. `mobile/` 目录：Expo 项目初始化。
2. 复用现有 API client 和 Zustand stores（适配 React Native fetch）。
3. 核心页面：Thread 列表、聊天页、设置页。

---

## 建议执行顺序

1. **Phase 0**（1-2 小时）: 修复 worklist 测试、解除 python-multipart 阻塞、校准 ROADMAP。
2. **Phase 1 并行启动**: 建议先同时推进 **Plan 1.1 (Rich Block)** + **Plan 1.3 (Voice 后端)**，因为它们互相独立且产品可见性最高。
3. **Phase 1 完成后**: 启动 **Plan 1.2 (Signal Study)**。
4. **Phase 2**: 按 2.1 → 2.2 → 2.3 → 2.4 顺序推进（Mission Hub 和 Scheduler 可并行）。
5. **Phase 3**: 游戏引擎可穿插在 P2 之间作为调剂；Happy 延伸（加密/推送/远程/移动）放在所有 Clowder 对齐完成后。

---

## Self-Review Checklist

- [x] **无重复测试创建项**: auth/upload 测试已确认存在于仓库中，计划中不再要求重写。
- [x] **无固定 commit 签名**: 已删除所有 `[宪宪/Opus-46🐾]` 等固定签名，避免身份冒充。
- [x] **Gap Matrix 精确**: 基于代码审计结果，区分了"骨架已存在"和"完全缺失"的功能域。
- [x] **ROADMAP 修正范围足够**: 覆盖了已发现的 3 组自相矛盾，而非仅改局部。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-clowder-alignment-and-happy-extension-v2.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per Phase 0 task, review between tasks, fast iteration.
2. **Inline Execution** — I execute Phase 0 tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
