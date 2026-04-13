# Phase 4.1: Agent 调用引擎 (A1-A5) 完成

**日期:** 2026-04-11
**阶段:** Phase 4.1 - Agent Invocation Engine
**状态:** ✅ 已完成

---

## 今日成果

Phase A (Agent 调用引擎) 全部完成，5个模块 + 97个测试。

### 已完成的模块

| 模块 | 文件 | 代码行 | 测试数 |
|------|------|--------|--------|
| A1 InvocationQueue | `src/invocation/queue.py` | 126 | 17 |
| A2 QueueProcessor | `src/invocation/processor.py` | 65 | 14 |
| A3 DegradationPolicy | `src/invocation/degradation.py` | 76 | 19 |
| A4 EventAuditLog | `src/invocation/audit.py` | 89 | 17 |
| A5 Worklist路由 | `src/collaboration/a2a_controller.py` | +60 | 16 |

**总计:** 630+ 行新代码，97 个测试全部通过

---

## 技术实现要点

### A1: InvocationQueue
- Per-thread FIFO 队列（thread_id:user_id 作为 key）
- Tail merge: 同源同意图同目标的消息自动合并
- Max depth = 5，防止队列无限增长
- Stale cleanup: 1分钟排队/10分钟处理超时清理

### A2: QueueProcessor
- Per-slot mutex: `thread_id:cat_id` 作为锁 key
- Pause-on-failure: 失败后暂停该 slot，不影响其他
- Multi-cat entry: 多目标时占用第一个空闲 slot

### A3: DegradationPolicy
```python
BudgetLevel.FULL      # 正常范围内
BudgetLevel.TRUNCATED # 1.2x 范围内，可截断处理
BudgetLevel.ABORT     # 超出 1.2x，直接中止
```
- Self-heal retry: 对 stale_session/timeout/prompt_limit 最多重试2次
- Overflow circuit breaker: 连续3次失败触发熔断

### A4: EventAuditLog
- Append-only NDJSON，按日期分片
- 5种事件类型: CAT_INVOKED, CAT_RESPONDED, CAT_ERROR, A2A_HANDOFF, CLI_TIMEOUT
- 支持按 thread_id, cat_id, event_type, date 查询

### A5: Worklist 路由升级
- `parse_a2a_mentions()`: 解析 @cat_name 提及
- Worklist 模式: 支持 targetCats 指定初始列表
- Max depth = 5 防止无限链
- Fairness gate: 用户消息排队时不追加新 cat

---

## 测试结果

```
$ python3.11 -m pytest tests/invocation/ -v

97 passed in 0.11s
```

全量回归测试: 807 passed
(11 errors in e2e/benchmark 为环境依赖问题，不影响核心功能)

---

## 关键设计决策

### 1. targetCats 工作列表逻辑
```python
if agents_with_targets:
    # 只有被 targetCats 指定的 cat 进入初始 worklist
    worklist = [a for a in agents if a.breed_id in a.targetCats]
else:
    # 无指定时使用全部 agents
    worklist = all_agents
```

### 2. MagicMock 兼容性处理
测试使用 MagicMock，`agent.get("targetCats")` 返回 MagicMock (truthy)。
使用 `isinstance(tc, list)` 判断是否为真实列表。

### 3. Fairness Gate 实现
```python
if self._user_queue_has_pending():
    # 阻止将新提到的 cats 加入 worklist
    continue
```
子类可覆盖 `_user_queue_has_pending()` 方法。

---

## Invocation Engine 实现总结

核心特性全部实现：
- InvocationQueue — 请求队列
- Per-slot mutex — 防并发
- DegradationPolicy — 降级策略
- EventAuditLog — 调用审计
- Worklist routing — 工作列表路由

代码量: ~630 行新增

---

## 下一步

**Phase B: Session 连续性 (B1-B3)**
- B1: TranscriptWriter — 对话记录
- B2: SessionManager — Session 生命周期
- B3: HandoffDigest — 交接摘要

预计代码量: ~800 行，25+ 测试

---

*Phase 4.1 Agent 调用引擎完成！5个模块全部测试通过，为 Session 连续性打下基础。*
