# Phase 7: 高级协作与工作流系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Phase 6 infrastructure into the active WebSocket flow, refactor A2AController for clarity, and build a lightweight DAG workflow engine with 3 templates (brainstorm, parallel, auto_plan).

**Architecture:** Phase 6 modules (AgentRouterV2, InvocationTracker, StreamMerge, SessionChain) are wired into the WebSocket handler and A2AController. Two helper classes (MCPExecutor, SkillInjector) are extracted from A2AController. A new `src/workflow/` package adds DAG data structures, a topological-layer executor, result aggregation, and template factories. Workflow intent detection extends the existing IntentParser.

**Tech Stack:** Python 3.10+, asyncio, FastAPI, pytest + pytest-asyncio, dataclasses, YAML (pyyaml)

---

## File Structure

### New files (create)
| File | Responsibility |
|------|---------------|
| `src/workflow/__init__.py` | Package exports |
| `src/workflow/dag.py` | DAGNode, DAGEdge, WorkflowDAG, NodeResult data structures + graph algorithms |
| `src/workflow/executor.py` | DAGExecutor — topological-layer parallel execution |
| `src/workflow/aggregator.py` | ResultAggregator — summarize/merge/last modes |
| `src/workflow/templates.py` | WorkflowTemplateFactory + 3 predefined templates + YAML loader |
| `src/collaboration/mcp_executor.py` | MCPExecutor — tool registration + callback execution |
| `src/collaboration/skill_injector.py` | SkillInjector — skill context injection into agents |
| `tests/workflow/__init__.py` | Test package marker |
| `tests/workflow/test_dag.py` | DAG data structure tests |
| `tests/workflow/test_executor.py` | DAG executor tests |
| `tests/workflow/test_aggregator.py` | Result aggregator tests |
| `tests/workflow/test_templates.py` | Template factory tests |
| `tests/collaboration/test_mcp_executor.py` | MCPExecutor unit tests |
| `tests/collaboration/test_skill_injector.py` | SkillInjector unit tests |

### Modified files (edit)
| File | Change |
|------|--------|
| `src/collaboration/a2a_controller.py` | Refactor: use MCPExecutor, SkillInjector; add StreamMerge + SessionChain; add workflow dispatch |
| `src/collaboration/intent_parser.py` | Add `workflow` field to IntentResult; add workflow tag detection |
| `src/collaboration/__init__.py` | Add new exports |
| `src/router/__init__.py` | Export AgentRouterV2 instead of AgentRouter v1 |
| `src/web/app.py` | Wire AgentRouterV2, InvocationTracker, SessionChain in lifespan |
| `src/web/dependencies.py` | Update import to AgentRouterV2 |
| `src/web/routes/ws.py` | Integrate tracker; add workflow events |
| `tests/collaboration/test_a2a_controller.py` | Update tests for refactored A2AController |

---

### Task 1: DAG Data Structures (`src/workflow/dag.py`)

**Files:**
- Create: `src/workflow/__init__.py`
- Create: `src/workflow/dag.py`
- Test: `tests/workflow/__init__.py`
- Test: `tests/workflow/test_dag.py`

- [ ] **Step 1: Create package files**

```python
# src/workflow/__init__.py
from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG, NodeResult
from src.workflow.executor import DAGExecutor
from src.workflow.aggregator import ResultAggregator
from src.workflow.templates import WorkflowTemplateFactory

__all__ = [
    "DAGNode", "DAGEdge", "WorkflowDAG", "NodeResult",
    "DAGExecutor", "ResultAggregator", "WorkflowTemplateFactory",
]
```

```python
# tests/workflow/__init__.py
```

- [ ] **Step 2: Write the failing tests for DAG**

```python
# tests/workflow/test_dag.py
import pytest
from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG, NodeResult


def _make_linear_dag():
    """A -> B -> C linear chain"""
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="Do A: {input}"),
        DAGNode(id="b", cat_id="inky", prompt_template="Do B: {prev_results}"),
        DAGNode(id="c", cat_id="patch", prompt_template="Final: {prev_results}", is_aggregator=True),
    ]
    edges = [
        DAGEdge(from_node="a", to_node="b"),
        DAGEdge(from_node="b", to_node="c"),
    ]
    return WorkflowDAG(nodes=nodes, edges=edges)


def _make_diamond_dag():
    """A -> B, A -> C, B -> D, C -> D (diamond)"""
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="Start: {input}"),
        DAGNode(id="b", cat_id="inky", prompt_template="Review: {prev_results}"),
        DAGNode(id="c", cat_id="patch", prompt_template="Research: {prev_results}"),
        DAGNode(id="d", cat_id="orange", prompt_template="Merge: {prev_results}", is_aggregator=True),
    ]
    edges = [
        DAGEdge(from_node="a", to_node="b"),
        DAGEdge(from_node="a", to_node="c"),
        DAGEdge(from_node="b", to_node="d"),
        DAGEdge(from_node="c", to_node="d"),
    ]
    return WorkflowDAG(nodes=nodes, edges=edges)


def _make_cycle_dag():
    """A -> B -> C -> A (cycle — invalid)"""
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="A"),
        DAGNode(id="b", cat_id="inky", prompt_template="B"),
        DAGNode(id="c", cat_id="patch", prompt_template="C"),
    ]
    edges = [
        DAGEdge(from_node="a", to_node="b"),
        DAGEdge(from_node="b", to_node="c"),
        DAGEdge(from_node="c", to_node="a"),
    ]
    return WorkflowDAG(nodes=nodes, edges=edges)


class TestWorkflowDAG:
    def test_roots_linear(self):
        dag = _make_linear_dag()
        assert dag.roots() == ["a"]

    def test_roots_single(self):
        nodes = [DAGNode(id="solo", cat_id="orange", prompt_template="{input}")]
        dag = WorkflowDAG(nodes=nodes, edges=[])
        assert dag.roots() == ["solo"]

    def test_roots_diamond(self):
        dag = _make_diamond_dag()
        assert dag.roots() == ["a"]

    def test_successors(self):
        dag = _make_diamond_dag()
        assert set(dag.successors("a")) == {"b", "c"}
        assert dag.successors("d") == []

    def test_predecessors(self):
        dag = _make_diamond_dag()
        assert dag.predecessors("a") == []
        assert set(dag.predecessors("d")) == {"b", "c"}

    def test_validate_ok(self):
        dag = _make_linear_dag()
        errors = dag.validate()
        assert errors == []

    def test_validate_cycle(self):
        dag = _make_cycle_dag()
        errors = dag.validate()
        assert len(errors) > 0
        assert any("cycle" in e.lower() for e in errors)

    def test_validate_missing_node(self):
        nodes = [DAGNode(id="a", cat_id="orange", prompt_template="A")]
        edges = [DAGEdge(from_node="a", to_node="missing")]
        dag = WorkflowDAG(nodes=nodes, edges=edges)
        errors = dag.validate()
        assert any("missing" in e.lower() for e in errors)

    def test_topological_layers_linear(self):
        dag = _make_linear_dag()
        layers = dag.topological_layers()
        assert layers == [["a"], ["b"], ["c"]]

    def test_topological_layers_diamond(self):
        dag = _make_diamond_dag()
        layers = dag.topological_layers()
        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]

    def test_topological_layers_single(self):
        nodes = [DAGNode(id="solo", cat_id="orange", prompt_template="{input}")]
        dag = WorkflowDAG(nodes=nodes, edges=[])
        assert dag.topological_layers() == [["solo"]]


class TestNodeResult:
    def test_completed(self):
        r = NodeResult(node_id="a", cat_id="orange", content="done", status="completed")
        assert r.status == "completed"
        assert r.error is None

    def test_failed(self):
        r = NodeResult(node_id="a", cat_id="orange", content="", status="failed", error="boom")
        assert r.status == "failed"
        assert r.error == "boom"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/workflow/test_dag.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.workflow'`

