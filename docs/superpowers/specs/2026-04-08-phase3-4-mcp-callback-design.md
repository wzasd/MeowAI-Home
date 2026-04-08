# Phase 3.4: MCP 回调机制设计文档

> **Status**: design | **Owner**: Claude Sonnet 4.6
> **Created**: 2026-04-08

---

## 1. 目标

让猫在执行过程中能够调用外部工具（轻量级本地实现）。

**参考项目**: Clowder AI MCP Callbacks 机制

---

## 2. 背景

### 2.1 当前状态 (Phase 3.3)
- A2A 协作已实现（并行 ideate / 串行 execute）
- 猫通过文本 @mention 进行协作
- 协作模式清晰但依赖文本解析

### 2.2 问题
- 文本 @mention 容易出错（格式不标准、忘记换行）
- 猫无法主动调用工具获取信息
- 无法结构化声明下一个回复者

### 2.3 解决方案
引入 MCP（Model Context Protocol）回调机制，让猫能够：
1. 调用工具（搜索文件、发送消息）
2. 结构化声明 targetCats（替代文本 @mention）

---

## 3. 架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    A2AController                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   猫 A       │───▶│  MCPClient   │◀───│   猫 B       │  │
│  │  (阿橘)      │    │  (回调中心)   │    │  (墨点)      │  │
│  └──────────────┘    └──────┬───────┘    └──────────────┘  │
│                             │                               │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │   工具注册表     │                      │
│                    │  - post_message │                      │
│                    │  - search_files │                      │
│                    │  - targetCats   │                      │
│                    └─────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心组件

#### 3.2.1 MCPClient

**职责**: 工具注册和调用的中心枢纽

**设计要点**:
- 单例模式（简化实现，所有猫共享）
- 轻量级本地调用（非 HTTP）
- 工具结果返回给调用者

**接口**:
```python
class MCPClient:
    def register_tool(self, name: str, handler: Callable) -> None
    async def call(self, tool_name: str, params: Dict) -> MCPResult
    def get_available_tools(self) -> List[str]
```

#### 3.2.2 工具集 (Phase 3.4)

| 工具名 | 功能 | 参数 | 返回值 |
|--------|------|------|--------|
| `post_message` | 发送消息到当前 thread | `content: str` | `message_id: str` |
| `search_files` | 搜索项目文件 | `query: str, path: str` | `matches: List[Match]` |
| `targetCats` | 声明下一个回复的猫 | `cats: List[str]` | `routing_info: Dict` |

**TODO(v0.4.0)**: 添加更多工具
- `update_task` - 更新任务状态
- `request_permission` - 请求用户确认
- `get_thread_context` - 获取 thread 历史

#### 3.2.3 targetCats 结构化路由

**替代文本 @mention**，猫在回调中声明下一个回复者：

```python
# 猫的回调响应
{
    "content": "我发现问题了...",
    "targetCats": ["inky", "patch"]  # 接下来墨点和花花回复
}
```

**路由优先级**:
1. **第一层**: targetCats 结构化字段（MCP 声明，最可靠）
2. **第二层**: 文本 @mention 解析（过渡期 fallback）

---

## 4. 与现有代码集成

### 4.1 修改点

#### 4.1.1 A2AController._call_cat()

**修改内容**:
1. 创建 MCPClient 实例注入到系统提示
2. 猫通过 MCPClient 调用工具
3. 收集回调结果（包括 targetCats）
4. 根据 targetCats 调整后续路由

**伪代码**:
```python
async def _call_cat(self, service, name, breed_id, message, thread):
    # 1. 创建 MCPClient
    mcp_client = MCPClient(thread)
    mcp_client.register_tool("post_message", post_message_handler)
    mcp_client.register_tool("search_files", search_files_handler)
    mcp_client.register_tool("targetCats", target_cats_handler)

    # 2. 构建系统提示（注入 MCP 工具描述）
    system_prompt = service.build_system_prompt()
    system_prompt += mcp_client.build_tools_prompt()  # 添加工具说明

    # 3. 调用猫服务
    response = await service.chat(message, system_prompt)

    # 4. 解析回调（提取工具调用和 targetCats）
    callbacks = parse_callbacks(response)

    # 5. 执行工具调用
    for callback in callbacks:
        result = await mcp_client.call(callback.tool, callback.params)

    # 6. 返回处理后的响应
    return CatResponse(
        cat_id=breed_id,
        cat_name=name,
        content=callbacks.clean_content,  # 移除回调标记的干净内容
        targetCats=callbacks.targetCats   # 结构化路由信息
    )
```

#### 4.1.2 CatResponse 扩展

