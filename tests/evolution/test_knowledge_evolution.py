"""Knowledge Evolution tests"""
import pytest
import tempfile
from pathlib import Path
from src.memory import MemoryDB, SemanticMemory
from src.evolution.knowledge_evolution import KnowledgeEvolution, InferredRelation, _infer_relation_type


@pytest.fixture
def semantic():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDB(str(Path(tmpdir) / "test.db"))
        yield SemanticMemory(db)


class TestMultiHopGetRelated:
    def test_single_hop_unchanged(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_relation("A", "B", "uses")
        related = semantic.get_related("A")
        assert len(related) == 1
        assert related[0]["name"] == "B"

    def test_multi_hop_two_hops(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses")
        semantic.add_relation("B", "C", "depends_on")
        related = semantic.get_related("A", max_depth=2)
        names = [r["name"] for r in related]
        assert "B" in names and "C" in names

    def test_multi_hop_respects_max_depth(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses")
        semantic.add_relation("B", "C", "depends_on")
        related = semantic.get_related("A", max_depth=1)
        assert len(related) == 1
        assert related[0]["name"] == "B"

    def test_multi_hop_cycles_prevented(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_relation("A", "B", "uses")
        semantic.add_relation("B", "A", "uses")
        related = semantic.get_related("A", max_depth=3)
        names = [r["name"] for r in related]
        assert "B" in names
        assert names.count("B") == 1  # no infinite loop

    def test_multi_hop_nonexistent_entity(self, semantic):
        related = semantic.get_related("nonexistent")
        assert related == []

    def test_multi_hop_with_relation_type_filter(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses")
        semantic.add_relation("B", "C", "depends_on")
        related = semantic.get_related("A", relation_type="uses", max_depth=2)
        assert len(related) == 1
        assert related[0]["name"] == "B"


class TestKnowledgeEvolutionInfer:
    def test_infer_relations_finds_indirect(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses", strength=0.9)
        semantic.add_relation("B", "C", "depends_on", strength=0.8)
        ke = KnowledgeEvolution(semantic)
        inferred = ke.infer_relations("A")
        indirect = [r for r in inferred if r.target == "C"]
        assert len(indirect) >= 1

    def test_infer_no_duplicate_for_existing(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_relation("A", "B", "uses")
        ke = KnowledgeEvolution(semantic)
        inferred = ke.infer_relations("A")
        direct = [r for r in inferred if r.target == "B"]
        assert len(direct) == 0

    def test_infer_min_confidence(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses", strength=0.1)
        semantic.add_relation("B", "C", "depends_on", strength=0.1)
        ke = KnowledgeEvolution(semantic)
        inferred = ke.infer_relations("A", min_confidence=0.5)
        assert len(inferred) == 0

    def test_get_graph_subset(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_relation("A", "B", "uses")
        ke = KnowledgeEvolution(semantic)
        graph = ke.get_graph_subset("A", radius=1)
        assert "nodes" in graph and "edges" in graph
        assert len(graph["nodes"]) >= 2

    def test_get_graph_subset_radius(self, semantic):
        semantic.add_entity("A", "concept")
        semantic.add_entity("B", "concept")
        semantic.add_entity("C", "concept")
        semantic.add_relation("A", "B", "uses")
        semantic.add_relation("B", "C", "uses")
        ke = KnowledgeEvolution(semantic)
        graph1 = ke.get_graph_subset("A", radius=1)
        graph2 = ke.get_graph_subset("A", radius=2)
        assert len(graph2["nodes"]) >= len(graph1["nodes"])


class TestInferRelationType:
    def test_preference_technology(self):
        assert _infer_relation_type("preference", "technology") == "prefers_using"

    def test_technology_technology(self):
        assert _infer_relation_type("technology", "technology") == "related_to"

    def test_role_technology(self):
        assert _infer_relation_type("role", "technology") == "works_with"

    def test_unknown_pair(self):
        assert _infer_relation_type("foo", "bar") == "co_occurs_with"