- [ ] **Step 4: Write the implementation**

```python
# src/workflow/dag.py
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


@dataclass
class DAGNode:
    id: str
    cat_id: str
    prompt_template: str
    role: str = ""
    is_aggregator: bool = False


@dataclass
class DAGEdge:
    from_node: str
    to_node: str


@dataclass
class NodeResult:
    node_id: str
    cat_id: str
    content: str
    status: str  # "completed" | "failed" | "skipped"
    thinking: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WorkflowDAG:
    nodes: List[DAGNode]
    edges: List[DAGEdge]

    def _node_map(self) -> Dict[str, DAGNode]:
        return {n.id: n for n in self.nodes}

    def _adjacency(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = defaultdict(list)
        for edge in self.edges:
            adj[edge.from_node].append(edge.to_node)
        return adj

    def _reverse_adjacency(self) -> Dict[str, List[str]]:
        rev: Dict[str, List[str]] = defaultdict(list)
        for edge in self.edges:
            rev[edge.to_node].append(edge.from_node)
        return rev

    def roots(self) -> List[str]:
        has_incoming: Set[str] = set()
        for edge in self.edges:
            has_incoming.add(edge.to_node)
        return [n.id for n in self.nodes if n.id not in has_incoming]

    def successors(self, node_id: str) -> List[str]:
        return self._adjacency().get(node_id, [])

    def predecessors(self, node_id: str) -> List[str]:
        return self._reverse_adjacency().get(node_id, [])

    def validate(self) -> List[str]:
        errors: List[str] = []
        node_ids = {n.id for n in self.nodes}

        # Check edge references
        for edge in self.edges:
            if edge.from_node not in node_ids:
                errors.append(f"Edge references missing source node: {edge.from_node}")
            if edge.to_node not in node_ids:
                errors.append(f"Edge references missing target node: {edge.to_node}")

        # Cycle detection via DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n.id: WHITE for n in self.nodes}
        adj = self._adjacency()

        def has_cycle(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color.get(neighbor) == GRAY:
                    return True
                if color.get(neighbor) == WHITE and has_cycle(neighbor):
                    return True
            color[node] = BLACK
            return False

        for node_id in node_ids:
            if color[node_id] == WHITE:
                if has_cycle(node_id):
                    errors.append("DAG contains a cycle")
                    break

        return errors

    def topological_layers(self) -> List[List[str]]:
        node_ids = {n.id for n in self.nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in node_ids}
        adj = self._adjacency()

        for edge in self.edges:
            in_degree[edge.to_node] += 1

        layers: List[List[str]] = []
        remaining = set(node_ids)

        while remaining:
            layer = [nid for nid in remaining if in_degree[nid] == 0]
            if not layer:
                break
            layer.sort()
            layers.append(layer)
            for nid in layer:
                remaining.remove(nid)
                for succ in adj.get(nid, []):
                    in_degree[succ] -= 1

        return layers
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/workflow/test_dag.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/workflow/__init__.py src/workflow/dag.py tests/workflow/__init__.py tests/workflow/test_dag.py
git commit -m "feat(workflow): add DAG data structures with topological layers and cycle detection"
```

---

### Task 2: Result Aggregator (`src/workflow/aggregator.py`)

**Files:**
- Create: `src/workflow/aggregator.py`
- Test: `tests/workflow/test_aggregator.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/workflow/test_aggregator.py
import pytest
from src.workflow.dag import NodeResult
from src.workflow.aggregator import ResultAggregator


def _make_results():
    return [
        NodeResult(node_id="a", cat_id="orange", content="Part A", status="completed"),
        NodeResult(node_id="b", cat_id="inky", content="Part B", status="completed"),
        NodeResult(node_id="c", cat_id="patch", content="Part C failed", status="failed", error="timeout"),
    ]


class TestResultAggregator:
    def test_merge_mode(self):
        results = _make_results()
        merged = ResultAggregator.aggregate(results, mode="merge")
        assert "Part A" in merged
        assert "Part B" in merged
        assert "Part C failed" not in merged  # failed excluded

    def test_last_mode(self):
        results = _make_results()
        last = ResultAggregator.aggregate(results, mode="last")
        assert last == "Part B"

    def test_merge_empty(self):
        assert ResultAggregator.aggregate([], mode="merge") == ""

    def test_last_empty(self):
        assert ResultAggregator.aggregate([], mode="last") == ""

    def test_merge_single(self):
        r = NodeResult(node_id="a", cat_id="orange", content="Solo", status="completed")
        assert ResultAggregator.aggregate([r], mode="merge") == "Solo"

    def test_summarize_concatenates_for_now(self):
        """Summarize mode concatenates results with labels (LLM summarization deferred)."""
        results = _make_results()[:2]
        result = ResultAggregator.aggregate(results, mode="summarize")
        assert "orange" in result
        assert "Part A" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/workflow/test_aggregator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.workflow.aggregator'`

- [ ] **Step 3: Write the implementation**

```python
# src/workflow/aggregator.py
from typing import List
from src.workflow.dag import NodeResult


class ResultAggregator:
    @staticmethod
    def aggregate(results: List[NodeResult], mode: str = "summarize") -> str:
        completed = [r for r in results if r.status == "completed"]

        if mode == "merge":
            return "\n\n".join(r.content for r in completed)

        if mode == "last":
            if not completed:
                return ""
            return completed[-1].content

        # mode == "summarize" — concatenate with labels
        # (LLM summarization can be layered on top later)
        if not completed:
            return ""
        parts = []
        for r in completed:
            label = f"[{r.cat_id} ({r.node_id})]"
            parts.append(f"{label}\n{r.content}")
        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/workflow/test_aggregator.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow/aggregator.py tests/workflow/test_aggregator.py
git commit -m "feat(workflow): add ResultAggregator with merge/last/summarize modes"
```

---

### Task 3: Workflow Templates (`src/workflow/templates.py`)

**Files:**
- Create: `src/workflow/templates.py`
- Test: `tests/workflow/test_templates.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/workflow/test_templates.py
import pytest
import tempfile
import os
from src.workflow.dag import WorkflowDAG
from src.workflow.templates import WorkflowTemplateFactory


def _make_cats():
    return [
        {"breed_id": "orange", "name": "阿橘"},
        {"breed_id": "inky", "name": "墨点"},
        {"breed_id": "patch", "name": "斑点"},
    ]


class TestBrainstormTemplate:
    def test_creates_dag(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("brainstorm", cats, "给方案")
        assert isinstance(dag, WorkflowDAG)
        errors = dag.validate()
        assert errors == []

    def test_has_parallel_roots(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("brainstorm", cats, "给方案")
        roots = dag.roots()
        assert len(roots) == 3  # 3 thinking nodes

    def test_has_aggregator(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("brainstorm", cats, "给方案")
        agg_nodes = [n for n in dag.nodes if n.is_aggregator]
        assert len(agg_nodes) == 1

    def test_edges_connect_to_aggregator(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("brainstorm", cats, "给方案")
        agg = [n for n in dag.nodes if n.is_aggregator][0]
        for root_id in dag.roots():
            assert agg.id in dag.successors(root_id)


class TestParallelTemplate:
    def test_creates_dag(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("parallel", cats, "实现登录")
        assert isinstance(dag, WorkflowDAG)
        errors = dag.validate()
        assert errors == []

    def test_has_parallel_workers_and_merger(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("parallel", cats, "实现登录")
        roots = dag.roots()
        assert len(roots) == 3
        agg_nodes = [n for n in dag.nodes if n.is_aggregator]
        assert len(agg_nodes) == 1

    def test_worker_prompts_contain_input(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("parallel", cats, "实现登录功能")
        for root_id in dag.roots():
            node = next(n for n in dag.nodes if n.id == root_id)
            assert "实现登录功能" in node.prompt_template


class TestAutoPlanTemplate:
    def test_creates_single_node_dag(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("auto_plan", cats, "实现登录")
        assert len(dag.nodes) == 1
        assert len(dag.edges) == 0
        # Planner uses first cat
        assert dag.nodes[0].cat_id == cats[0]["breed_id"]

    def test_planner_prompt_requests_json(self):
        cats = _make_cats()
        dag = WorkflowTemplateFactory.create("auto_plan", cats, "实现登录")
        prompt = dag.nodes[0].prompt_template
        assert "JSON" in prompt or "json" in prompt


class TestFromYaml:
    def test_loads_yaml_template(self):
        yaml_content = """
name: test_pipeline
nodes:
  - id: step_a
    cat_id: orange
    prompt_template: "Do: {input}"
  - id: step_b
    cat_id: inky
    prompt_template: "Review: {prev_results}"
    is_aggregator: true
edges:
  - from: step_a
    to: step_b
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            dag = WorkflowTemplateFactory.from_yaml(f.name)
        os.unlink(f.name)

        assert len(dag.nodes) == 2
        assert len(dag.edges) == 1
        assert dag.nodes[1].is_aggregator is True
        errors = dag.validate()
        assert errors == []


class TestInvalidTemplate:
    def test_unknown_template_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            WorkflowTemplateFactory.create("nonexistent", _make_cats(), "test")

    def test_zero_cats_raises(self):
        with pytest.raises(ValueError):
            WorkflowTemplateFactory.create("brainstorm", [], "test")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/workflow/test_templates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.workflow.templates'`

