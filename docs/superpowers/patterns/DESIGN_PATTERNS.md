# MeowAI Home 设计范式

> **记录系统的设计原则、架构模式和最佳实践**
>
> **Last Updated**: 2026-04-08

---

## 核心设计原则

### 1. 开源优先 (Open Source First)

**原则**: 所有核心功能必须开源，商业版只提供增值服务

**理由**:
- 建立社区信任
- 吸引贡献者
- 加速迭代
- 降低用户采用门槛

**应用**:
- ✅ 核心引擎 (MIT 协议)
- ✅ 基础技能和工具
- ✅ 文档和示例
- ⚠️ 企业级功能 (商业版)

**反例**:
- ❌ 核心功能闭源
- ❌ 开源版功能阉割

---

### 2. 渐进式复杂度 (Progressive Complexity)

**原则**: 入门简单，高级功能按需解锁

**理由**:
- 降低学习曲线
- 快速上手
- 减少认知负担
- 按需深入

**应用**:
```
L1: 单猫对话 (5 分钟上手)
  ↓
L2: 多猫协作 (自动推断模式)
  ↓
L3: MCP 工具调用 (按需启用)
  ↓
L4: 自定义技能 (高级用户)
  ↓
L5: 工作流编排 (企业用户)
```

**实现**:
- 默认配置合理
- 高级配置可选
- 分层文档 (快速开始 → 深入指南)
- 示例项目分级

**反例**:
- ❌ 所有功能一视同仁
- ❌ 强制配置复杂选项

---

### 3. 零依赖部署 (Zero-Dependency Deploy)

**原则**: 核心功能无需外部依赖（Redis/PostgreSQL/Docker）

**理由**:
- 降低部署门槛
- 减少运维成本
- 提高可靠性
- 适合个人开发者

**应用**:
- ✅ SQLite 单机模式
- ✅ 文件存储
- ⚠️ Redis 集群模式（可选，用于高并发）
- ⚠️ PostgreSQL（可选，用于企业版）

**实现**:
```python
# 默认配置
STORAGE_BACKEND = "sqlite"
DATABASE_URL = "~/.meowai/meowai.db"

# 可选配置（高可用）
STORAGE_BACKEND = "redis+postgresql"
REDIS_URL = "redis://localhost:6379"
DATABASE_URL = "postgresql://..."
```

**反例**:
- ❌ 强制依赖 Redis
- ❌ 强制使用 Docker

---

### 4. 声明式配置 (Declarative Configuration)

**原则**: 使用声明式配置，而非命令式脚本

**理由**:
- 配置可读性好
- 易于版本控制
- 支持验证和检查
- 幂等性（可重复执行）

**应用**:

**Agent 配置**:
```json
{
  "id": "orange",
  "name": "阿橘",
  "breed": "ragdoll",
  "model": "claude-sonnet-4-6",
  "role": "developer",
  "personality": "热情话唠、点子多",
  "skills": ["tdd", "refactor", "debug"]
}
```

**技能配置**:
```yaml
name: tdd
description: 测试驱动开发
triggers:
  - keywords: ["test", "测试", "tdd"]
  - intents: ["execute"]
handler: skills.tdd.execute
```

**工作流配置**:
```yaml
name: code-review
steps:
  - agent: developer
    action: write_code
  - agent: reviewer
    action: review_code
    condition: "code.changed"
```

**反例**:
- ❌ 大量脚本配置
- ❌ 命令式配置

---

### 5. 插件化架构 (Plugin Architecture)

**原则**: 核心功能最小化，扩展通过插件实现

**理由**:
- 核心稳定
- 易于扩展
- 降低耦合
- 社区贡献

**应用**:

**核心**:
- Agent 管理
- Thread 管理
- 消息路由
- 存储层

**插件**:
- 技能插件 (`skills/`)
- 工具插件 (`tools/`)
- 模型插件 (`models/`)
- 集成插件 (`integrations/`)

**实现**:
```python
# 插件注册
@skill("tdd")
class TDDSkill(Skill):
    def execute(self, context):
        # 技能实现
        pass

# 插件加载
skill_registry.register(TDDSkill)
```