```python
@dataclass
class CatResponse:
    cat_id: str
    cat_name: str
    content: str
    targetCats: Optional[List[str]] = None  # 新增：结构化路由
```

### 4.2 回调格式

**猫在回复中嵌入回调**:

```markdown
我来帮你查找相关资料。

<mcp:search_files>
{"query": "class A2AController", "path": "src/collaboration"}
</mcp:search_files>

<mcp:targetCats>
{"cats": ["inky"]}
</mcp:targetCats>

找到问题了！在 a2a_controller.py 第 42 行...
```

**解析后**:
- 干净内容: "我来帮你查找相关资料。\n\n找到问题了！在 a2a_controller.py 第 42 行..."
- 工具调用: search_files
- targetCats: ["inky"]

---

## 5. 数据结构

### 5.1 MCPResult

```python
@dataclass
class MCPResult:
    success: bool
    tool_name: str
    data: Any
    error: Optional[str] = None
```

### 5.2 MCPTool

```python
@dataclass
class MCPTool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    handler: Callable
```

### 5.3 CallbackParseResult

```python
@dataclass
class CallbackParseResult:
    clean_content: str          # 移除回调标记的干净内容
    tool_calls: List[ToolCall]  # 工具调用列表
    targetCats: List[str]       # 结构化路由
```

---

## 6. 接口设计

### 6.1 MCPClient

```python
class MCPClient:
    """MCP 回调客户端（轻量级本地实现）"""

    def __init__(self, thread: Thread):
        self.thread = thread
        self._tools: Dict[str, MCPTool] = {}

    def register_tool(self, name: str, description: str,
                     parameters: Dict, handler: Callable) -> None:
        """注册工具"""

    async def call(self, tool_name: str, params: Dict) -> MCPResult:
        """调用工具"""

    def build_tools_prompt(self) -> str:
        """构建工具说明（注入系统提示）"""

    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
```

### 6.2 工具处理器

```python
# post_message
async def handle_post_message(thread: Thread, content: str) -> MCPResult:
    """发送消息到当前 thread"""
    thread.add_message("assistant", content)
    return MCPResult(success=True, tool_name="post_message", data={"status": "sent"})

# search_files
async def handle_search_files(query: str, path: str = ".") -> MCPResult:
    """搜索项目文件"""
    matches = await grep_search(query, path)
    return MCPResult(success=True, tool_name="search_files", data=matches)

# targetCats
async def handle_target_cats(cats: List[str]) -> MCPResult:
    """声明下一个回复的猫"""
    return MCPResult(success=True, tool_name="targetCats", data={"targetCats": cats})
```

---

## 7. 测试策略

### 7.1 单元测试

| 测试 | 描述 |
|------|------|
| `test_mcp_client_register_tool` | 测试工具注册 |
| `test_mcp_client_call_tool` | 测试工具调用 |
| `test_post_message_tool` | 测试 post_message 工具 |
| `test_search_files_tool` | 测试 search_files 工具 |
| `test_target_cats_tool` | 测试 targetCats 工具 |
| `test_callback_parser` | 测试回调解析 |
| `test_target_cats_routing` | 测试结构化路由 |

### 7.2 集成测试

| 测试 | 描述 |
|------|------|
| `test_mcp_in_a2a_flow` | 测试 MCP 在 A2A 流程中的集成 |
| `test_targetCats_fallback_to_mention` | 测试路由 fallback |

---

## 8. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 猫不理解 MCP 格式 | Phase 1 保留文本 @mention fallback |
| 工具调用失败影响回复 | 错误隔离，失败不影响主流程 |
| 回调格式解析错误 | 严格格式验证，失败时返回原始内容 |

---

## 9. TODO 列表（后期迭代）

### v0.4.0（下一阶段）
- [ ] 迁移到 HTTP-based MCP Server
- [ ] 支持异步工具调用（工具执行不阻塞猫回复）
- [ ] 添加更多工具（update_task, request_permission, get_thread_context）
- [ ] 支持外部工具注册（插件机制）

### v0.5.0（远期）
- [ ] 支持工具权限控制
- [ ] 工具调用审计日志
- [ ] 工具性能监控

---

## 10. 验收标准

- [ ] AC-1: MCPClient 支持工具注册和调用
- [ ] AC-2: post_message 工具正常工作
- [ ] AC-3: search_files 工具正常工作
- [ ] AC-4: targetCats 结构化路由正常工作
- [ ] AC-5: 文本 @mention 作为 fallback 保留
- [ ] AC-6: 所有单元测试通过
- [ ] AC-7: 集成测试通过

---

## 11. 依赖

- **依赖**: Phase 3.3（A2A Controller）
- **阻塞**: 无

---

*Phase 3.4，让猫猫拥有超能力！* 🐱