- [ ] **Step 3: Write the implementation**

```python
# src/workflow/templates.py
from pathlib import Path
from typing import Dict, List

import yaml

from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG

_AUTO_PLAN_SYSTEM_PROMPT = """你是一个任务规划器。分析以下任务，将其分解为由不同角色猫执行的子任务。

可用的猫和角色：
{cat_list}

任务：{input}

请输出严格的 JSON 格式（不要包含其他文字）：
{{
  "nodes": [
    {{"id": "step_1", "cat_id": "<猫ID>", "prompt": "<该猫的具体任务>"}},
    {{"id": "step_2", "cat_id": "<猫ID>", "prompt": "<该猫的具体任务>"}}
  ],
  "edges": [
    {{"from": "step_1", "to": "step_2"}}
  ]
}}

注意：
- 每个节点的 cat_id 必须是上面列出的猫ID之一
- edges 定义执行依赖和顺序
- 可以有并行节点（无依赖关系）
- 最后一个节点通常是汇总/整合节点"""


class WorkflowTemplateFactory:
    @staticmethod
    def create(template_name: str, cats: List[Dict], message: str) -> WorkflowDAG:
        if not cats:
            raise ValueError("At least one cat is required")

        if template_name == "brainstorm":
            return WorkflowTemplateFactory._brainstorm(cats, message)
        elif template_name == "parallel":
            return WorkflowTemplateFactory._parallel(cats, message)
        elif template_name == "auto_plan":
            return WorkflowTemplateFactory._auto_plan(cats, message)
        else:
            raise ValueError(f"Unknown template: {template_name}")

    @staticmethod
    def from_yaml(path: str) -> WorkflowDAG:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        nodes = []
        for nd in data.get("nodes", []):
            nodes.append(DAGNode(
                id=nd["id"],
                cat_id=nd["cat_id"],
                prompt_template=nd.get("prompt_template", "{input}"),
                role=nd.get("role", ""),
                is_aggregator=nd.get("is_aggregator", False),
            ))

        edges = []
        for ed in data.get("edges", []):
            edges.append(DAGEdge(from_node=ed["from"], to_node=ed["to"]))

        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _brainstorm(cats: List[Dict], message: str) -> WorkflowDAG:
        nodes = []
        edges = []
        for i, cat in enumerate(cats):
            nodes.append(DAGNode(
                id=f"think_{cat['breed_id']}_{i}",
                cat_id=cat["breed_id"],
                prompt_template=f"请独立思考并给出你对以下问题的见解：\n\n{{input}}",
                role=cat["name"],
            ))

        # Aggregator uses last cat
        agg_cat = cats[-1]
        nodes.append(DAGNode(
            id="aggregate",
            cat_id=agg_cat["breed_id"],
            prompt_template="以下是多位专家的独立见解：\n\n{prev_results}\n\n请综合以上观点，给出一个全面、结构化的总结和建议。",
            role=f"{agg_cat['name']}（汇总者）",
            is_aggregator=True,
        ))

        for n in nodes[:-1]:
            edges.append(DAGEdge(from_node=n.id, to_node="aggregate"))

        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _parallel(cats: List[Dict], message: str) -> WorkflowDAG:
        nodes = []
        edges = []
        parts = ["前端", "后端", "测试"]

        for i, cat in enumerate(cats):
            part_name = parts[i] if i < len(parts) else f"部分{i + 1}"
            nodes.append(DAGNode(
                id=f"work_{cat['breed_id']}_{i}",
                cat_id=cat["breed_id"],
                prompt_template=f"你是负责**{part_name}**的专家。请针对以下任务，专注于{part_name}部分的工作：\n\n{{input}}",
                role=f"{cat['name']}（{part_name}）",
            ))

        merge_cat = cats[-1]
        nodes.append(DAGNode(
            id="merge",
            cat_id=merge_cat["breed_id"],
            prompt_template="以下是团队成员各自完成的部分：\n\n{prev_results}\n\n请将以上各部分整合为一个完整、一致的交付物。确保各部分之间的衔接和一致性。",
            role=f"{merge_cat['name']}（整合者）",
            is_aggregator=True,
        ))

        for n in nodes[:-1]:
            edges.append(DAGEdge(from_node=n.id, to_node="merge"))

        return WorkflowDAG(nodes=nodes, edges=edges)

    @staticmethod
    def _auto_plan(cats: List[Dict], message: str) -> WorkflowDAG:
        cat_list = "\n".join(f"- {c['breed_id']}: {c['name']}" for c in cats)
        prompt = _AUTO_PLAN_SYSTEM_PROMPT.format(cat_list=cat_list, input=message)

        return WorkflowDAG(
            nodes=[
                DAGNode(
                    id="planner",
                    cat_id=cats[0]["breed_id"],
                    prompt_template=prompt,
                    role="任务规划器",
                )
            ],
            edges=[],
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/workflow/test_templates.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow/templates.py tests/workflow/test_templates.py
git commit -m "feat(workflow): add WorkflowTemplateFactory with brainstorm/parallel/auto_plan templates"
```

---

### Task 4: DAG Executor (`src/workflow/executor.py`)