**反例**:
- ❌ 所有功能内置
- ❌ 硬编码功能

---

### 6. 事件驱动 (Event-Driven)

**原则**: 组件间通过事件通信，而非直接调用

**理由**:
- 降低耦合
- 异步处理
- 易于扩展
- 审计日志

**应用**:

**事件类型**:
```python
# Agent 事件
AgentCreated
AgentActivated
AgentDeactivated

# Thread 事件
ThreadCreated
MessageAdded
ThreadArchived

# 工具事件
ToolInvoked
ToolCompleted
ToolFailed

# 协作事件
CollaborationStarted
AgentReplied
CollaborationEnded
```

**事件处理**:
```python
@event_handler(MessageAdded)
async def on_message_added(event):
    # 1. 持久化消息
    await store.save_message(event.message)

    # 2. 触发 Agent 响应
    await router.route(event.message)

    # 3. 更新统计
    await stats.increment("messages")
```

**反例**:
- ❌ 组件间直接调用
- ❌ 同步阻塞操作

---

### 7. 失败优雅 (Fail Gracefully)

**原则**: 任何失败都不应导致系统崩溃，提供降级方案

**理由**:
- 提高可靠性
- 用户体验好
- 易于调试
- 防止雪崩

**应用**:

**API 调用失败**:
```python
try:
    response = await model.chat(message)
except ModelAPIError as e:
    # 降级到备用模型
    logger.warning(f"Model {model} failed: {e}")
    response = await fallback_model.chat(message)
```

**工具调用失败**:
```python
try:
    result = await tool.execute(params)
except ToolError as e:
    # 返回错误信息，不中断流程
    logger.error(f"Tool {tool} failed: {e}")
    result = ToolResult(
        success=False,
        error=str(e),
        suggestion="请检查参数或稍后重试"
    )
```

**Agent 失败**:
```python
try:
    response = await agent.chat(message)
except AgentError as e:
    # 通知其他 Agent 接手
    await notify_other_agents(error=e, context=context)
```

**反例**:
- ❌ 未捕获异常导致崩溃
- ❌ 失败后无降级方案

---

### 8. 可观测性 (Observability)

**原则**: 系统状态必须可观测，提供完整的监控和诊断信息

**理由**:
- 快速定位问题
- 性能优化
- 容量规划
- 用户行为分析

**应用**:

**日志**:
```python
# 结构化日志
logger.info(
    "Agent replied",
    extra={
        "agent_id": agent.id,
        "thread_id": thread.id,
        "response_time": elapsed_ms,
        "tokens_used": response.usage.total_tokens
    }
)
```

**指标**:
```python
# Prometheus 指标
messages_total = Counter("messages_total", "Total messages")
response_time = Histogram("response_time_seconds", "Response time")
active_threads = Gauge("active_threads", "Active threads")
```

**追踪**:
```python
# 分布式追踪
with tracer.start_as_current_span("agent.chat") as span:
    span.set_attribute("agent.id", agent.id)
    span.set_attribute("message.length", len(message))
    response = await agent.chat(message)
    span.set_attribute("response.tokens", response.usage.total_tokens)
```

**反例**:
- ❌ 无日志或日志不完整
- ❌ 无法监控性能
- ❌ 无法追踪请求

---

## 架构模式

### 分层架构 (Layered Architecture)

```
┌─────────────────────────────────────┐
│         Presentation Layer          │
│  (CLI / Web UI / API / IDE Plugin)  │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│        Application Layer            │
│  (ThreadManager / AgentRouter /     │
│   CollaborationEngine / Workflow)   │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│          Domain Layer               │
│  (Agent / Thread / Message / Skill) │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│       Infrastructure Layer          │
│  (SQLiteStore / ModelClient / MCP)  │
└─────────────────────────────────────┘
```

**规则**:
- 上层依赖下层
- 下层不依赖上层
- 同层可依赖
- 跨层通过接口

---

### Repository Pattern (仓储模式)

**目的**: 隔离数据访问逻辑

