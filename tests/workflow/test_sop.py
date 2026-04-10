"""Phase 8.2: SOP workflow tests"""
import pytest
from unittest.mock import MagicMock

from src.workflow.dag import DAGNode, DAGEdge, NodeResult, QualityGate, WorkflowDAG
from src.workflow.executor import DAGExecutor
from src.workflow.templates import WorkflowTemplateFactory
from src.collaboration.intent_parser import IntentParser, WORKFLOW_TAGS
from src.thread.models import Thread
from src.models.types import AgentMessage, AgentMessageType


def _make_cats():
    return [
        {"breed_id": "orange", "name": "阿橘"},
        {"breed_id": "inky", "name": "墨点"},
        {"breed_id": "patch", "name": "斑点"},
    ]


def _make_stream_fn(cat_id):
    async def stream(prompt="", options=None):
        yield AgentMessage(type=AgentMessageType.TEXT, content=f"response from {cat_id}")
    return stream


def _mock_agent_registry(nodes):
    registry = MagicMock()
    services = {}
    for node in nodes:
        if node.cat_id not in services:
            service = MagicMock()
            service.invoke = _make_stream_fn(node.cat_id)
            service.build_system_prompt = MagicMock(return_value=f"You are {node.cat_id}")
            services[node.cat_id] = service
    registry.get = MagicMock(side_effect=lambda cat_id: services.get(cat_id))
    registry.has = MagicMock(side_effect=lambda cat_id: cat_id in services)
    return registry


# === QualityGate unit tests ===

class TestQualityGate:
    def test_quality_gate_creation(self):
        gate = QualityGate(gate_type="test_exists", description="Tests exist")
        assert gate.gate_type == "test_exists"
        assert gate.description == "Tests exist"

    def test_quality_gate_types(self):
        for gate_type in ["test_pass", "test_exists", "no_blocking", "always"]:
            gate = QualityGate(gate_type=gate_type, description=f"gate {gate_type}")
            assert gate.gate_type == gate_type


# === SOP Template creation tests ===

class TestTDDTemplate:
    def test_creates_valid_dag(self):
        dag = WorkflowTemplateFactory.create("tdd", _make_cats(), "实现登录")
        assert dag.validate() == []

    def test_has_three_sequential_steps(self):
        dag = WorkflowTemplateFactory.create("tdd", _make_cats(), "实现登录")
        layers = dag.topological_layers()
        assert len(layers) == 3

    def test_step_names(self):
        dag = WorkflowTemplateFactory.create("tdd", _make_cats(), "实现登录")
        ids = {n.id for n in dag.nodes}
        assert "write_tests" in ids
        assert "implement" in ids
        assert "refactor" in ids

    def test_gates_on_later_steps(self):
        dag = WorkflowTemplateFactory.create("tdd", _make_cats(), "实现登录")
        node_map = {n.id: n for n in dag.nodes}
        assert node_map["write_tests"].gate is None
        assert node_map["implement"].gate is not None
        assert node_map["implement"].gate.gate_type == "test_exists"
        assert node_map["refactor"].gate is not None
        assert node_map["refactor"].gate.gate_type == "test_pass"

    def test_single_cat_fallback(self):
        """Works with just 1 cat"""
        cats = [{"breed_id": "orange", "name": "阿橘"}]
        dag = WorkflowTemplateFactory.create("tdd", cats, "实现功能")
        assert dag.validate() == []
        assert len(dag.nodes) == 3


class TestReviewTemplate:
    def test_creates_valid_dag(self):
        dag = WorkflowTemplateFactory.create("review", _make_cats(), "审查代码")
        assert dag.validate() == []

    def test_has_three_sequential_steps(self):
        dag = WorkflowTemplateFactory.create("review", _make_cats(), "审查代码")
        layers = dag.topological_layers()
        assert len(layers) == 3

    def test_step_names(self):
        dag = WorkflowTemplateFactory.create("review", _make_cats(), "审查代码")
        ids = {n.id for n in dag.nodes}
        assert "reviewer_1" in ids
        assert "reviewer_2" in ids
        assert "merge_check" in ids

    def test_gates_on_reviewer_2(self):
        dag = WorkflowTemplateFactory.create("review", _make_cats(), "审查代码")
        node_map = {n.id: n for n in dag.nodes}
        assert node_map["reviewer_1"].gate is None
        assert node_map["reviewer_2"].gate is not None
        assert node_map["reviewer_2"].gate.gate_type == "no_blocking"

    def test_merge_check_is_aggregator(self):
        dag = WorkflowTemplateFactory.create("review", _make_cats(), "审查代码")
        merge_node = next(n for n in dag.nodes if n.id == "merge_check")
        assert merge_node.is_aggregator is True


class TestDeployTemplate:
    def test_creates_valid_dag(self):
        dag = WorkflowTemplateFactory.create("deploy", _make_cats(), "发布 v2.0")
        assert dag.validate() == []

    def test_has_three_sequential_steps(self):
        dag = WorkflowTemplateFactory.create("deploy", _make_cats(), "发布 v2.0")
        layers = dag.topological_layers()
        assert len(layers) == 3

    def test_step_names(self):
        dag = WorkflowTemplateFactory.create("deploy", _make_cats(), "发布 v2.0")
        ids = {n.id for n in dag.nodes}
        assert "run_tests" in ids
        assert "build_check" in ids
        assert "release_notes" in ids

    def test_gates(self):
        dag = WorkflowTemplateFactory.create("deploy", _make_cats(), "发布 v2.0")
        node_map = {n.id: n for n in dag.nodes}
        assert node_map["run_tests"].gate is None
        assert node_map["build_check"].gate.gate_type == "test_pass"
        assert node_map["release_notes"].gate.gate_type == "no_blocking"


