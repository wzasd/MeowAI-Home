# Kittens 开发日记 — Phase CRUD 集成修复

**日期:** 2026-04-11
**阶段:** 猫咪管理 + 配置系统端到端集成

---

## 背景

Phase A~J 全部实现完成后，发现猫咪管理（RuntimeCatalog）、配置注册（CatRegistry）、Agent 注册（AgentRegistry）三个子系统各自为政，前后端没有打通。参考 cankao/ (Clowder AI) 的两层 Breed+Variant deep-merge 架构后，进行了彻底的集成梳理。

## 完成的工作

### 1. RuntimeCatalog → CatRegistry 桥接
- **新增:** `src/models/registry_init.py` — `_apply_runtime_overlay()` 函数
- 启动时读取 `~/.meowai/cat-catalog.json`，deep-merge 到 CatRegistry
- 已有 cat: 更新 provider/model/personality 等字段
- 新 cat: 创建 CatConfig 并注册到 registry
- `initialize_registries()` 在加载 seed config 后调用 overlay

### 2. 统一猫咪 CRUD API
- **重写:** `src/web/routes/cats.py` — 完整 CRUD 端点
- POST `/api/cats` — 创建新猫，同时写入 RuntimeCatalog + CatRegistry + AgentRegistry
- GET `/api/cats` — 列出所有猫
- GET `/api/cats/{id}` — 获取单只猫详情
- PATCH `/api/cats/{id}` — 更新配置，三处同步刷新
- DELETE `/api/cats/{id}` — 删除猫，三处同步清理
- `_refresh_agent_registry()` helper 安全更新 provider

### 3. 前端猫咪管理 CRUD
- **重写:** `web/src/components/settings/CatSettings.tsx` — 完整交互式管理界面
  - CatEditor 表单组件（名称、Provider、模型、个性、Mention 别名）
  - 编辑/创建/删除按钮
  - API 错误显示
- **重写:** `web/src/stores/catStore.ts` — createCat/updateCat/deleteCat actions
- **新增:** `web/src/api/client.ts` — cats.create/update/delete 方法

### 4. Thread 猫切换
- **修改:** `src/web/routes/threads.py` — PATCH 支持 `current_cat_id`
- **新增:** `src/web/schemas.py` — ThreadUpdate schema
- **修改:** `web/src/components/chat/ChatArea.tsx` — CatSelector 连接 API

### 5. Bug 修复
- RuntimeCatalog._validate_mentions 收到 None → 添加 `is not None` guard
- cats.py PATCH 传递 None kwargs → 只传非 None 字段
- AgentRegistry.get() KeyError → 使用安全 dict 查找
- AgentRegistry.unregister() KeyError → 使用 `in` 检查
- RuntimeCatalog.update_cat() 缺少 displayName mapping → 添加

## 验证结果

```
Full CRUD cycle:
  CREATE testcat → ✅
  UPDATE testcat (personality + model) → ✅
  DELETE testcat → ✅
  LIST cats → [orange, inky, patch, tabby, siamese] ✅

Test suite: 1215 passed, 1 pre-existing failure (monitoring)
```

## 架构对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| RuntimeCatalog | 孤岛，启动不加载 | 启动 deep-merge + 实时同步 |
| Cat CRUD API | 只有 GET | 完整 POST/PATCH/DELETE |
| 前端管理 | 只读展示 | 完整交互式编辑 |
| 猫切换 | console.log 空操作 | API 调用 + 状态更新 |
| AgentRegistry | KeyError 崩溃 | 安全查询 |

## 关键文件

- `src/models/registry_init.py` — 桥接层
- `src/web/routes/cats.py` — CRUD 端点
- `src/config/runtime_catalog.py` — 持久化层
- `web/src/stores/catStore.ts` — 前端状态
- `web/src/components/settings/CatSettings.tsx` — 管理界面
