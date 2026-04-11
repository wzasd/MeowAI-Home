# Phase A: Agent 调用引擎实现日记

**日期:** 2026-04-11  
**模块:** Phase A - Agent Invocation Engine (P0)  
**范围:** A1-A5 完整实现

---

## 今日成果

完成 Phase A 全部五个子任务，实现核心 Agent 调用引擎。

### 交付文件

| 文件 | 功能 | 测试 |
|------|------|------|
| `src/invocation/queue.py` | InvocationQueue 请求队列 | 17 passing |
| `src/invocation/processor.py` | QueueProcessor 队列消费器 | 15 passing |
| `src/invocation/degradation.py` | DegradationPolicy 降级策略 | 23 passing |
| `src/invocation/audit.py` | EventAuditLog 调用审计 | 16 passing |
| `src/collaboration/a2a_controller.py` | Worklist 路由升级 | 已存在 |

**总计:** ~650 行代码，97 invocation 测试

---

## 实现细节

### A1: InvocationQueue 请求队列

**核心功能:**
- Per-thread FIFO 队列（最大深度 5）
- 尾部合并：同源同意图同目标的消息自动合并
- 过期清理：1分钟 queued / 10分钟 processing 自动标记失败
- 线程安全：RLock 保护并发操作

```python
queue = InvocationQueue(max_depth=5)
result = queue.enqueue(
    thread_id="t1",
    user_id="u1", 
    content="Hello",
    target_cats=["cat_1"],
    source="user",
    intent="execute",
)
# result.outcome: "enqueued" | "merged" | "full"
```

### A2: QueueProcessor 队列消费器

**核心功能:**
- Per-slot 互斥锁：thread_id:cat_id 防止并发执行
- 失败暂停：slot 失败时暂停，不影响其他 slot
- 自动执行：A2A dispatch 自动触发下一个

```python
processor = QueueProcessor(queue)
entry = processor.try_execute_next("t1", "u1")
success = processor.execute_entry(entry, handler)
```

### A3: DegradationPolicy 降级策略

**核心功能:**
- Context budget 检查：FULL → TRUNCATED → ABORT
- 自愈重试：最多 2 次重试（stale_session, timeout）
- 熔断器：连续 3 次失败开启熔断

```python
policy = DegradationPolicy()
level = policy.check_context_budget(prompt_tokens=100_000, context_tokens=80_000)
# level: FULL | TRUNCATED | ABORT
```

### A4: EventAuditLog 调用审计

**核心功能:**
- 按日期分片的 NDJSON 日志
- 事件类型：CAT_INVOKED, CAT_RESPONDED, CAT_ERROR, A2A_HANDOFF, CLI_TIMEOUT
- 查询接口：by thread, by cat, by time range

```python
audit = EventAuditLog(log_dir="data/audit")
audit.append(AuditEvent(
    event_type=AuditEventType.CAT_INVOKED,
    thread_id="t1",
    cat_id="opus",
    timestamp=time.time(),
))
```

### A5: Worklist 路由升级

**已存在于:** `src/collaboration/a2a_controller.py`

**核心功能:**
- `_serial_execute()` 改为 worklist 模式
- @mention 检测动态追加到 worklist
- max_depth=5 防止无限链
- Fairness gate：用户消息排队时不追加

---

## 测试覆盖

```
tests/invocation/test_queue.py       17 tests  ✓
tests/invocation/test_processor.py   15 tests  ✓
tests/invocation/test_degradation.py 23 tests  ✓
tests/invocation/test_audit.py       16 tests  ✓
tests/invocation/test_worklist.py    11 tests  ✓
tests/invocation/test_tracker.py      6 tests  ✓
tests/invocation/test_stream_merge.py 3 tests  ✓
-------------------------------------------------
Total: 97 tests passing
```

---

## 集成检查

- [x] 97 invocation 测试全部通过
- [x] 全量回归测试 1151 通过
- [x] A2A Controller worklist 功能验证
- [x] 与现有 MCP 工具系统集成

---

## 下一步

Phase A (P0 核心差异) 完成。下一步可选:
- Phase B: Session 连续性 (TranscriptWriter, SessionManager, HandoffDigest)
- Phase C: MCP 工具系统增强
- Phase D: 配置系统升级

