# Phase 7: 高级协作与工作流系统 (v0.7.0) — 设计规格

> **日期**: 2026-04-09
> **前置**: Phase 6 多模型支持 (v0.6.0) 已完成
> **范围**: Phase 6 基础设施接入 + 轻量 DAG 工作流引擎

---

## 目标

1. 将 Phase 6 已实现但未接入的 4 个模块（AgentRouterV2、InvocationTracker、StreamMerge、SessionChain）接入 WebSocket 活跃流程
2. 重构 A2AController 为更清晰的协调器（提取 MCP 执行和技能注入为独立辅助类）
3. 构建轻量 DAG 工作流引擎，支持 3 种工作流模板：头脑风暴+汇总、并行分工+合并、LLM 自动规划

## 架构方案

**方案 A: 最小 DAG 核心模式**

核心只做 3 件事：定义 DAG → 调度执行 → 聚合结果。没有状态机、没有 SOP Bulletin Board、没有 Lease 锁。复用 Phase 6 已有的 Provider、SessionChain、InvocationTracker 等基础设施。

---

## 第1节：Phase 6 基础设施接入

### 1.1 AgentRouterV2 替换 AgentRouter v1

**文件变更**:
- `src/router/__init__.py` — 改为导出 `AgentRouterV2`
- `src/web/routes/ws.py` — `agent_router` 改为 `AgentRouterV2` 实例
- `src/web/app.py` — lifespan 中初始化 `AgentRouterV2` 传入 `cat_registry` 和 `agent_registry`

**行为**:
- 使用 `cat_registry.get_by_mention()` 替代 v1 的 config 直接读取
- 保持 `route_message()` 返回 `[{breed_id, name, service}, ...]` 格式不变
- 支持中文/日文 @mention（已实现）

### 1.2 InvocationTracker 接入 WebSocket

**文件变更**:
- `src/web/routes/ws.py` — 在 `_handle_send_message` 中集成 tracker
- `src/web/app.py` — 在 state 中挂载 `InvocationTracker` 实例

**行为**:
- 每次调用 agent 前执行 `tracker.start(thread_id, cat_id)`
- 新消息到来时，自动 cancel 同 slot 的旧 invocation
- `done` 事件后 `tracker.complete(thread_id, cat_id)`

### 1.3 StreamMerge 替换 asyncio.as_completed

**文件变更**:
- `src/collaboration/a2a_controller.py` — `_parallel_ideate` 改用 `merge_streams()`

**行为**:
- 创建 `AsyncIterator` 流列表（每个 agent 的 `_call_cat_stream`）
- 调用 `merge_streams(streams, on_error=...)` 合并输出
- 统一流式输出格式，错误隔离（一个 agent 失败不影响其他）

### 1.4 SessionChain 接入 _call_cat

**文件变更**:
- `src/collaboration/a2a_controller.py` — `_call_cat` 中集成 SessionChain
- `src/web/app.py` — 在 state 中挂载 `SessionChain` 实例

**行为**:
- 调用 Provider 前检查 `chain.get_active(cat_id, thread_id)`
- 如果有活跃 session，传 `session_id` 给 Provider 的 `--resume` 参数
- 调用完成后 `chain.create(cat_id, thread_id, new_session_id)`
- `should_auto_seal()` 为 true 时 `chain.seal()` 并创建新 session

### 1.5 A2AController 重构

**当前问题**: 333 行，混杂路由、执行、MCP、技能注入 4 种职责。

**重构方案**:

提取 `MCPExecutor` 辅助类（`src/collaboration/mcp_executor.py`）:
- `register_tools(thread)` — 注册 TOOL_REGISTRY 中的工具到 MCPClient
- `execute_callbacks(raw_content, thread)` — 解析并执行 MCP 回调
- `build_tools_prompt()` — 生成工具说明文本

提取 `SkillInjector` 辅助类（`src/collaboration/skill_injector.py`）:
- `inject(agents, skill_id)` — 为 agents 注入技能上下文
- `restore(agents)` — 恢复原始 build_system_prompt
- `load_skill(skill_id)` — 加载技能内容

重构后 A2AController 约 150 行，只保留协调逻辑。

---

## 第2节：轻量 DAG 工作流引擎

### 2.1 核心数据结构 (`src/workflow/dag.py`)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DAGNode:
    id: str                      # 唯一标识，如 "brainstorm_1"
    cat_id: str                  # 执行的猫 ID，如 "orange"
    prompt_template: str         # 提示词模板，支持 {input}, {prev_results} 变量
    role: str = ""               # 角色描述（注入系统提示）
    is_aggregator: bool = False  # 是否为汇总节点

