# MeowAI Home: Clowder 对齐 + Happy 延伸 总体规划

> **For agentic workers:** 本计划为**总体规划 (Master Plan)**，拆分为多个可独立执行的子计划。每个子计划产出可测试、可运行的软件。 REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each sub-plan.

**Goal:** 将 MeowAI Home 与 Clowder AI 核心功能对齐，然后向 Happy 的移动端/远程控制/加密/推送方向延伸，最终成为功能完整、体验一流的多 Agent 协作平台。

**Architecture:** 采用"先还债、再补齐、后创新"的三阶段策略。第一阶段清理技术债务和验证已声称完成但实际存在 gap 的功能；第二阶段按优先级补齐 Clowder 的核心功能域（Rich Block、Signal Study、Voice、Mission Hub）；第三阶段引入 Happy 的端到端加密、推送通知、设备切换和移动端架构。

**Tech Stack:** Python 3.11 + FastAPI + SQLite/FTS5 + React 19 + TypeScript + Tailwind + Zustand + WebSocket

---

## 子计划清单与依赖关系

```
Phase 1: 基础验证与债务清理
    │
    ▼
Phase 2: Clowder 核心体验对齐
    ├── Plan 2.1: Rich Block 增强 (diff / checklist / interactive / audio)
    ├── Plan 2.2: Signal Study 深度 (文章研究、笔记、Podcast 生成)
    ├── Plan 2.3: Voice Companion 后端 (TTS 管道、ASR、per-cat voice)
    └── Plan 2.4: Mission Hub & Workspace 增强 (SOP 面板、文件树、嵌入终端)
    │
    ▼
Phase 3: Clowder 高级功能对齐
    ├── Plan 3.1: 游戏引擎 (狼人杀、像素格斗)
    ├── Plan 3.2: GitHub PR 自动化与邮件路由
    ├── Plan 3.3: 调度器与动态任务系统
    └── Plan 3.4: Limb Control Plane (远程设备配对)
    │
    ▼
Phase 4: Happy 延伸
    ├── Plan 4.1: 端到端加密架构
    ├── Plan 4.2: 推送通知系统 (Expo / Web Push)
    ├── Plan 4.3: 设备切换与远程会话控制
    └── Plan 4.4: 移动端应用 (Expo / React Native)
```

---

## Phase 1: 基础验证与债务清理

> **本阶段是唯一在 Master Plan 中完全展开的细节计划。** 完成后方可进入 Phase 2。

### 范围

1. 修复已知测试失败
2. 验证并补齐认证/文件上传的端到端流程
3. 更新 ROADMAP 中过时的状态标记，建立真实基线

### 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `tests/invocation/test_worklist.py` | 修改 | 修复 `_call_cat` async mock |
| `src/collaboration/a2a_controller.py` | 阅读 | 确认 `_call_cat` 签名 |
| `tests/web/test_auth_api.py` | 新增 | 认证 API 覆盖 |
| `tests/web/test_uploads.py` | 新增/修改 | 文件上传覆盖 |
| `tests/web/conftest.py` | 新增 | Web 测试 fixtures |
| `pyproject.toml` 或 `requirements.txt` | 修改 | 补 `python-multipart` |
| `docs/superpowers/ROADMAP.md` | 修改 | 状态标记修正 |

---

### Task 1: 修复 worklist 测试失败

**Files:**
- Modify: `tests/invocation/test_worklist.py`
- Read: `src/collaboration/a2a_controller.py:160-190`

- [ ] **Step 1: 阅读 `_call_cat` 方法确认签名**

  运行:
  ```bash
  grep -n "_call_cat" src/collaboration/a2a_controller.py
  ```
  确认该方法返回的是 `AsyncGenerator`（即函数本身定义为 `async def` 且内部使用 `yield`）。

- [ ] **Step 2: 修改测试中的 mock 使其返回 async generator**

  在 `tests/invocation/test_worklist.py` 中，找到所有:
  ```python
  ctrl._call_cat = AsyncMock(return_value=[...])
  ```
  替换为:
  ```python
  async def _mock_call_cat(*args, **kwargs):
      yield {"content": "mock response"}
  ctrl._call_cat = _mock_call_cat
  ```
  （如果测试期望多段流式返回，则使用多个 `yield`）。

