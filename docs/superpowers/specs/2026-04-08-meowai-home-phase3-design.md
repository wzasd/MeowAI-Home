# MeowAI Home Phase 3 设计文档：智能协作系统

**Created**: 2026-04-08
**Status**: Draft
**Owner**: 首席铲屎官

---

## 目录

1. [Phase 3 概述](#1-phase-3-概述)
2. [Phase 3.1: Thread 多会话管理](#2-phase-31-thread-多会话管理)
3. [Phase 3.2: 会话持久化与恢复](#3-phase-32-会话持久化与恢复)
4. [Phase 3.3: Intent 解析与 A2A 协作](#4-phase-33-intent-解析与-a2a-协作)
5. [Phase 3.4: MCP 回调机制](#5-phase-34-mcp-回调机制)
6. [实施计划](#6-实施计划)

---

## 1. Phase 3 概述

### 1.1 目标

构建完整的三猫智能协作系统，实现多会话管理、持久化存储、智能协作模式。

### 1.2 分阶段规划

```
Phase 3.1 ──→ Phase 3.2 ──→ Phase 3.3 ──→ Phase 3.4
Thread管理    持久化存储    A2A协作      MCP回调
 内存+JSON    SQLite       #ideate      猫主动@
             --resume     #execute     异步消息
```

---

## 2. Phase 3.1: Thread 多会话管理

### 2.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI 用户输入                              │
│         meowai thread create "项目A"                         │
│         meowai thread list                                   │
│         meowai thread switch <id>                            │
│         meowai chat  (使用当前 thread)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ThreadManager (单例)                            │
│  - 内存存储: Dict[thread_id, Thread]                        │
│  - JSON 持久化: ~/.meowai/threads.json                      │
│  - 当前 thread 追踪                                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Chat 流程 (使用当前 Thread)                      │
│  1. 读取 thread.messages 作为历史                            │
│  2. 构建 system prompt (猫的人设)                            │
│  3. 调用 Claude CLI 并解析响应                                │
│  4. 保存 thread 到 JSON                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据模型

```python
@dataclass
class Message:
    role: str              # "user" | "assistant"
    content: str
    cat_id: Optional[str]  # 如果是猫回复，记录是哪只
    timestamp: datetime

@dataclass
class Thread:
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message]
    current_cat_id: str    # 默认使用的猫 (@dev→orange)
    is_archived: bool = False
```

### 2.3 CLI 命令

```bash
# Thread 管理
meowai thread create "项目A" [--cat @dev]     # 创建并切换
meowai thread list                              # 列出所有 threads
meowai thread switch <id>                       # 切换到指定 thread
meowai thread rename <id> "新名称"              # 重命名
meowai thread delete <id> [--force]             # 删除
meowai thread archive <id>                      # 归档

# Chat 使用当前 thread
meowai chat                                     # 进入交互模式
meowai chat "一次性消息"                        # 单条消息

# 显示当前状态
meowai status                                   # 显示当前 thread、猫
```

### 2.4 存储策略

- **运行时**: 内存 Dict
- **退出时**: 保存到 `~/.meowai/threads.json`
- **启动时**: 从 JSON 加载
- **Phase 3.2 迁移**: SQLite

### 2.5 上下文传递

- 完整历史传递给 CLI
- 每条消息包含角色、内容、猫ID、时间戳
- 类似 Claude Code `--resume` 行为

---

## 3. Phase 3.2: 会话持久化与恢复

### 3.1 目标

- 可靠的长期存储
- 快速启动恢复
- 历史搜索能力

### 3.2 SQLite Schema

```sql
-- threads 表
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_cat_id TEXT NOT NULL,
    is_archived BOOLEAN DEFAULT FALSE
);

-- messages 表
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    cat_id TEXT,  -- NULL for user
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

-- 索引
CREATE INDEX idx_messages_thread ON messages(thread_id, timestamp);
CREATE INDEX idx_threads_updated ON threads(updated_at DESC);
```

### 3.3 恢复机制

```bash
meowai chat --resume                    # 恢复上次会话
meowai chat --resume --thread <id>      # 恢复指定会话
```

### 3.4 归档策略

- 自动归档：30 天无活动的 thread
- 归档后保留在数据库，但默认不显示
- `meowai thread list --all` 显示全部

---

## 4. Phase 3.3: Intent 解析与 A2A 协作

### 4.1 Intent 类型

```
#ideate     → 并行独立思考（多猫同时回答同一问题）
#execute    → 串行执行（多猫按顺序接力完成）
#critique   → 批判性分析（思维方式标签）
```

### 4.2 自动推断规则

```python
if explicit_intent:
    return explicit_intent
elif cat_count >= 2:
    return 'ideate'  # 多猫默认并行
else:
    return 'execute'  # 单猫默认执行
```

### 4.3 A2A 协作模式

**并行模式 (ideate)**:
```
用户: @dev @review 这个架构怎么样？#ideate
阿橘: （独立给出架构建议）
墨点: （独立给出审查意见）
```

**串行模式 (execute)**:
```
用户: @dev @review 实现这个功能 #execute
阿橘: （实现代码）
      ↓ 自动 @review
墨点: （审查代码）
      ↓ 自动 @dev（如有修改意见）
阿橘: （修复）
```

### 4.4 IntentParser 实现

```python
class IntentParser:
    def parse(self, message: str, cat_count: int) -> IntentResult:
        tags = self._extract_tags(message)  # #ideate, #execute, #critique
        intent = self._determine_intent(tags, cat_count)
        return IntentResult(
            intent=intent,
            explicit=bool(tags.intent_tag),
            prompt_tags=tags.prompt_tags
        )

    def strip_tags(self, message: str) -> str:
        # 移除 intent tags 后返回干净消息
```

---

## 5. Phase 3.4: MCP 回调机制

### 5.1 目标

- 猫可以主动 @其他猫
- 异步消息处理
- 支持工具调用

### 5.2 回调工具

```python
# MCP 工具描述
cat_cafe_post_message = {
    "name": "cat_cafe_post_message",
    "description": "向指定猫或用户发送异步消息",
    "parameters": {
        "target": "@dev | @review | @research | @user",
        "content": "消息内容",
        "thread_id": "可选，指定 thread"
    }
}
```

### 5.3 回调流程

```
阿橘正在写代码
    ↓
发现需要审查 → 调用 cat_cafe_post_message(@review, "请审查这段代码")
    ↓
系统接收回调 → 触发墨点响应
    ↓
墨点审查完成 → 调用 cat_cafe_post_message(@dev, "修复意见...")
```

### 5.4 消息队列

```python
class CallbackQueue:
    """异步回调队列"""
    def enqueue(self, callback: CallbackMessage):
        pass

    def process_next(self) -> Optional[Response]:
        pass
```

---

## 6. 实施计划

### 6.1 Phase 3.1 任务清单

| Task | 描述 | 预估时间 |
|------|------|----------|
| 3.1.1 | Thread 数据模型 | 30 分钟 |
| 3.1.2 | ThreadManager 实现 | 1.5 小时 |
| 3.1.3 | Thread CLI 命令 | 1 小时 |
| 3.1.4 | Chat 集成 Thread | 1 小时 |
| 3.1.5 | JSON 持久化 | 30 分钟 |
| 3.1.6 | 测试和文档 | 1 小时 |

**Phase 3.1 总预估**: ~5.5 小时

### 6.2 依赖关系

```
Phase 3.1 (Thread管理)
    │
    ├─→ Phase 3.2 (持久化)
    │      └─→ Phase 3.4 (MCP回调需要存储)
    │
    └─→ Phase 3.3 (A2A协作)
```

### 6.3 成功标准

**Phase 3.1**:
- ✅ 创建/列出/切换/删除/归档 thread
- ✅ Chat 使用当前 thread 的上下文
- ✅ JSON 持久化工作正常
- ✅ 所有测试通过

**Phase 3.2**:
- ✅ SQLite 存储替换 JSON
- ✅ --resume 恢复会话
- ✅ 历史搜索功能

**Phase 3.3**:
- ✅ #ideate 多猫并行
- ✅ #execute 多猫串行
- ✅ Intent 自动推断

**Phase 3.4**:
- ✅ 猫主动 @其他猫
- ✅ 异步消息处理
- ✅ 协作工作流闭环

---

**文档结束**

*本文档将随项目演进而持续更新。*