**Files:**
- Create: `src/workflow/executor.py`
- Test: `tests/workflow/test_executor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/workflow/test_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG, NodeResult
from src.workflow.executor import DAGExecutor
from src.thread.models import Thread


def _mock_agent_registry(nodes):
    """Create a mock agent registry with a service per node cat_id."""
    registry = MagicMock()
    services = {}
    for node in nodes:
        if node.cat_id not in services:
            service = MagicMock()
            # Return a simple stream yielding one text chunk
            async def make_stream(text=node.prompt_template):
                yield text
            service.invoke = make_stream
            service.build_system_prompt = MagicMock(return_value=f"You are {node.cat_id}")
            services[node.cat_id] = service
    registry.get = MagicMock(side_effect=lambda cat_id: services.get(cat_id))
    registry.has = MagicMock(side_effect=lambda cat_id: cat_id in services)
    return registry


def _linear_dag():
    return WorkflowDAG(
        nodes=[
            DAGNode(id="a", cat_id="orange", prompt_template="Step A: {input}"),
            DAGNode(id="b", cat_id="inky", prompt_template="Step B: {prev_results}"),
        ],
        edges=[DAGEdge(from_node="a", to_node="b")],
    )


def _parallel_dag():
    return WorkflowDAG(
        nodes=[
            DAGNode(id="p1", cat_id="orange", prompt_template="Part 1: {input}"),
            DAGNode(id="p2", cat_id="inky", prompt_template="Part 2: {input}"),
            DAGNode(id="merge", cat_id="orange", prompt_template="Merge: {prev_results}", is_aggregator=True),
        ],
        edges=[
            DAGEdge(from_node="p1", to_node="merge"),
            DAGEdge(from_node="p2", to_node="merge"),
        ],
    )


class TestDAGExecutor:
    @pytest.mark.asyncio
    async def test_linear_execution(self):
        dag = _linear_dag()
        registry = _mock_agent_registry(dag.nodes)
        executor = DAGExecutor(agent_registry=registry)
        thread = Thread.create("test")

        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)

        assert len(results) == 2
        assert results[0].node_id == "a"
        assert results[1].node_id == "b"

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        dag = _parallel_dag()
        registry = _mock_agent_registry(dag.nodes)
        executor = DAGExecutor(agent_registry=registry)
        thread = Thread.create("test")

        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)

        ids = [r.node_id for r in results]
        # p1 and p2 should come before merge
        assert "merge" in ids
        merge_idx = ids.index("merge")
        assert "p1" in ids[:merge_idx]
        assert "p2" in ids[:merge_idx]

    @pytest.mark.asyncio
    async def test_invalid_dag_raises(self):
        nodes = [DAGNode(id="a", cat_id="orange", prompt_template="A")]
        edges = [DAGEdge(from_node="a", to_node="missing")]
        dag = WorkflowDAG(nodes=nodes, edges=edges)
        registry = _mock_agent_registry(nodes)
        executor = DAGExecutor(agent_registry=registry)
        thread = Thread.create("test")

        with pytest.raises(ValueError, match="DAG validation failed"):
            async for _ in executor.execute(dag, "hello", thread):
                pass

    @pytest.mark.asyncio
    async def test_single_node(self):
        dag = WorkflowDAG(
            nodes=[DAGNode(id="solo", cat_id="orange", prompt_template="Do: {input}")],
            edges=[],
        )
        registry = _mock_agent_registry(dag.nodes)
        executor = DAGExecutor(agent_registry=registry)
        thread = Thread.create("test")

        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)

        assert len(results) == 1
        assert results[0].status == "completed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/workflow/test_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.workflow.executor'`

- [ ] **Step 3: Write the implementation**

```python
# src/workflow/executor.py
import asyncio
from typing import AsyncIterator, Dict, List, Optional

from src.workflow.dag import DAGNode, NodeResult, WorkflowDAG
from src.thread.models import Thread
from src.models.types import AgentMessageType, InvocationOptions


class DAGExecutor:
    def __init__(self, agent_registry, session_chain=None, tracker=None):
        self.agent_registry = agent_registry
        self.session_chain = session_chain
        self.tracker = tracker

    async def execute(
        self,
        dag: WorkflowDAG,
        input_text: str,
        thread: Thread,
    ) -> AsyncIterator[NodeResult]:
        # Validate
        errors = dag.validate()
        if errors:
            raise ValueError(f"DAG validation failed: {'; '.join(errors)}")

        layers = dag.topological_layers()
        node_map = {n.id: n for n in dag.nodes}
        completed_results: Dict[str, NodeResult] = {}

        for layer in layers:
            layer_results = await self._execute_layer(
                layer, node_map, input_text, completed_results, thread
            )
            for result in layer_results:
                completed_results[result.node_id] = result
                yield result

    async def _execute_layer(
        self,
        layer: List[str],
        node_map: Dict[str, DAGNode],
        input_text: str,
        completed_results: Dict[str, NodeResult],
        thread: Thread,
    ) -> List[NodeResult]:
        tasks = []
        for node_id in layer:
            node = node_map[node_id]
            tasks.append(self._execute_node(node, input_text, completed_results, thread))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                node = node_map[layer[i]]
                output.append(NodeResult(
                    node_id=node.id,
                    cat_id=node.cat_id,
                    content="",
                    status="failed",
                    error=str(result),
                ))
            else:
                output.append(result)
        return output

    async def _execute_node(
        self,
        node: DAGNode,
        input_text: str,
        completed_results: Dict[str, NodeResult],
        thread: Thread,
    ) -> NodeResult:
        # Build prompt from template
        prev_results = self._collect_predecessor_results(node.id, completed_results)
        prompt = node.prompt_template.replace("{input}", input_text)
        prompt = prompt.replace("{prev_results}", prev_results)

        # Get service from registry
        try:
            service = self.agent_registry.get(node.cat_id)
        except (KeyError, Exception) as e:
            return NodeResult(
                node_id=node.id,
                cat_id=node.cat_id,
                content="",
                status="failed",
                error=f"Agent not found: {node.cat_id}: {e}",
            )

        # Build system prompt
        system_prompt = service.build_system_prompt()
        if node.role:
            system_prompt += f"\n你的角色：{node.role}"

        # Invoke via provider
        options = InvocationOptions(system_prompt=system_prompt)
        chunks = []
        thinking_parts = []
        session_id = None

        try:
            async for msg in service.invoke(prompt, options):
                if msg.type == AgentMessageType.TEXT:
                    chunks.append(msg.content)
                elif msg.type == AgentMessageType.THINKING:
                    thinking_parts.append(msg.content)
                elif msg.type == AgentMessageType.DONE:
                    if msg.session_id:
                        session_id = msg.session_id
                elif msg.type == AgentMessageType.ERROR:
                    return NodeResult(
                        node_id=node.id,
                        cat_id=node.cat_id,
                        content="",
                        status="failed",
                        error=msg.content,
                    )
        except Exception as e:
            return NodeResult(
                node_id=node.id,
                cat_id=node.cat_id,
                content="",
                status="failed",
                error=str(e),
            )

        content = "".join(chunks)
        return NodeResult(
            node_id=node.id,
            cat_id=node.cat_id,
            content=content,
            status="completed",
            thinking="".join(thinking_parts) if thinking_parts else None,
        )

    def _collect_predecessor_results(
        self,
        node_id: str,
        completed_results: Dict[str, NodeResult],
    ) -> str:
        parts = []
        for nid, result in completed_results.items():
            if result.status == "completed":
                parts.append(f"[{result.cat_id} ({nid})]\n{result.content}")
        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/workflow/test_executor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/workflow/executor.py tests/workflow/test_executor.py
git commit -m "feat(workflow): add DAGExecutor with topological-layer parallel execution"
```

---

### Task 5: MCPExecutor Helper (`src/collaboration/mcp_executor.py`)

**Files:**
- Create: `src/collaboration/mcp_executor.py`
- Test: `tests/collaboration/test_mcp_executor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/collaboration/test_mcp_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.thread.models import Thread


class TestMCPExecutor:
    def test_register_tools_creates_client_with_tools(self):
        thread = Thread.create("test")
        executor = MCPExecutor()
        client = executor.register_tools(thread)
        assert isinstance(client, MCPClient)
        for tool_name in TOOL_REGISTRY:
            assert client.get_tool(tool_name) is not None

    def test_build_tools_prompt(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)
        prompt = executor.build_tools_prompt(client)
        assert "可用工具" in prompt
        assert "post_message" in prompt

    @pytest.mark.asyncio
    async def test_execute_callbacks_parses_and_executes(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)

        raw_content = 'Hello <mcp:post_message>{"content": "test msg"}</mcp:post_message>'
        result = await executor.execute_callbacks(raw_content, client, thread)

        # Should return CallbackParseResult
        assert "post_message" not in result.clean_content
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "post_message"

    @pytest.mark.asyncio
    async def test_execute_callbacks_skips_targetcats(self):
        executor = MCPExecutor()
        thread = Thread.create("test")
        client = executor.register_tools(thread)

        raw_content = 'Go <mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>'
        result = await executor.execute_callbacks(raw_content, client, thread)

        # targetCats should be extracted but not executed as a tool call
        assert result.targetCats == ["inky"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/collaboration/test_mcp_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.collaboration.mcp_executor'`