@dataclass
class DAGEdge:
    from_node: str               # 源节点 ID
    to_node: str                 # 目标节点 ID

@dataclass
class WorkflowDAG:
    nodes: List[DAGNode]
    edges: List[DAGEdge]

    def roots(self) -> List[str]:
        """返回无入度的节点（起始点）"""

    def successors(self, node_id: str) -> List[str]:
        """返回后继节点 ID 列表"""

    def predecessors(self, node_id: str) -> List[str]:
        """返回前驱节点 ID 列表"""

    def validate(self) -> List[str]:
        """验证 DAG：检测环、孤立节点、缺失引用。返回错误列表"""

    def topological_layers(self) -> List[List[str]]:
        """返回拓扑分层，每层节点可并行执行"""

@dataclass
class NodeResult:
    node_id: str
    cat_id: str
    content: str
    status: str                  # "completed" | "failed" | "skipped"
    thinking: Optional[str] = None
    error: Optional[str] = None
```

### 2.2 DAG 执行器 (`src/workflow/executor.py`)

```python
class DAGExecutor:
    def __init__(self, agent_registry, session_chain=None, tracker=None):
        self.agent_registry = agent_registry
        self.session_chain = session_chain
        self.tracker = tracker

    async def execute(
        self,
        dag: WorkflowDAG,
        input_text: str,
        thread: Thread
    ) -> AsyncIterator[NodeResult]:
        """
        执行 DAG：
        1. 验证 DAG
        2. 拓扑排序为层级
        3. 按层级执行（同层并行）
        4. 节点间传递前驱结果
        5. yield 每个节点结果
        """
```

**关键行为**:
- 使用 `topological_layers()` 获取层级
- 同层节点通过 `merge_streams` 并行执行
- 每个节点的 `prompt_template` 用 `{input}` 替换为原始输入，`{prev_results}` 替换为前驱节点结果
- 节点失败标记 `status="failed"`，后继节点仍可尝试执行
- 汇总节点（`is_aggregator=True`）自动接收所有前驱结果

### 2.3 结果聚合器 (`src/workflow/aggregator.py`)

```python
class ResultAggregator:
    @staticmethod
    def aggregate(results: List[NodeResult], mode: str = "summarize") -> str:
        """
        聚合模式：
        - summarize: 用汇总节点的猫生成综合摘要
        - merge: 拼接各节点输出为一段文字
        - last: 取最后一个成功节点的结果
        """
```

### 2.4 工作流模板 (`src/workflow/templates.py`)

**预定义模板**:

1. **brainstorm（头脑风暴+汇总）**:
   - N 个并行 root 节点（每只猫独立思考）
   - 1 个汇总节点（聚合猫总结所有结果）
   - `DAGEdge` 从每个思考节点指向汇总节点

2. **parallel（并行分工+合并）**:
   - N 个并行节点（每只猫收到不同的分工 prompt）
   - 1 个合并节点
   - 每个并行节点的 prompt 包含具体分工指令

3. **auto_plan（LLM 自动规划）**:
   - 1 个规划节点（使用 agents 列表中的第一只猫作为规划者）
   - 规划者收到的 prompt 要求输出结构化 JSON
   - JSON 格式：`{nodes: [{id, cat_id, prompt}], edges: [{from, to}]}`
   - 系统解析 JSON 构建 DAG，继续执行
   - 如果 JSON 解析失败，降级为 brainstorm 模板（使用原 agents 列表）

**模板工厂**:

```python
class WorkflowTemplateFactory:
    @staticmethod
    def create(template_name: str, cats: List[Dict], message: str) -> WorkflowDAG:
        """根据模板名和猫列表创建 DAG"""

    @staticmethod
    def from_yaml(path: str) -> WorkflowDAG:
        """从 YAML 文件加载自定义 DAG"""
```

**YAML 自定义模板格式**:
```yaml
name: code_review_pipeline
description: "代码审查流水线"
nodes:
  - id: implement
    cat_id: orange
    prompt_template: "实现以下功能：{input}"
    role: "开发者"
  - id: review
    cat_id: inky
    prompt_template: "审查以下代码：{prev_results}"
    role: "审查者"
    is_aggregator: true
edges:
  - from: implement
    to: review