**实现**:
```python
# 抽象接口
class ThreadRepository(ABC):
    @abstractmethod
    async def get(self, thread_id: str) -> Optional[Thread]:
        pass

    @abstractmethod
    async def save(self, thread: Thread) -> None:
        pass

# SQLite 实现
class SQLiteThreadRepository(ThreadRepository):
    async def get(self, thread_id: str) -> Optional[Thread]:
        # SQL 查询
        pass

# Redis 实现（可选）
class RedisThreadRepository(ThreadRepository):
    async def get(self, thread_id: str) -> Optional[Thread]:
        # Redis 查询
        pass
```

**好处**:
- 数据库无关
- 易于测试（Mock）
- 易于切换实现

---

### Strategy Pattern (策略模式)

**目的**: 动态选择算法/行为

**实现**:
```python
# 模型选择策略
class ModelSelectionStrategy(ABC):
    @abstractmethod
    def select(self, task: Task) -> Model:
        pass

class CostOptimizedStrategy(ModelSelectionStrategy):
    def select(self, task: Task) -> Model:
        # 选择成本最低的模型
        pass

class QualityOptimizedStrategy(ModelSelectionStrategy):
    def select(self, task: Task) -> Model:
        # 选择质量最高的模型
        pass

# 使用
strategy = CostOptimizedStrategy()
model = strategy.select(task)
```

**应用场景**:
- 模型选择
- 路由策略
- 任务调度

---

### Factory Pattern (工厂模式)

**目的**: 封装对象创建逻辑

**实现**:
```python
class AgentFactory:
    @staticmethod
    def create(config: AgentConfig) -> Agent:
        if config.breed == "ragdoll":
            return RagdollAgent(config)
        elif config.breed == "maine_coon":
            return MaineCoonAgent(config)
        else:
            raise ValueError(f"Unknown breed: {config.breed}")

# 使用
agent = AgentFactory.create(config)
```

**应用场景**:
- Agent 创建
- Skill 创建
- Tool 创建

---

### Observer Pattern (观察者模式)

**目的**: 事件通知

**实现**:
```python
class EventEmitter:
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, event_type: str, listener: Callable):
        self._listeners[event_type].append(listener)

    async def emit(self, event_type: str, data: Any):
        for listener in self._listeners[event_type]:
            await listener(data)

# 使用
event_emitter = EventEmitter()

@event_emitter.on("message_added")
async def on_message_added(message):
    await notify_agents(message)

await event_emitter.emit("message_added", message)
```

**应用场景**:
- 事件通知
- 状态变更
- 审计日志

---

## 代码规范

### 命名规范

**文件命名**:
```
模块: snake_case (agent_router.py)
测试: test_snake_case (test_agent_router.py)
配置: kebab-case (cat-config.json)
```

**类命名**:
```python
# PascalCase
class ThreadManager:
    pass

class SQLiteStore:
    pass
```

**函数/方法命名**:
```python
# snake_case
async def get_current_thread(self) -> Thread:
    pass

def calculate_response_time(self) -> float:
    pass
```

**常量命名**:
```python
# UPPER_SNAKE_CASE
MAX_MESSAGE_LENGTH = 10000
DEFAULT_TIMEOUT = 30
```

---

### 类型注解

**强制使用类型注解**:
```python
# ✅ 正确
async def get_thread(self, thread_id: str) -> Optional[Thread]:
    pass

# ❌ 错误
async def get_thread(self, thread_id):
    pass
```

**好处**:
- 代码可读性
- IDE 提示
- 类型检查
- 文档生成

---

### 文档字符串

**Google Style**:
```python
async def save_thread(self, thread: Thread) -> None:
    """保存 thread 到数据库

    Args:
        thread: 要保存的 thread 对象

    Raises:
        StorageError: 如果保存失败

    Example:
        >>> thread = Thread.create("测试")
        >>> await store.save_thread(thread)
    """
    pass
```

---

### 错误处理

**使用自定义异常**:
```python
class MeowAIError(Exception):
    """基础异常"""
    pass

class StorageError(MeowAIError):
    """存储错误"""
    pass

class AgentError(MeowAIError):
    """Agent 错误"""
    pass

# 使用
if not thread:
    raise StorageError(f"Thread {thread_id} not found")
```