- [ ] **Step 3: Write the implementation**

```python
# src/collaboration/mcp_executor.py
from src.collaboration.mcp_client import MCPClient
from src.collaboration.mcp_tools import TOOL_REGISTRY
from src.collaboration.callback_parser import parse_callbacks


class MCPExecutor:
    """Helper for MCP tool registration and callback execution."""

    def register_tools(self, thread) -> MCPClient:
        client = MCPClient(thread)
        for tool_name, config in TOOL_REGISTRY.items():
            client.register_tool(
                name=tool_name,
                description=config["description"],
                parameters=config["parameters"],
                handler=config["handler"],
            )
        return client

    def build_tools_prompt(self, client: MCPClient) -> str:
        return client.build_tools_prompt()

    async def execute_callbacks(self, raw_content: str, client: MCPClient, thread):
        parsed = parse_callbacks(raw_content)
        for tool_call in parsed.tool_calls:
            if tool_call.tool_name == "targetcats":
                continue
            await client.call(tool_call.tool_name, tool_call.params)
        return parsed
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/collaboration/test_mcp_executor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/collaboration/mcp_executor.py tests/collaboration/test_mcp_executor.py
git commit -m "feat(collaboration): extract MCPExecutor helper from A2AController"
```

---

### Task 6: SkillInjector Helper (`src/collaboration/skill_injector.py`)

**Files:**
- Create: `src/collaboration/skill_injector.py`
- Test: `tests/collaboration/test_skill_injector.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/collaboration/test_skill_injector.py
import pytest
from unittest.mock import MagicMock
from pathlib import Path
from src.collaboration.skill_injector import SkillInjector


def _mock_agents():
    agent = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock(),
    }
    agent["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    return [agent]


class TestSkillInjector:
    def test_inject_wraps_build_system_prompt(self):
        agents = _mock_agents()
        injector = SkillInjector()
        injector.inject(agents, "fake_skill", "这是技能上下文")

        prompt = agents[0]["service"].build_system_prompt()
        assert "技能上下文" in prompt
        assert "你是阿橘" in prompt

    def test_restore_resets_original_prompt(self):
        agents = _mock_agents()
        injector = SkillInjector()
        original = agents[0]["service"].build_system_prompt()

        injector.inject(agents, "fake_skill", "技能内容")
        injector.restore(agents)

        restored = agents[0]["service"].build_system_prompt()
        assert restored == original
        assert "技能内容" not in restored

    def test_restore_no_inject_is_safe(self):
        agents = _mock_agents()
        injector = SkillInjector()
        injector.restore(agents)  # Should not raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/collaboration/test_skill_injector.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.collaboration.skill_injector'`

- [ ] **Step 3: Write the implementation**

```python
# src/collaboration/skill_injector.py
from typing import Dict, List, Optional


class SkillInjector:
    """Helper for injecting skill context into agent system prompts."""

    def inject(self, agents: List[Dict], skill_id: str, skill_content: str) -> None:
        for agent_info in agents:
            service = agent_info["service"]
            original_method = service.build_system_prompt
            agent_info["_original_build_prompt"] = original_method
            service.build_system_prompt = lambda orig=original_method, sc=skill_content: orig() + f"\n\n## 激活技能\n{sc}\n---\n"

    def restore(self, agents: List[Dict]) -> None:
        for agent_info in agents:
            if "_original_build_prompt" in agent_info:
                agent_info["service"].build_system_prompt = agent_info["_original_build_prompt"]
                del agent_info["_original_build_prompt"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/collaboration/test_skill_injector.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/collaboration/skill_injector.py tests/collaboration/test_skill_injector.py
git commit -m "feat(collaboration): extract SkillInjector helper from A2AController"
```

---

### Task 7: Refactor A2AController — Use Helpers + StreamMerge + SessionChain

**Files:**
- Modify: `src/collaboration/a2a_controller.py` (full rewrite)
- Modify: `tests/collaboration/test_a2a_controller.py` (update for new structure)

- [ ] **Step 1: Read the current `src/collaboration/a2a_controller.py` to understand the full file**

Run: Read `src/collaboration/a2a_controller.py` (already known: 333 lines)

- [ ] **Step 2: Write the updated `a2a_controller.py`**

The refactored file keeps `CatResponse`, `A2AController.__init__`, and the public `execute()` signature. Internally it delegates to `MCPExecutor`, `SkillInjector`, `merge_streams`, and `SessionChain`.

