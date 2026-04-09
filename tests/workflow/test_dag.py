import pytest
from src.workflow.dag import DAGNode, DAGEdge, WorkflowDAG, NodeResult


def _make_linear_dag():
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="Do A: {input}"),
        DAGNode(id="b", cat_id="inky", prompt_template="Do B: {prev_results}"),
        DAGNode(id="c", cat_id="patch", prompt_template="Final: {prev_results}", is_aggregator=True),
    ]
    edges = [DAGEdge(from_node="a", to_node="b"), DAGEdge(from_node="b", to_node="c")]
    return WorkflowDAG(nodes=nodes, edges=edges)


def _make_diamond_dag():
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="Start: {input}"),
        DAGNode(id="b", cat_id="inky", prompt_template="Review: {prev_results}"),
        DAGNode(id="c", cat_id="patch", prompt_template="Research: {prev_results}"),
        DAGNode(id="d", cat_id="orange", prompt_template="Merge: {prev_results}", is_aggregator=True),
    ]
    edges = [
        DAGEdge(from_node="a", to_node="b"), DAGEdge(from_node="a", to_node="c"),
        DAGEdge(from_node="b", to_node="d"), DAGEdge(from_node="c", to_node="d"),
    ]
    return WorkflowDAG(nodes=nodes, edges=edges)


def _make_cycle_dag():
    nodes = [
        DAGNode(id="a", cat_id="orange", prompt_template="A"),
        DAGNode(id="b", cat_id="inky", prompt_template="B"),
        DAGNode(id="c", cat_id="patch", prompt_template="C"),
    ]
    edges = [DAGEdge(from_node="a", to_node="b"), DAGEdge(from_node="b", to_node="c"), DAGEdge(from_node="c", to_node="a")]
    return WorkflowDAG(nodes=nodes, edges=edges)


class TestWorkflowDAG:
    def test_roots_linear(self):
        assert _make_linear_dag().roots() == ["a"]

    def test_roots_single(self):
        dag = WorkflowDAG(nodes=[DAGNode(id="solo", cat_id="orange", prompt_template="{input}")], edges=[])
        assert dag.roots() == ["solo"]

    def test_roots_diamond(self):
        assert _make_diamond_dag().roots() == ["a"]

    def test_successors(self):
        dag = _make_diamond_dag()
        assert set(dag.successors("a")) == {"b", "c"}
        assert dag.successors("d") == []

    def test_predecessors(self):
        dag = _make_diamond_dag()
        assert dag.predecessors("a") == []
        assert set(dag.predecessors("d")) == {"b", "c"}

    def test_validate_ok(self):
        assert _make_linear_dag().validate() == []

    def test_validate_cycle(self):
        errors = _make_cycle_dag().validate()
        assert len(errors) > 0
        assert any("cycle" in e.lower() for e in errors)

    def test_validate_missing_node(self):
        dag = WorkflowDAG(
            nodes=[DAGNode(id="a", cat_id="orange", prompt_template="A")],
            edges=[DAGEdge(from_node="a", to_node="missing")],
        )
        errors = dag.validate()
        assert any("missing" in e.lower() for e in errors)

    def test_topological_layers_linear(self):
        assert _make_linear_dag().topological_layers() == [["a"], ["b"], ["c"]]

    def test_topological_layers_diamond(self):
        layers = _make_diamond_dag().topological_layers()
        assert len(layers) == 3
        assert layers[0] == ["a"]
        assert set(layers[1]) == {"b", "c"}
        assert layers[2] == ["d"]

    def test_topological_layers_single(self):
        dag = WorkflowDAG(nodes=[DAGNode(id="solo", cat_id="orange", prompt_template="{input}")], edges=[])
        assert dag.topological_layers() == [["solo"]]


class TestNodeResult:
    def test_completed(self):
        r = NodeResult(node_id="a", cat_id="orange", content="done", status="completed")
        assert r.status == "completed" and r.error is None

    def test_failed(self):
        r = NodeResult(node_id="a", cat_id="orange", content="", status="failed", error="boom")
        assert r.status == "failed" and r.error == "boom"