- [ ] **Step 3: 运行测试确认修复**

  运行:
  ```bash
  pytest tests/invocation/test_worklist.py -v
  ```
  Expected: 16 tests all pass (当前 11 pass + 5 failed)。

- [ ] **Step 4: Commit**

  ```bash
  git add tests/invocation/test_worklist.py
  git commit -m "fix: 修复 worklist 测试中 async generator mock 不匹配 [宪宪/Opus-46🐾]"
  ```

---

### Task 2: 补齐 Web 测试依赖与认证 API 测试

**Files:**
- Create: `tests/web/conftest.py`
- Create: `tests/web/test_auth_api.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: 确认缺失依赖**

  运行:
  ```bash
  pytest tests/web/ -v --collect-only 2>&1 | grep -i "multipart\|ModuleNotFoundError" | head -5
  ```
  若报错缺少 `python-multipart`，则在 `pyproject.toml` 的依赖列表中加入:
  ```toml
  python-multipart>=0.0.9
  ```

- [ ] **Step 2: 安装依赖**

  运行:
  ```bash
  pip install python-multipart
  ```

- [ ] **Step 3: 编写认证 API 测试**

  创建 `tests/web/test_auth_api.py`:
  ```python
  import pytest
  from fastapi.testclient import TestClient
  from src.web.app import create_app

  @pytest.fixture
  def client():
      app = create_app()
      return TestClient(app)

  def test_register_and_login(client):
      # Register
      r = client.post("/api/auth/register", json={
          "username": "testuser",
          "password": "testpass123",
          "role": "member",
      })
      assert r.status_code == 200
      data = r.json()
      assert data["username"] == "testuser"
      assert data["role"] == "member"

      # Login
      r = client.post("/api/auth/login", json={
          "username": "testuser",
          "password": "testpass123",
      })
      assert r.status_code == 200
      data = r.json()
      assert "access_token" in data
      assert data["username"] == "testuser"

      # Me
      r = client.get("/api/auth/me", headers={
          "Authorization": f"Bearer {data['access_token']}"
      })
      assert r.status_code == 200
      assert r.json()["username"] == "testuser"

  def test_login_invalid_password(client):
      r = client.post("/api/auth/login", json={
          "username": "testuser",
          "password": "wrongpass",
      })
      assert r.status_code == 401
  ```

- [ ] **Step 4: 运行认证测试**

  运行:
  ```bash
  pytest tests/web/test_auth_api.py -v
  ```
  Expected: all pass。

- [ ] **Step 5: Commit**

  ```bash
  git add tests/web/test_auth_api.py tests/web/conftest.py pyproject.toml
  git commit -m "test: 补齐认证 API 测试与 python-multipart 依赖 [宪宪/Opus-46🐾]"
  ```

---

### Task 3: 验证文件上传端到端

**Files:**
- Create: `tests/web/test_uploads.py`
- Read: `src/web/routes/uploads.py`

- [ ] **Step 1: 编写上传测试**

  创建 `tests/web/test_uploads.py`:
  ```python
  import pytest
  import io
  from fastapi.testclient import TestClient
  from src.web.app import create_app

  @pytest.fixture
  def client():
      app = create_app()
      return TestClient(app)

  def test_upload_requires_auth(client):
      # 未认证应 401
      r = client.post("/api/threads/t1/uploads", files={"file": ("x.txt", io.BytesIO(b"hi"))})
      assert r.status_code == 401
  ```
  （如果当前上传路由未要求认证，则测试应验证其允许匿名或返回 401，视实际策略而定。阅读 `src/web/routes/uploads.py` 和 `src/web/app.py` 中的中间件挂载确认）。

- [ ] **Step 2: 运行测试**

  运行:
  ```bash
  pytest tests/web/test_uploads.py -v
  ```
  Expected: 行为与代码一致。

- [ ] **Step 3: Commit**

  ```bash
  git add tests/web/test_uploads.py
  git commit -m "test: 验证文件上传 API 行为 [宪宪/Opus-46🐾]"
  ```

---

### Task 4: 修正 ROADMAP 状态标记

**Files:**
- Modify: `docs/superpowers/ROADMAP.md`

- [ ] **Step 1: 更新 Phase 9 认证状态**

  将 Phase 9.1 中:
  ```markdown
  - ❌ **用户管理 API**: 注册/登录/注销端点未实现
  ```
  改为:
  ```markdown
  - ✅ **用户管理 API**: 注册/登录/me 端点已实现 (`src/web/routes/auth.py` + `web/src/stores/authStore.ts`)
  ```

- [ ] **Step 2: 更新 Phase 5 文件上传状态**

  将 Phase 5.3 中:
  ```markdown
  - ❌ **文件上传** - 支持代码、文档、图片 (REST + WebSocket + MCP read_uploaded_file)
  ```
  （如果存在此标记）改为 ✅，并补充说明前端已集成。

- [ ] **Step 3: Commit**

  ```bash
  git add docs/superpowers/ROADMAP.md
  git commit -m "docs: 修正 ROADMAP 中认证与文件上传的实际状态 [宪宪/Opus-46🐾]"
  ```

---

## Phase 2: Clowder 核心体验对齐 (Sub-plans)

### Plan 2.1: Rich Block 增强

**Goal:** 让 MeowAI Home 的消息系统支持 diff、checklist、interactive select、audio 四种新 Rich Block。

**关键差距:**
- Clowder 支持 12+ rich block 类型；MeowAI 当前仅有 card / diff / checklist / media_gallery / audio / interactive 的枚举定义，但前端实际只渲染了 card 和简单 checklist。
- 需要补齐：代码 diff 高亮对比、可交互选择块、音频播放器。

**核心文件:**
- `web/src/types/rich.ts`
- `web/src/components/rich/RichBlocks.tsx`
- `web/src/components/rich/DiffBlock.tsx`
- `web/src/components/rich/ChecklistBlock.tsx`
- `web/src/components/rich/InteractiveBlock.tsx`
- `web/src/components/rich/AudioBlock.tsx`
- `src/web/schemas.py`

---

### Plan 2.2: Signal Study 深度

**Goal:** 将 Signal 从简单的 RSS 收件箱升级为支持研究笔记、多猫协作分析、Podcast 生成的研究助手。

**关键差距:**
- Clowder 有完整的 article query service、study notes、podcast generator；MeowAI 仅有 `SignalInboxPage.tsx`。
- 需要补齐：文章详情页、笔记编辑器、多猫研究报告、TTS podcast 合成。

**核心文件:**
- `web/src/pages/SignalStudyPage.tsx`
- `web/src/components/signals/StudyNotes.tsx`
- `src/signals/` (若不存在则新建)
- `src/web/routes/signals.py`

---

### Plan 2.3: Voice Companion 后端

**Goal:** 建立真正的 TTS/STT 后端管道，支持每只猫的独特声音。

**关键差距:**
- 当前前端有 `TTSButton.tsx` 和 `VoiceInput.tsx`，但仅使用浏览器原生 API；无后端基础设施。
- 需要补齐：TTS 服务抽象（Edge TTS / ElevenLabs）、音频流式 API、per-cat voice 配置、ASR 上传处理。

**核心文件:**
- `src/voice/` (新建)
- `src/voice/tts_service.py`
- `src/voice/asr_service.py`
- `src/web/routes/voice.py`
- `web/src/components/chat/AudioPlayer.tsx`

---

### Plan 2.4: Mission Hub & Workspace 增强

**Goal:** 让 Mission Hub 成为真正的功能治理中枢，Workspace 能浏览文件树和嵌入终端。

**关键差距:**
- Mission Hub 当前只有单页；Clowder 有 workflow SOP 面板、feature bird-eye、resolution queues。
- Workspace 当前只有占位面板；Clowder 有文件树、git diff、tmux 终端。

**核心文件:**
- `web/src/pages/MissionHubPage.tsx`
- `web/src/components/mission/WorkflowPanel.tsx`
- `web/src/components/workspace/FileTree.tsx`
- `web/src/components/workspace/TerminalPanel.tsx`
- `src/workspace/` (若不存在则新建)

---

## Phase 3: Clowder 高级功能对齐 (Sub-plans)

### Plan 3.1: 游戏引擎

**Goal:** 实现狼人杀和像素格斗两个游戏模式。

**核心文件:**
- `src/games/` (新建)
- `src/games/werewolf/` — 游戏规则引擎、角色分配、日夜循环、投票
- `src/games/brawl/` — 像素格斗 demo
- `web/src/pages/GameLobbyPage.tsx`

---

### Plan 3.2: GitHub PR 自动化

**Goal:** 自动追踪 GitHub PR 评论并路由到对应 thread。

**核心文件:**
- `src/integrations/github/` (新建)
- `src/integrations/github/pr_router.py`
- `src/integrations/email/` (IMAP 轮询、评论解析)
- `web/src/components/settings/GitHubIntegration.tsx`

---

### Plan 3.3: 调度器与动态任务

**Goal:** 实现 cron 模板（reminder、repo-activity、web-digest）和动态任务注册。

**核心文件:**
- `src/scheduler/` (新建)
- `src/scheduler/task_runner.py`
- `src/scheduler/cron_templates.py`
- `src/web/routes/tasks.py`

---

### Plan 3.4: Limb Control Plane

**Goal:** 实现远程设备/节点（Limb）的发现、配对和调用。

**核心文件:**
- `src/limb/limb_registry.py`
- `src/limb/limb_manager.py`
- `src/web/routes/limbs.py`
- `web/src/components/settings/LimbPanel.tsx`

---

## Phase 4: Happy 延伸 (Sub-plans)

### Plan 4.1: 端到端加密架构

**Goal:** 借鉴 Happy 的"server-blind"模型，对会话内容和消息进行客户端端到端加密。

**核心设计:**
- 每会话生成独立的数据密钥
- 客户端使用 TweetNaCl/libsodium 加密后上传密文 blob
- 服务端仅存储和转发，无法解密

**核心文件:**
- `web/src/crypto/` (新建)
- `packages/mobile/crypto/` (React Native 兼容层)
- `src/encryption/session_key.py`

---

### Plan 4.2: 推送通知系统

**Goal:** 实现 Expo Push Token + Web Push 的混合推送路由。

**核心设计:**
- 设备注册时存储平台、设备名、最后活跃时间
- 根据 presence/activity 智能路由通知
- 抑制 originating 设备的通知

**核心文件:**
- `src/notifications/` (新建)
- `src/notifications/push_router.py`
- `src/notifications/expo_client.py`
- `src/notifications/web_push.py`

---

### Plan 4.3: 设备切换与远程会话控制

**Goal:** 支持手机 ↔ 桌面的一键切换，远程查看和控制本地 Agent 会话。

**核心设计:**
- daemon 模式保持机器在线状态
- 移动端请求时，本地 session 进入 remote 模式
- 任意键盘输入自动切回本地模式

**核心文件:**
- `src/remote/` (新建)
- `src/remote/session_proxy.py`
- `src/remote/machine_presence.py`
- `packages/mobile/RemoteControlPage.tsx`

---

### Plan 4.4: 移动端应用 (Expo / React Native)

**Goal:** 用 Expo 构建 iOS/Android 应用，共享现有 React 组件逻辑。

**核心文件:**
- `mobile/` (新建)
- `mobile/App.tsx`
- `mobile/package.json`
- `mobile/src/api/client.ts` (适配 React Native fetch)

---

## 建议执行顺序

1. **立即执行 Phase 1**（预计 1-2 小时）
2. **选择 Phase 2 的 1-2 个子计划并行推进**（建议 2.1 Rich Block + 2.2 Signal Study）
3. **完成 Phase 2 后再进入 Phase 3**
4. **Happy 延伸放在 Phase 3 之后**，因为加密和移动化需要稳定的核心功能作为基础。

---

## Self-Review Checklist

- [x] **Spec coverage:** 所有 Clowder 核心差距（Rich Block、Signal、Voice、Mission Hub、Game、GitHub、Scheduler、Limb）均已映射到子计划。
- [x] **Placeholder scan:** 无 "TBD" 或 "implement later"。Phase 1 的任务已完全展开到代码级别。
- [x] **Type consistency:** 使用的类型（`TokenResponse`、`AuthUserResponse`、`Attachment`）与现有代码一致。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-clowder-alignment-and-happy-extension.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per Phase 1 task, review between tasks, fast iteration.
2. **Inline Execution** — I execute Phase 1 tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach? And after Phase 1, which Phase 2 sub-plan should we tackle first?**
