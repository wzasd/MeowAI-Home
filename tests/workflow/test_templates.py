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
    def test_creates_valid_dag(self):
        dag = WorkflowTemplateFactory.create("brainstorm", _make_cats(), "给方案")
        assert isinstance(dag, WorkflowDAG)
        assert dag.validate() == []

    def test_has_parallel_roots(self):
        dag = WorkflowTemplateFactory.create("brainstorm", _make_cats(), "给方案")
        assert len(dag.roots()) == 3

    def test_has_aggregator(self):
        dag = WorkflowTemplateFactory.create("brainstorm", _make_cats(), "给方案")
        assert len([n for n in dag.nodes if n.is_aggregator]) == 1

    def test_edges_connect_to_aggregator(self):
        dag = WorkflowTemplateFactory.create("brainstorm", _make_cats(), "给方案")
        agg = [n for n in dag.nodes if n.is_aggregator][0]
        for root_id in dag.roots():
            assert agg.id in dag.successors(root_id)


class TestParallelTemplate:
    def test_creates_valid_dag(self):
        dag = WorkflowTemplateFactory.create("parallel", _make_cats(), "实现登录")
        assert dag.validate() == []

    def test_has_workers_and_merger(self):
        dag = WorkflowTemplateFactory.create("parallel", _make_cats(), "实现登录")
        assert len(dag.roots()) == 3
        assert len([n for n in dag.nodes if n.is_aggregator]) == 1

    def test_worker_prompts_contain_input(self):
        dag = WorkflowTemplateFactory.create("parallel", _make_cats(), "实现登录功能")
        for root_id in dag.roots():
            node = next(n for n in dag.nodes if n.id == root_id)
            assert "实现登录功能" in node.prompt_template


class TestAutoPlanTemplate:
    def test_single_node(self):
        dag = WorkflowTemplateFactory.create("auto_plan", _make_cats(), "实现登录")
        assert len(dag.nodes) == 1 and len(dag.edges) == 0
        assert dag.nodes[0].cat_id == "orange"

    def test_prompt_requests_json(self):
        dag = WorkflowTemplateFactory.create("auto_plan", _make_cats(), "实现登录")
        assert "JSON" in dag.nodes[0].prompt_template or "json" in dag.nodes[0].prompt_template


class TestFromYaml:
    def test_loads_yaml(self):
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
        assert len(dag.nodes) == 2 and len(dag.edges) == 1
        assert dag.nodes[1].is_aggregator is True
        assert dag.validate() == []


class TestInvalidTemplate:
    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            WorkflowTemplateFactory.create("nonexistent", _make_cats(), "test")

    def test_zero_cats_raises(self):
        with pytest.raises(ValueError):
            WorkflowTemplateFactory.create("brainstorm", [], "test")
