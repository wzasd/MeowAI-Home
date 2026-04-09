import pytest
from unittest.mock import MagicMock
from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG, NodeResult
from src.workflow.executor import DAGExecutor
from src.thread.models import Thread
from src.models.types import AgentMessage, AgentMessageType


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
        edges=[DAGEdge(from_node="p1", to_node="merge"), DAGEdge(from_node="p2", to_node="merge")],
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
        assert results[0].node_id == "a" and results[1].node_id == "b"

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
        assert "merge" in ids
        merge_idx = ids.index("merge")
        assert "p1" in ids[:merge_idx]
        assert "p2" in ids[:merge_idx]

    @pytest.mark.asyncio
    async def test_invalid_dag_raises(self):
        dag = WorkflowDAG(
            nodes=[DAGNode(id="a", cat_id="orange", prompt_template="A")],
            edges=[DAGEdge(from_node="a", to_node="missing")],
        )
        executor = DAGExecutor(agent_registry=_mock_agent_registry(dag.nodes))
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
        executor = DAGExecutor(agent_registry=_mock_agent_registry(dag.nodes))
        thread = Thread.create("test")
        results = []
        async for r in executor.execute(dag, "hello", thread):
            results.append(r)
        assert len(results) == 1 and results[0].status == "completed"