---

## 测试规范

### 测试金字塔

```
        /\
       /  \  E2E Tests (10%)
      /────\
     /      \ Integration Tests (20%)
    /────────\
   /          \ Unit Tests (70%)
  /────────────\
```

### 测试命名

```python
def test_<功能>_<场景>_<预期结果>():
    pass

# 示例
def test_get_thread_existing_id_returns_thread():
    pass

def test_get_thread_nonexistent_id_returns_none():
    pass
```

### AAA 模式

```python
def test_save_thread():
    # Arrange (准备)
    thread = Thread.create("测试")

    # Act (执行)
    await store.save_thread(thread)

    # Assert (断言)
    loaded = await store.get_thread(thread.id)
    assert loaded == thread
```

---

## 性能优化

### 异步优先

**原则**: 所有 I/O 操作使用 async/await

**实现**:
```python
# ✅ 正确
async def get_thread(self, thread_id: str) -> Thread:
    async with aiosqlite.connect(self.db_path) as db:
        # 异步查询
        pass

# ❌ 错误
def get_thread(self, thread_id: str) -> Thread:
    with sqlite3.connect(self.db_path) as db:
        # 同步查询
        pass
```

---

### 延迟加载

**原则**: 只在需要时加载数据

**实现**:
```python
class Thread:
    def __init__(self, id: str):
        self.id = id
        self._messages = None

    @property
    async def messages(self) -> List[Message]:
        if self._messages is None:
            self._messages = await self._load_messages()
        return self._messages
```

---

### 分页查询

**原则**: 大数据集使用分页

**实现**:
```python
async def get_messages(
    self,
    thread_id: str,
    page: int = 1,
    page_size: int = 50
) -> List[Message]:
    offset = (page - 1) * page_size
    async with aiosqlite.connect(self.db_path) as db:
        cursor = await db.execute(
            "SELECT * FROM messages WHERE thread_id = ? "
            "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            (thread_id, page_size, offset)
        )
        return await cursor.fetchall()
```

---

## 安全规范

### 输入验证

**原则**: 所有外部输入必须验证

**实现**:
```python
from pydantic import BaseModel, validator

class MessageInput(BaseModel):
    content: str

    @validator("content")
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        if len(v) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message too long (max {MAX_MESSAGE_LENGTH})")
        return v
```

---

### 权限检查

**原则**: 每个操作检查权限

**实现**:
```python
async def delete_thread(self, thread_id: str, user: User):
    # 检查权限
    if not await self.can_delete_thread(user, thread_id):
        raise PermissionError("You don't have permission to delete this thread")

    # 执行删除
    await self.store.delete_thread(thread_id)
```

---

### 敏感数据保护

**原则**: API Key 等敏感数据加密存储

**实现**:
```python
from cryptography.fernet import Fernet

class SecretManager:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

# 使用
secret_manager = SecretManager(SECRET_KEY)
encrypted_key = secret_manager.encrypt(api_key)
```

---

## 文档规范

### README 结构

```markdown
# Project Name

一句话介绍

## Features

核心功能列表

## Quick Start

5 分钟快速开始

## Installation

安装步骤

## Usage

基本使用方法

## Configuration

配置说明

## API Reference

API 文档链接

## Contributing

贡献指南

## License

开源协议
```

---

### API 文档

**使用 OpenAPI/Swagger**:
```yaml
openapi: 3.0.0
paths:
  /api/threads:
    get:
      summary: List all threads
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Thread'
```

---

## 持续改进

### 代码审查清单

- [ ] 类型注解完整
- [ ] 文档字符串完整
- [ ] 单元测试覆盖率 > 80%
- [ ] 无安全漏洞
- [ ] 性能测试通过
- [ ] 文档已更新
- [ ] CHANGELOG 已更新

---

### 技术债务管理

**原则**: 每个迭代预留 20% 时间处理技术债务

**流程**:
1. 记录技术债务 (GitHub Issues)
2. 评估优先级 (P0/P1/P2)
3. 每个迭代处理 2-3 个
4. 定期回顾

---

*持续优化，追求卓越！* 🚀

**Last Updated**: 2026-04-08