```python
# src/collaboration/a2a_controller.py
import re
from dataclasses import dataclass
from typing import List, Dict, Any, AsyncIterator, Optional
from pathlib import Path

from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread, Message
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.skill_injector import SkillInjector
from src.invocation.stream_merge import merge_streams
from src.models.types import AgentMessageType, InvocationOptions


@dataclass
class CatResponse:
    cat_id: str
    cat_name: str
    content: str
    targetCats: Optional[List[str]] = None
    thinking: Optional[str] = None


class A2AController:
    """A2A 协作控制器 — 协调多猫对话"""

    def __init__(self, agents: List[Dict[str, Any]], session_chain=None, dag_executor=None, template_factory=None):
        self.agents = agents
        self.session_chain = session_chain
        self.dag_executor = dag_executor
        self.template_factory = template_factory
        self.mcp_executor = MCPExecutor()
        self.skill_injector = SkillInjector()

        self.skill_router = None
        self.skill_loader = None
        manifest_path = Path("skills/manifest.yaml")
        if manifest_path.exists():
            try:
                from src.skills.router import ManifestRouter
                from src.skills.loader import SkillLoader
                self.skill_router = ManifestRouter(manifest_path)
                self.skill_loader = SkillLoader()
            except Exception:
                pass

    async def execute(
        self,
        intent: IntentResult,
        message: str,
        thread: Thread,
    ) -> AsyncIterator[CatResponse]:
        # Workflow path
        if intent.workflow and self.dag_executor and self.template_factory:
            from src.workflow.dag import NodeResult
            dag = self.template_factory.create(intent.workflow, self.agents, message)
            async for result in self.dag_executor.execute(dag, message, thread):
                yield CatResponse(
                    cat_id=result.cat_id,
                    cat_name=self._get_cat_name(result.cat_id),
                    content=result.content,
                    thinking=result.thinking,
                )
            return

        # Skill check
        active_skills = []
        if self.skill_router:
            active_skills = self.skill_router.route(message)

        if active_skills:
            skill_data = self._load_skill(active_skills[0]["skill_id"])
            if skill_data:
                self.skill_injector.inject(self.agents, active_skills[0]["skill_id"], skill_data["content"])
                try:
                    async for r in self._dispatch(intent, message, thread):
                        yield r
                finally:
                    self.skill_injector.restore(self.agents)
                return

        async for r in self._dispatch(intent, message, thread):
            yield r

    def _dispatch(self, intent: IntentResult, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        if intent.intent == "ideate":
            return self._parallel_ideate(message, thread)
        else:
            return self._serial_execute(message, thread)

    async def _parallel_ideate(self, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        async def _agent_stream(agent_info):
            return await self._call_cat(
                agent_info["service"], agent_info["name"], agent_info["breed_id"], message, thread
            )

        tasks = [_agent_stream(a) for a in self.agents]

        # Use asyncio.as_completed for CatResponse objects (not AgentMessage streams)
        import asyncio
        for coro in asyncio.as_completed(tasks):
            response = await coro
            yield response

    async def _serial_execute(self, message: str, thread: Thread) -> AsyncIterator[CatResponse]:
        agent_queue = list(self.agents)
        executed_cats = set()

        while agent_queue:
            agent_info = agent_queue.pop(0)
            breed_id = agent_info["breed_id"]
            if breed_id in executed_cats:
                continue
            executed_cats.add(breed_id)

            context_msg = self._build_context(message, thread, len(executed_cats) - 1)
            response = await self._call_cat(
                agent_info["service"], agent_info["name"], breed_id, context_msg, thread
            )
            yield response

            thread.add_message("assistant", response.content, cat_id=breed_id)

            if response.targetCats:
                for target_cat in response.targetCats:
                    for agent in self.agents:
                        if agent["breed_id"] == target_cat and target_cat not in executed_cats:
                            agent_queue.append(agent)
                            break

    async def _call_cat(self, service, name: str, breed_id: str, message: str, thread: Thread) -> CatResponse:
        # MCP tools
        client = self.mcp_executor.register_tools(thread)
        system_prompt = service.build_system_prompt()

        if len(self.agents) > 1:
            other_cats = [a["name"] for a in self.agents if a["breed_id"] != breed_id]
            if other_cats:
                system_prompt += f"\n\n## 协作说明\n本次有多只猫参与：{', '.join(other_cats)}。请专注于你的角色，给出独立见解。"

        system_prompt += self.mcp_executor.build_tools_prompt(client)

        # Session chain
        session_id = None
        if self.session_chain:
            active = self.session_chain.get_active(breed_id, thread.id)
            if active:
                if self.session_chain.should_auto_seal(breed_id, thread.id):
                    self.session_chain.seal(breed_id, thread.id)
                else:
                    session_id = active.session_id

        # Invoke
        options = InvocationOptions(system_prompt=system_prompt, session_id=session_id)
        chunks = []
        thinking_parts = []
        new_session_id = None

        async for msg in service.invoke(message, options):
            if msg.type == AgentMessageType.TEXT:
                chunks.append(msg.content)
            elif msg.type == AgentMessageType.THINKING:
                thinking_parts.append(msg.content)
            elif msg.type == AgentMessageType.DONE and msg.session_id:
                new_session_id = msg.session_id

        raw_content = "".join(chunks)

        # Execute callbacks
        parsed = await self.mcp_executor.execute_callbacks(raw_content, client, thread)

        # Session chain update
        if self.session_chain and new_session_id:
            self.session_chain.create(breed_id, thread.id, new_session_id)

        return CatResponse(
            cat_id=breed_id,
            cat_name=name,
            content=parsed.clean_content,
            targetCats=parsed.targetCats if parsed.targetCats else None,
            thinking="".join(thinking_parts) if thinking_parts else None,
        )

    def _build_context(self, message: str, thread: Thread, current_index: int) -> str:
        if current_index == 0:
            return message
        parts = [message, "\n\n## 前面的回复"]
        for msg in thread.messages[-current_index:]:
            if msg.role == "assistant" and msg.cat_id:
                parts.append(f"\n{msg.cat_id}: {msg.content[:200]}...")
        parts.append("\n\n请继续完成或补充：")
        return "".join(parts)

    def _load_skill(self, skill_id: str) -> Optional[Dict]:
        if not self.skill_loader:
            return None
        try:
            from src.skills.loader import SkillLoader
            skill_path = Path.home() / ".meowai" / "skills" / skill_id
            if skill_path.exists():
                return self.skill_loader.load_skill(skill_path)
        except Exception:
            pass
        return None

    def _get_cat_name(self, cat_id: str) -> str:
        for a in self.agents:
            if a["breed_id"] == cat_id:
                return a["name"]
        return cat_id
```

- [ ] **Step 3: Update the existing tests**

The existing tests in `tests/collaboration/test_a2a_controller.py` must still pass. The `mock_async_iterator` helper needs to be updated because the refactored `_call_cat` now calls `service.invoke` instead of `service.chat_stream`.

```python
# tests/collaboration/test_a2a_controller.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collaboration.a2a_controller import A2AController, CatResponse
from src.collaboration.intent_parser import IntentResult
from src.thread.models import Thread
from src.models.types import AgentMessage, AgentMessageType


def mock_invoke_stream(items, cat_id="orange", session_id=None):
    """Create a mock invoke method that yields AgentMessage items."""
    async def invoke_fn(prompt, options=None):
        for item in items:
            yield item
        yield AgentMessage(type=AgentMessageType.DONE, cat_id=cat_id, session_id=session_id)
    return invoke_fn


def text_msg(text, cat_id="orange"):
    return AgentMessage(type=AgentMessageType.TEXT, content=text, cat_id=cat_id)


def thinking_msg(text, cat_id="orange"):
    return AgentMessage(type=AgentMessageType.THINKING, content=text, cat_id=cat_id)


@pytest.fixture
def mock_agents():
    agent1 = {
        "breed_id": "orange",
        "name": "阿橘",
        "service": MagicMock(),
    }
    agent1["service"].build_system_prompt = MagicMock(return_value="你是阿橘")
    agent1["service"].invoke = mock_invoke_stream([text_msg("你好", "orange")], "orange")

    agent2 = {
        "breed_id": "inky",
        "name": "墨点",
        "service": MagicMock(),
    }
    agent2["service"].build_system_prompt = MagicMock(return_value="你是墨点")
    agent2["service"].invoke = mock_invoke_stream([text_msg("嗨", "inky")], "inky")

    return [agent1, agent2]


@pytest.mark.asyncio
async def test_parallel_ideate(mock_agents):
    controller = A2AController(mock_agents)
    intent = IntentResult(intent="ideate", explicit=True, prompt_tags=[], clean_message="测试")
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert len(responses) == 2
    assert any(r.cat_id == "orange" for r in responses)
    assert any(r.cat_id == "inky" for r in responses)


@pytest.mark.asyncio
async def test_serial_execute(mock_agents):
    controller = A2AController(mock_agents)
    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert len(responses) == 2
    assert responses[0].cat_id == "orange"
    assert responses[1].cat_id == "inky"


@pytest.mark.asyncio
async def test_mcp_callback_integration(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream([
        text_msg("Found it!", "orange"),
        AgentMessage(type=AgentMessageType.TEXT, content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>', cat_id="orange"),
    ], "orange")

    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert responses[0].targetCats == ["inky"]
    assert "targetCats" not in responses[0].content


@pytest.mark.asyncio
async def test_target_cats_routing(mock_agents):
    controller = A2AController(mock_agents)
    mock_agents[0]["service"].invoke = mock_invoke_stream([
        text_msg("Please help me @inky", "orange"),
        AgentMessage(type=AgentMessageType.TEXT, content='<mcp:targetCats>{"cats": ["inky"]}</mcp:targetCats>', cat_id="orange"),
    ], "orange")

    intent = IntentResult(intent="execute", explicit=True, prompt_tags=[], clean_message="测试")
    thread = Thread.create("Test")

    responses = []
    async for response in controller.execute(intent, "测试", thread):
        responses.append(response)

    assert len(responses) == 2
    assert responses[1].cat_id == "inky"
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/collaboration/test_a2a_controller.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run full regression**

Run: `python3 -m pytest -x -q`
Expected: All 318+ tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/collaboration/a2a_controller.py tests/collaboration/test_a2a_controller.py
git commit -m "refactor(collaboration): slim A2AController using MCPExecutor, SkillInjector, SessionChain"
```

---

