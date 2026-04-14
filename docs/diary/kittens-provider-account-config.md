# Provider Account Configuration 系统开发日记

**日期**: 2026-04-13
**角色**: 阿橘（后端 + 前端）

---

## 背景

### 问题

MeowAI Home 的所有 AI Provider（Claude/Codex/Gemini/OpenCode）在调用 CLI 时都不传递 `env` 参数，子进程直接继承父进程环境。当用户同时在运行 Claude Code 时，MeowAI 发起的 CLI 调用会共享同一个 OAuth session 的 API 并发配额，导致请求挂死。

### 解决方案

实现完整的 Provider Account Configuration 系统，支持两种认证模式：
1. **subscription** — CLI OAuth 模式（现有行为，共享配额）
2. **api_key** — 直接 API Key 模式（独立配额，解决并发问题）

架构采用双文件存储：账户元数据存在 `~/.meowai/accounts.json`，API Key 密钥存在 `~/.meowai/credentials.json`（权限 0o600）。

---

## 实现内容

### 1. AccountStore 数据模型

**新增文件**: `src/config/account_store.py`

双文件存储的账户管理器，遵循 `runtime_catalog.py` 的原子写入和 JSON 加载模式。

- 4 个 builtin 账户在首次加载时自动创建（不可删除）：
  - `builtin-anthropic` — Anthropic (Subscription)
  - `builtin-openai` — OpenAI (Subscription)
  - `builtin-google` — Google (Subscription)
  - `builtin-opencode` — OpenCode (Subscription)
- CRUD 方法：`list_accounts()`, `get_account()`, `create_account()`, `update_account()`, `delete_account()`
- 凭证方法：`get_credential()`, `set_credential()`, `delete_credential()`
- 列表返回时自动遮蔽 API Key，用 `hasApiKey` 布尔值替代
- 拒绝 `builtin-` 前缀的自定义账户 ID
- 单例工厂 `get_account_store()`

**测试**: `tests/config/test_account_store.py` — 8 个测试全部通过

### 2. 账户解析接入 Provider 调用链

**修改文件**:

- `src/models/types.py` — `CatConfig` 新增 `account_ref: Optional[str] = None` 字段
- `src/models/cat_registry.py` — `load_from_breeds()` 读取 `accountRef` 配置
- `src/config/account_resolver.py` — 新增 `resolve_account_env()` 函数：
  - 查找 AccountStore 中的账户
  - subscription 模式：剥离 API Key 环境变量
  - api_key 模式：注入凭证为环境变量
  - baseUrl 设置：注入 base URL 环境变量
- `src/providers/base.py` — `BaseProvider` 新增 `build_env()` 方法
- 4 个 Provider 全部更新，传递 `env=self.build_env()` 给 `spawn_cli()`:
  - `src/providers/claude_provider.py`
  - `src/providers/codex_provider.py`
  - `src/providers/gemini_provider.py`
  - `src/providers/opencode_provider.py`
- `cat-config.json` — 3 个 breed 都加了 `"accountRef": "builtin-anthropic"`

**调用链**: Provider.invoke() → build_env() → resolve_account_env(account_ref, provider) → resolve_runtime_env() → env dict → spawn_cli(env=env)

**测试**: `tests/config/test_account_resolver.py` — 8 个测试全部通过

### 3. Account CRUD API

**修改文件**: `src/web/routes/config.py`