# === Gate checking tests ===

class TestGateChecking:
    def test_no_gate_always_passes(self):
        dag = WorkflowDAG(
            nodes=[DAGNode(id="a", cat_id="orange", prompt_template="A")],
            edges=[],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        node = dag.nodes[0]
        assert executor._check_gate(node, dag, {}) is True

    def test_gate_always_passes(self):
        gate = QualityGate(gate_type="always", description="always pass")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="ok", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is True

    def test_test_exists_passes(self):
        gate = QualityGate(gate_type="test_exists", description="test exists")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="def test_login(): assert True", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is True

    def test_test_exists_fails(self):
        gate = QualityGate(gate_type="test_exists", description="test exists")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="no tests here", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is False

    def test_test_pass_passes(self):
        gate = QualityGate(gate_type="test_pass", description="tests pass")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="5 passed, 0 failed", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is True

    def test_test_pass_fails_with_failures(self):
        gate = QualityGate(gate_type="test_pass", description="tests pass")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="3 passed, 2 failed", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is False

    def test_no_blocking_passes(self):
        gate = QualityGate(gate_type="no_blocking", description="no blocking")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="minor issues found", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is True

    def test_no_blocking_fails(self):
        gate = QualityGate(gate_type="no_blocking", description="no blocking")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        executor = DAGExecutor(agent_registry=MagicMock())
        completed = {"a": NodeResult(node_id="a", cat_id="orange", content="BLOCKING: SQL injection found", status="completed")}
        assert executor._check_gate(dag.nodes[1], dag, completed) is False


# === Gate integration with executor ===

class TestExecutorGateIntegration:
    @pytest.mark.asyncio
    async def test_gate_block_skips_node(self):
        """Node with failing gate is skipped"""
        gate = QualityGate(gate_type="test_exists", description="test exists")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        # Make first node return content without "test_"
        async def stream_no_test(prompt="", options=None):
            yield AgentMessage(type=AgentMessageType.TEXT, content="no tests here")
        async def stream_b(prompt="", options=None):
            yield AgentMessage(type=AgentMessageType.TEXT, content="should not run")

        registry = MagicMock()
        svc_a = MagicMock()
        svc_a.invoke = stream_no_test
        svc_a.build_system_prompt = MagicMock(return_value="A")
        svc_b = MagicMock()
        svc_b.invoke = stream_b
        svc_b.build_system_prompt = MagicMock(return_value="B")
        services = {"orange": svc_a, "inky": svc_b}
        registry.get = MagicMock(side_effect=lambda k: services.get(k))

        executor = DAGExecutor(agent_registry=registry)
        thread = Thread.create("test")
        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)

        assert len(results) == 2
        assert results[0].status == "completed"
        assert results[1].status == "skipped"

    @pytest.mark.asyncio
    async def test_gate_pass_executes_node(self):
        """Node with passing gate executes normally"""
        gate = QualityGate(gate_type="test_exists", description="test exists")
        dag = WorkflowDAG(
            nodes=[
                DAGNode(id="a", cat_id="orange", prompt_template="A"),
                DAGNode(id="b", cat_id="inky", prompt_template="B", gate=gate),
            ],
            edges=[DAGEdge(from_node="a", to_node="b")],
        )
        registry = _mock_agent_registry(dag.nodes)
        # Override stream for first node to include test_
        svc = MagicMock()
        async def stream_with_test(prompt="", options=None):
            yield AgentMessage(type=AgentMessageType.TEXT, content="def test_func(): assert True")
        svc.invoke = stream_with_test
        svc.build_system_prompt = MagicMock(return_value="A")
        services = {"orange": svc}
        # Reuse inky from _mock_agent_registry
        registry2 = _mock_agent_registry(dag.nodes)
        registry2.get = MagicMock(side_effect=lambda k: svc if k == "orange" else MagicMock(
            invoke=_make_stream_fn(k),
            build_system_prompt=MagicMock(return_value=k),
        ))

        executor = DAGExecutor(agent_registry=registry2)
        thread = Thread.create("test")
        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)

        assert len(results) == 2
        assert results[0].status == "completed"
        assert results[1].status == "completed"


# === IntentParser SOP tag tests ===

class TestIntentParserSOPTags:
    def test_tdd_tag(self):
        parser = IntentParser()
        result = parser.parse("#tdd 实现登录功能", 1)
        assert result.workflow == "tdd"
        assert "tdd" not in result.clean_message.lower()

    def test_review_tag(self):
        parser = IntentParser()
        result = parser.parse("#review 检查这段代码", 1)
        assert result.workflow == "review"

    def test_deploy_tag(self):
        parser = IntentParser()
        result = parser.parse("#deploy 发布 v2.0", 1)
        assert result.workflow == "deploy"

    def test_workflow_tags_include_sop(self):
        assert "tdd" in WORKFLOW_TAGS
        assert "review" in WORKFLOW_TAGS
        assert "deploy" in WORKFLOW_TAGS

    def test_sop_tags_case_insensitive(self):
        parser = IntentParser()
        result = parser.parse("#TDD test-driven", 1)
        assert result.workflow == "tdd"
