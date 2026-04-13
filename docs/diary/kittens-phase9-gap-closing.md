# Phase 9 开发日记 — 差距消除 8 模块 (v0.9.0)

**日期**: 2026-04-10
**角色**: 阿橘（架构）、墨点（安全）、花花（API）

---

## 背景

Phase 8 完成后，进行功能完整性分析，发现 8 个关键功能差距。用户选择了全部实现。

---

## 8 模块总览

| # | 模块 | 优先级 | 测试 | 状态 |
|---|------|--------|------|------|
| 1 | 多平台网关 | P1 | 30 | ✅ |
| 2 | 向量搜索 | P1 | 20 | ✅ |
| 3 | 技能链执行 | P1 | 12 | ✅ |
| 4 | Agent 热注册 | P2 | 15 | ✅ |
| 5 | Pack 系统 | P2 | 20 | ✅ |
| 6 | Web API 完善 | P2 | 18 | ✅ |
| 7 | 核心认证 | P2 | 25 | ✅ |
| 8 | 测试覆盖 | - | 扩展 | ✅ |

---

## 模块 1: 多平台网关

### 为什么先做这个？

阿橘："企业用户第一件事就是问能不能接飞书钉钉。没有多平台网关，就没有企业入场券。"

### 架构设计

```
BaseConnector (抽象类)
  ├── FeishuConnector   — 飞书/Lark
  ├── DingTalkConnector — 钉钉
  ├── WeComConnector    — 企业微信
  └── TelegramConnector — Telegram
```

每个 Connector 实现 3 个核心方法：
- `validate_request()` — 验证 Webhook 签名
- `parse_message()` — 解析平台消息为统一的 `PlatformMessage`
- `send_response()` — 回复消息

### 并行开发策略

由于 4 个平台适配器完全独立，用 **3 个并行 subagent** 同时开发：
- Agent A: Feishu + BaseConnector
- Agent B: DingTalk
- Agent C: WeCom + Telegram

**结果**: 原本需要串行 4 小时的工作，30 分钟全部完成。

### 踩坑

**飞书签名验证**: 飞书使用 timestamp + token 的 HMAC-SHA256，一开始没对齐文档里的拼接顺序，改了两次才过。

---

## 模块 2: 向量搜索

### 技术选型

**方案对比**:

| 方案 | 优点 | 缺点 |
|------|------|------|
| sqlite-vec | 无外部依赖 | 需要编译 C 扩展 |
| HashEmbedding | 纯 Python | 语义质量低 |
| Qdrant | 生产级 | 需要独立服务 |

**最终方案**: HashEmbedding (零依赖) + Hybrid RRF (与 FTS5 结合)

### Hybrid RRF 算法

```
score = Σ 1/(k + rank_fts) + Σ 1/(k + rank_vector)
```

两个信号（全文搜索 + 向量相似度）通过 Reciprocal Rank Fusion 合并。k=60 是平滑常数。

### 踩坑

**HybridSearch 构造函数**: 一开始接受 `MemoryDB`，但 `MemoryDB` 没有 `episodic` 属性。改成接受 `EpisodicMemory` 直接注入才通过。

---

## 模块 3: 技能链执行

### ChainTracker 设计

```python
chain = tracker.start_chain("thread-1", ["tdd", "debugging", "quality-gate"])
# 技能1执行完成 → advance → 自动注入技能2的上下文
tracker.advance("thread-1", {"result": "tests passed"})
```

**最大深度 5**，防止无限递归。

### 踩坑

**advance() 返回值**: 完成所有技能后应该返回 None，一开始写成了返回 chain（已完成状态），导致下游判断错误。修了一行搞定。

---

## 模块 4: Agent 热注册

### AgentDiscovery

运行时动态添加/移除 Agent，无需重启服务：

```python
discovery = AgentDiscovery(registry)
discovery.register(AgentDescriptor(
    cat_id="new-agent",
    breed="ragdoll",
    display_name="新伙伴",
    capabilities=["coding"],
    provider="claude",
))
```

### 踩坑

**AgentService import**: 尝试从 `src.models.types` 导入 `AgentService`，但该类不存在。改为在 discovery.py 中创建本地 dataclass。

---

## 模块 5: Pack 系统

### Pack = 预配置的 Agent 组

```yaml
# packs/tdd-pack.yaml
name: tdd-pack
agents:
  - cat_id: tester
    breed: siamese
  - cat_id: implementer
    breed: maine_coon
skills: [tdd, debugging, quality-gate]
workflow: tdd
```

一键激活一组 Agent + 技能 + 工作流。

---

## 模块 6: Web API 完善

补充了 REST API 端点：

| 端点 | 说明 |
|------|------|
| `GET /api/packs` | Pack 列表 |
| `GET /api/agents` | Agent 列表 |
| `POST /api/agents` | 注册 Agent |
| `GET /api/governance/iron-laws` | 铁律列表 |
| `GET /api/workflow/templates` | 工作流模板 |

---

## 模块 7: 核心认证

### JWT + RBAC

```python
user = User(id=1, username="admin", role="admin", ...)
token = user.generate_token(secret)

ROLE_PERMISSIONS = {
    "admin":  {"read", "write", "delete", "manage_users"},
    "member": {"read", "write"},
    "viewer": {"read"},
}
```

### 新增依赖

```toml
pyjwt>=2.8.0
httpx>=0.27.0
```

---

## 模块 8: 测试覆盖扩展

### 最终数字

```
Phase 8 基线:  470 tests
Phase 9 新增:  171 tests (+36%)
总计:          641 tests (100% 通过)
```

---

## 并行执行时间线

```
19:40  Task 1: BaseConnector 创建
19:42  Task 2: Embedding 接口
19:44  ──── 并行发射 3 个 subagent ────
       Agent A: Feishu adapter
       Agent B: DingTalk adapter
       Agent C: WeCom + Telegram adapter
19:47  所有 adapter 实现完成
19:49  模块 1 完成，模块 2 Vector Store 启动
19:52  向量搜索完成
19:55  Hybrid RRF 完成
20:00  技能链 + Agent 热注册
20:05  Pack + Web API
20:10  认证模块
20:15  全部 641 tests 绿
```

**实际用时**: ~40 分钟完成 8 个模块。

---

## 经验总结

### 做对的

1. **并行 subagent** — 独立模块同时开发，40 分钟完成 8 模块
2. **先测试后实现** — TDD 确保每个模块独立可用
3. **增量提交** — 每个模块独立 commit，方便回滚

### 踩过的坑

1. `MemoryDB` 没有 `episodic` 属性 → 直接注入 EpisodicMemory
2. `ChainTracker.advance()` 完成后返回值错误 → 修一行
3. `AgentService` 不存在于 models.types → 创建本地 dataclass
4. `VectorStore.delete()` 是同步方法但测试用了 await → 去掉 await

---

*Phase 9 完成！从 470 到 641 tests，8 个模块全部就位。* 🎯