新增 7 个端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config/accounts` | 列出所有账户（凭证已遮蔽） |
| GET | `/api/config/accounts/{id}` | 获取单个账户 |
| POST | `/api/config/accounts` | 创建账户 |
| PATCH | `/api/config/accounts/{id}` | 更新账户 |
| DELETE | `/api/config/accounts/{id}` | 删除账户（拒绝 builtin） |
| POST | `/api/config/accounts/{id}/test-key` | 验证 API Key 有效性 |
| PATCH | `/api/config/accounts/bind-cat` | 绑定猫到账户 |

test-key 端点通过轻量 API 调用验证：
- Anthropic: `POST /v1/messages` (max_tokens=1)
- OpenAI: `GET /v1/models`
- Google: `GET /v1beta/models?key=...`

**其他修改**:
- `src/config/runtime_catalog.py` — `to_overlay()` 输出 `accountRef` 字段
- `src/web/routes/cats.py` — 猫 API 响应包含 `accountRef` 字段

**测试**: `tests/web/test_account_e2e.py` — 4 个端到端测试全部通过

### 4. 前端实现

**类型定义** — `web/src/types/index.ts`:
- `AuthType`, `Protocol` 类型
- `AccountResponse`, `AccountListResponse`, `TestKeyResponse` 接口
- `CatResponse` 新增 `accountRef` 字段

**API 客户端** — `web/src/api/client.ts`:
- `api.config.accounts` 子对象，包含 list/create/get/update/delete/testKey/bindCat

**状态管理** — 新增 `web/src/stores/accountStore.ts`:
- Zustand store，标准 fetch/create/update/delete/testKey/bindCat 操作

**UI 组件** — 新增 `web/src/components/settings/AccountSettings.tsx`:
- 账户列表卡片：显示名称、协议 badge、认证类型 badge、API Key 状态指示
- 创建/编辑表单：Display Name、Protocol、Auth Type、API Key（含 Test 按钮）、Base URL、Models
- 猫绑定下拉框：在账户卡片内绑定/解绑猫

**设置入口** — 修改 `web/src/components/settings/SettingsPanel.tsx`:
- 新增 "AI Providers" tab（Key 图标），位于"猫咪管理"之后

**侧边栏设置按钮** — 修改 `web/src/components/thread/ThreadSidebar.tsx` + `web/src/App.tsx`:
- 在侧边栏底部 `v0.8.0 · MeowAI Home` 右侧添加 ⚙ 设置按钮
- 通过 `onOpenSettings` prop 触发 Settings 面板

### 5. 流式响应修复（前期工作）

本次会话前期还修复了流式响应的多个问题：

- `src/collaboration/a2a_controller.py` — `CatResponse` 新增 `is_final` 字段，`_call_cat` 改为 yield 增量内容块而非全量缓冲
- `src/web/routes/ws.py` — 只在 `is_final=True` 时持久化到数据库
- `web/src/hooks/useWebSocket.ts` — 修复 React Strict Mode 双重挂载导致的连接管理问题
- `web/src/stores/chatStore.ts` — 流式响应增量累积

---

## 测试结果

- 后端测试：**366 passed**（包含新增 20 个账户相关测试）
- 前端 TypeScript 编译：**0 errors**
- 之前已有的 9 个失败测试（A2A controller 签名不匹配等）与本次改动无关

---

## 文件变更汇总

| 文件 | 操作 |
|------|------|
| `src/config/account_store.py` | 新增 |
| `tests/config/test_account_store.py` | 新增 |
| `tests/config/test_account_resolver.py` | 扩展（+3 测试） |
| `tests/web/test_account_e2e.py` | 新增 |
| `web/src/stores/accountStore.ts` | 新增 |
| `web/src/components/settings/AccountSettings.tsx` | 新增 |
| `src/config/account_resolver.py` | 修改 |
| `src/models/types.py` | 修改 |
| `src/models/cat_registry.py` | 修改 |
| `src/config/runtime_catalog.py` | 修改 |
| `src/providers/base.py` | 修改 |
| `src/providers/claude_provider.py` | 修改 |
| `src/providers/codex_provider.py` | 修改 |
| `src/providers/gemini_provider.py` | 修改 |
| `src/providers/opencode_provider.py` | 修改 |
| `src/web/routes/config.py` | 修改 |
| `src/web/routes/cats.py` | 修改 |
| `cat-config.json` | 修改 |
| `web/src/types/index.ts` | 修改 |
| `web/src/api/client.ts` | 修改 |
| `web/src/components/settings/SettingsPanel.tsx` | 修改 |
| `web/src/components/thread/ThreadSidebar.tsx` | 修改 |
| `web/src/App.tsx` | 修改 |