```

**DAGExecutor 调用路径**:
DAGExecutor 通过 `agent_registry.get(node.cat_id)` 获取 service 实例，直接调用 `service.chat_stream(prompt, system_prompt)`。复用 `MCPExecutor` 辅助类处理工具注册和回调解析，但不通过 A2AController 的 `_call_cat`（避免循环依赖）。

---

## 第3节：集成层

### 3.1 Workflow 意图检测

扩展 `IntentResult` 和 `IntentParser`:

```python
@dataclass
class IntentResult:
    intent: str                  # "ideate" | "execute" | "workflow"
    explicit: bool
    prompt_tags: List[str]
    clean_message: str
    workflow: Optional[str] = None  # "brainstorm" | "parallel" | "auto_plan"
```

触发规则:
- `#brainstorm` 标签 → `workflow="brainstorm"`
- `#parallel` 标签 → `workflow="parallel"`
- `#autoplan` 标签 或 `@planner` mention → `workflow="auto_plan"`
- 3+ 只猫参与且无显式 intent → 默认 `workflow="brainstorm"`

### 3.2 A2AController 集成

```python
class A2AController:
    def __init__(self, agents, dag_executor=None, template_factory=None):
        ...
        self.dag_executor = dag_executor
        self.template_factory = template_factory

    async def execute(self, intent, message, thread):
        # 新增：workflow 路径
        if intent.workflow:
            dag = self.template_factory.create(
                intent.workflow, self.agents, message
            )
            async for result in self.dag_executor.execute(dag, message, thread):
                yield self._to_cat_response(result)
            return

        # 原有 ideate/execute 路径...
```

### 3.3 WebSocket 协议扩展

新增事件类型:

| 事件 | 方向 | 用途 |
|------|------|------|
| `workflow_start` | server→client | 通知工作流开始，包含工作流名和节点图 |
| `node_start` | server→client | 通知节点开始执行 |
| `cat_response` | server→client | 复用现有，增加 `node_id` 字段 |
| `workflow_done` | server→client | 工作流完成通知 |
| `workflow_error` | server→client | 工作流错误 |

### 3.4 文件结构

```
src/
├── workflow/
│   ├── __init__.py              # 导出 DAGExecutor, WorkflowDAG, WorkflowTemplateFactory
│   ├── dag.py                   # DAGNode, DAGEdge, WorkflowDAG, NodeResult
│   ├── executor.py              # DAGExecutor
│   ├── aggregator.py            # ResultAggregator
│   └── templates.py             # WorkflowTemplateFactory + 3 个预定义模板
├── collaboration/
│   ├── a2a_controller.py        # 重构后 ~150 行，核心协调
│   ├── mcp_executor.py          # 提取：MCP 工具注册和执行
│   ├── skill_injector.py        # 提取：技能上下文注入
│   ├── intent_parser.py         # 扩展：workflow 意图检测
│   ├── callback_parser.py       # 不变
│   ├── mcp_client.py            # 不变
│   ├── mcp_tools.py             # 不变
│   └── mcp_memory.py            # 不变
├── router/
│   └── __init__.py              # 改为导出 AgentRouterV2
├── session/
│   └── chain.py                 # 不变
├── invocation/
│   ├── tracker.py               # 不变
│   └── stream_merge.py          # 不变
└── web/
    ├── app.py                   # 扩展 lifespan：挂载新组件
    └── routes/ws.py             # 集成 tracker + workflow 事件
```

测试文件:
```
tests/
├── workflow/
│   ├── test_dag.py              # DAG 数据结构测试（拓扑排序、环检测）
│   ├── test_executor.py         # DAG 执行器测试（并行/串行执行）
│   ├── test_aggregator.py       # 结果聚合测试
│   └── test_templates.py        # 模板工厂测试
├── collaboration/
│   ├── test_mcp_executor.py     # MCP 执行器单元测试
│   └── test_skill_injector.py   # 技能注入器单元测试
└── web/
    └── test_ws_workflow.py      # WebSocket workflow 集成测试
```

---

## 非目标（明确排除）

- SOP Bulletin Board / 工作流状态机
- Lease 锁 / 分布式协调
- ResumeCapsule 断点续传
- 死信队列 / 重试策略
- 速率限制 / 成本控制
- 工作流持久化（重启后恢复）

这些留待后续 Phase 根据需要渐进增加。

---

## 成功标准

1. Phase 6 的 4 个模块全部接入活跃流程
2. 3 种工作流模板可从 WebSocket 触发并正确执行
3. 重构后 307 个现有测试全部通过
4. 新增测试覆盖所有新模块
5. WebSocket 协议向后兼容（不破坏现有前端）