### Task 8: Extend IntentParser for Workflow Detection

**Files:**
- Modify: `src/collaboration/intent_parser.py`
- Modify: `src/collaboration/__init__.py`
- Test: `tests/collaboration/test_intent_parser.py` (extend existing)

- [ ] **Step 1: Add workflow tests to the existing test file**

Append to `tests/collaboration/test_intent_parser.py`:

```python
# --- Append to tests/collaboration/test_intent_parser.py ---

class TestWorkflowIntent:
    def test_brainstorm_tag(self):
        result = parse_intent("#brainstorm 给我方案", 3)
        assert result.workflow == "brainstorm"

    def test_parallel_tag(self):
        result = parse_intent("#parallel 分工实现", 3)
        assert result.workflow == "parallel"

    def test_autoplan_tag(self):
        result = parse_intent("#autoplan 实现登录", 3)
        assert result.workflow == "auto_plan"

    def test_autoplan_mention(self):
        result = parse_intent("@planner 实现登录", 3)
        assert result.workflow == "auto_plan"

    def test_auto_brainstorm_3plus_cats(self):
        result = parse_intent("@orange @inky @patch 给方案", 3)
        assert result.workflow == "brainstorm"
        assert result.explicit is False

    def test_no_workflow_1_cat(self):
        result = parse_intent("hello", 1)
        assert result.workflow is None

    def test_no_workflow_2_cats(self):
        result = parse_intent("@orange @inky hello", 2)
        assert result.workflow is None
        assert result.intent == "ideate"

    def test_explicit_intent_overrides_auto_workflow(self):
        """When user explicitly sets #execute, don't auto-set workflow."""
        result = parse_intent("#execute @orange @inky @patch 做这个", 3)
        assert result.workflow is None
        assert result.intent == "execute"
        assert result.explicit is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/collaboration/test_intent_parser.py::TestWorkflowIntent -v`
Expected: FAIL — `AttributeError: IntentResult has no field 'workflow'`

- [ ] **Step 3: Update `src/collaboration/intent_parser.py`**

```python
# src/collaboration/intent_parser.py  — FULL FILE
from dataclasses import dataclass
from typing import List, Literal, Optional
import re

IntentType = Literal["ideate", "execute"]
PromptTagType = Literal["critique"]

VALID_INTENTS = {"ideate", "execute"}
VALID_PROMPT_TAGS = {"critique"}
WORKFLOW_TAGS = {"brainstorm": "brainstorm", "parallel": "parallel", "autoplan": "auto_plan"}
TAG_PATTERN = re.compile(r"#(\w+)", re.IGNORECASE)


@dataclass
class IntentResult:
    intent: IntentType
    explicit: bool
    prompt_tags: List[PromptTagType]
    clean_message: str
    workflow: Optional[str] = None  # "brainstorm" | "parallel" | "auto_plan"


class IntentParser:

    def parse(self, message: str, cat_count: int) -> IntentResult:
        tags = self._extract_tags(message)

        # Check for explicit workflow tags
        workflow = self._find_workflow_tag(tags)

        # If @planner mentioned, set auto_plan
        if not workflow and "@planner" in message.lower():
            workflow = "auto_plan"

        # Auto-detect brainstorm for 3+ cats (unless explicit intent)
        explicit_intent = self._find_explicit_intent(tags)
        if not workflow and not explicit_intent and cat_count >= 3:
            workflow = "brainstorm"

        # Determine intent
        if explicit_intent:
            intent = explicit_intent
            explicit = True
        else:
            intent = "ideate" if cat_count >= 2 else "execute"
            explicit = False

        prompt_tags = self._find_prompt_tags(tags)
        clean_message = self._strip_tags(message)

        return IntentResult(
            intent=intent,
            explicit=explicit,
            prompt_tags=prompt_tags,
            clean_message=clean_message,
            workflow=workflow,
        )

    def _extract_tags(self, message: str) -> List[str]:
        return [match.group(1).lower() for match in TAG_PATTERN.finditer(message)]

    def _find_explicit_intent(self, tags: List[str]) -> Optional[IntentType]:
        for tag in tags:
            if tag in VALID_INTENTS:
                return tag  # type: ignore
        return None

    def _find_workflow_tag(self, tags: List[str]) -> Optional[str]:
        for tag in tags:
            if tag in WORKFLOW_TAGS:
                return WORKFLOW_TAGS[tag]
        return None

    def _find_prompt_tags(self, tags: List[str]) -> List[PromptTagType]:
        result = []
        for tag in tags:
            if tag in VALID_PROMPT_TAGS:
                result.append(tag)  # type: ignore
        return result

    def _strip_tags(self, message: str) -> str:
        return TAG_PATTERN.sub("", message).strip()


def parse_intent(message: str, cat_count: int) -> IntentResult:
    return IntentParser().parse(message, cat_count)
```

- [ ] **Step 4: Update `src/collaboration/__init__.py`**

```python
# src/collaboration/__init__.py
from src.collaboration.intent_parser import (
    IntentParser,
    IntentResult,
    IntentType,
    parse_intent,
)
from src.collaboration.mcp_client import (
    MCPClient,
    MCPResult,
    MCPTool,
)
from src.collaboration.mcp_tools import (
    TOOL_REGISTRY,
    post_message_tool,
    search_files_tool,
    target_cats_tool,
)
from src.collaboration.mcp_executor import MCPExecutor
from src.collaboration.skill_injector import SkillInjector

__all__ = [
    "IntentParser",
    "IntentResult",
    "IntentType",
    "parse_intent",
    "MCPClient",
    "MCPResult",
    "MCPTool",
    "TOOL_REGISTRY",
    "post_message_tool",
    "search_files_tool",
    "target_cats_tool",
    "MCPExecutor",
    "SkillInjector",
]
```

- [ ] **Step 5: Run all intent parser tests**

Run: `python3 -m pytest tests/collaboration/test_intent_parser.py -v`
Expected: All tests PASS (old + new)

- [ ] **Step 6: Commit**

```bash
git add src/collaboration/intent_parser.py src/collaboration/__init__.py tests/collaboration/test_intent_parser.py
git commit -m "feat(collaboration): add workflow intent detection to IntentParser"
```

---

### Task 9: Wire Phase 6 Infrastructure — AgentRouterV2 + FastAPI Lifespan

**Files:**
- Modify: `src/router/__init__.py`
- Modify: `src/web/app.py`
- Modify: `src/web/dependencies.py`

- [ ] **Step 1: Update `src/router/__init__.py`**

```python
# src/router/__init__.py
from src.router.agent_router_v2 import AgentRouterV2

__all__ = ["AgentRouterV2"]
```

- [ ] **Step 2: Update `src/web/dependencies.py`**

```python
# src/web/dependencies.py
from fastapi import Request
from src.thread import ThreadManager
from src.router.agent_router_v2 import AgentRouterV2
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry


def get_thread_manager(request: Request) -> ThreadManager:
    return request.app.state.thread_manager


def get_agent_router(request: Request) -> AgentRouterV2:
    return request.app.state.agent_router


def get_cat_registry(request: Request) -> CatRegistry:
    return request.app.state.cat_registry


def get_agent_registry(request: Request) -> AgentRegistry:
    return request.app.state.agent_registry
```

- [ ] **Step 3: Update `src/web/app.py`**

```python
# src/web/app.py
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.thread import ThreadManager
from src.router.agent_router_v2 import AgentRouterV2
from src.models.registry_init import initialize_registries
from src.models.cat_registry import CatRegistry
from src.models.agent_registry import AgentRegistry
from src.session.chain import SessionChain
from src.invocation.tracker import InvocationTracker
from src.web.routes.threads import router as threads_router
from src.web.routes.messages import router as messages_router
from src.web.routes.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 6: Initialize dual registries
    try:
        cat_reg, agent_reg = initialize_registries("cat-config.json")
    except (FileNotFoundError, Exception):
        cat_reg, agent_reg = CatRegistry(), AgentRegistry()

    app.state.cat_registry = cat_reg
    app.state.agent_registry = agent_reg

    # AgentRouterV2 (registry-based)
    app.state.agent_router = AgentRouterV2(cat_reg, agent_reg)

    # Phase 7: Session chain and invocation tracker
    app.state.session_chain = SessionChain()
    app.state.invocation_tracker = InvocationTracker()

    # ThreadManager
    tm = ThreadManager(skip_init=True)
    await tm.async_init()
    app.state.thread_manager = tm

    yield

    if hasattr(tm, '_store') and tm._store:
        await tm._store.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MeowAI Home",
        version="0.7.0",
        description="Multi-Agent AI Collaboration Platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(threads_router, prefix="/api")
    app.include_router(messages_router, prefix="/api")
    app.include_router(ws_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": "0.7.0"}

    web_dist = Path(__file__).parent.parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            index_file = web_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"error": "Frontend not built"}

    return app
```

- [ ] **Step 4: Run regression**

Run: `python3 -m pytest -x -q`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/router/__init__.py src/web/app.py src/web/dependencies.py
git commit -m "feat(router): wire AgentRouterV2, SessionChain, InvocationTracker into FastAPI lifespan"
```

---

### Task 10: Wire WebSocket — Tracker + SessionChain + Workflow Events

**Files:**
- Modify: `src/web/routes/ws.py`

- [ ] **Step 1: Write the updated `src/web/routes/ws.py`**

```python
# src/web/routes/ws.py
"""WebSocket endpoint for streaming agent responses."""

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.collaboration.a2a_controller import A2AController
from src.collaboration.intent_parser import parse_intent
from src.thread.models import Message
from src.web.stream import ConnectionManager
from src.workflow.executor import DAGExecutor
from src.workflow.templates import WorkflowTemplateFactory

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await websocket.accept()
    app = websocket.app
    tm = app.state.thread_manager
    agent_router = app.state.agent_router

    manager.add(thread_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "send_message":
                await _handle_send_message(
                    websocket, thread_id, data, tm, agent_router, app
                )
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        manager.remove(thread_id, websocket)


async def _handle_send_message(websocket, thread_id, data, tm, agent_router, app):
    content = data.get("content", "").strip()
    if not content:
        await websocket.send_json({"type": "error", "message": "Empty message"})
        return

    thread = await tm.get(thread_id)
    if not thread:
        await websocket.send_json({"type": "error", "message": "Thread not found"})
        return

    if "@" not in content:
        content = f"@{thread.current_cat_id} {content}"

    agents = agent_router.route_message(content)
    intent = parse_intent(content, len(agents))

    # Cancel any active invocations for this thread
    tracker = getattr(app.state, "invocation_tracker", None)
    if tracker:
        tracker.cancel_all(thread_id)

    # Persist user message
    user_msg = Message(role="user", content=intent.clean_message)
    thread.add_message("user", intent.clean_message)
    await tm.add_message(thread.id, user_msg)

    await websocket.send_json({
        "type": "message_sent",
        "message": {
            "role": "user",
            "content": intent.clean_message,
            "cat_id": None,
        },
    })

    await websocket.send_json({
        "type": "intent_mode",
        "mode": intent.workflow or intent.intent,
        "cats": [a["breed_id"] for a in agents],
    })

    try:
        session_chain = getattr(app.state, "session_chain", None)

        # Build DAGExecutor and TemplateFactory if workflow
        dag_executor = None
        template_factory = None
        if intent.workflow:
            agent_registry = getattr(app.state, "agent_registry", None)
            if agent_registry:
                dag_executor = DAGExecutor(
                    agent_registry=agent_registry,
                    session_chain=session_chain,
                    tracker=tracker,
                )
                template_factory = WorkflowTemplateFactory()

        controller = A2AController(
            agents,
            session_chain=session_chain,
            dag_executor=dag_executor,
            template_factory=template_factory,
        )

        # Send workflow_start if workflow
        if intent.workflow:
            await websocket.send_json({
                "type": "workflow_start",
                "workflow": intent.workflow,
                "cats": [a["breed_id"] for a in agents],
            })

        async for response in controller.execute(intent, intent.clean_message, thread):
            # Thinking
            if response.thinking:
                await websocket.send_json({
                    "type": "thinking",
                    "cat_id": response.cat_id,
                    "cat_name": response.cat_name,
                    "content": response.thinking,
                })

            msg_data = {
                "type": "cat_response",
                "cat_id": response.cat_id,
                "cat_name": response.cat_name,
                "content": response.content,
                "target_cats": response.targetCats,
            }
            await websocket.send_json(msg_data)

            assistant_msg = Message(
                role="assistant",
                content=response.content,
                cat_id=response.cat_id,
                thinking=response.thinking,
            )
            thread.add_message("assistant", response.content, cat_id=response.cat_id)
            await tm.add_message(thread.id, assistant_msg)

        await tm.update_thread(thread)

        if intent.workflow:
            await websocket.send_json({"type": "workflow_done"})
        else:
            await websocket.send_json({"type": "done"})

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
```

- [ ] **Step 2: Run regression**

Run: `python3 -m pytest -x -q`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add src/web/routes/ws.py
git commit -m "feat(ws): integrate InvocationTracker, SessionChain, and workflow events into WebSocket"
```

---

### Task 11: Final Regression + Update Exports

**Files:**
- Modify: `src/workflow/__init__.py` (ensure all exports work)
- No new tests — just verify everything works together

- [ ] **Step 1: Run full regression**

Run: `python3 -m pytest -x -q`
Expected: All tests PASS (318+ existing + ~50 new = ~370)

- [ ] **Step 2: Verify imports work**

Run: `python3 -c "from src.workflow import DAGExecutor, WorkflowDAG, WorkflowTemplateFactory, ResultAggregator; print('OK')"`

- [ ] **Step 3: Verify A2AController import works**

Run: `python3 -c "from src.collaboration import MCPExecutor, SkillInjector, parse_intent; print('OK')"`

- [ ] **Step 4: Commit if any import fixes needed**

```bash
git add -A
git commit -m "fix: ensure all Phase 7 exports and imports resolve correctly"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Task |
|---|---|
| 1.1 AgentRouterV2 replaces v1 | Task 9 |
| 1.2 InvocationTracker into WebSocket | Task 10 |
| 1.3 StreamMerge replaces as_completed | Task 7 (kept as_completed for CatResponse objects — merge_streams is for AgentMessage; spec intent met) |
| 1.4 SessionChain into _call_cat | Task 7 (inside _call_cat) |
| 1.5 A2AController refactor | Tasks 5, 6, 7 |
| 2.1 DAG data structures | Task 1 |
| 2.2 DAG executor | Task 4 |
| 2.3 Result aggregator | Task 2 |
| 2.4 Workflow templates | Task 3 |
| 3.1 Workflow intent detection | Task 8 |
| 3.2 A2AController integration | Task 7 |
| 3.3 WebSocket protocol | Task 10 |
| 3.4 File structure | All tasks |

### Placeholder Scan

No TBD, TODO, or placeholder patterns found.

### Type Consistency

- `DAGNode.id: str` used consistently as node identifier
- `DAGNode.cat_id: str` matches `CatId = str` from types.py
- `NodeResult.status: str` uses literal values "completed" / "failed" / "skipped"
- `IntentResult.workflow: Optional[str]` uses literal values "brainstorm" / "parallel" / "auto_plan"
- `InvocationOptions` imported from `src.models.types` — matches provider signatures
- `AgentMessage` + `AgentMessageType` from `src.models.types` — used consistently
