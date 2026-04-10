"""Knowledge Evolution — multi-hop traversal and relation inference"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from src.memory import SemanticMemory


@dataclass
class InferredRelation:
    source: str
    target: str
    relation_type: str
    confidence: float
    evidence: str


def _infer_relation_type(source_type: str, target_type: str) -> str:
    TYPE_PAIR_RELATIONS = {
        ("preference", "technology"): "prefers_using",
        ("technology", "technology"): "related_to",
        ("preference", "constraint"): "conflicts_with",
        ("role", "technology"): "works_with",
        ("role", "preference"): "has_preference",
    }
    return TYPE_PAIR_RELATIONS.get((source_type, target_type), "co_occurs_with")


class KnowledgeEvolution:
    def __init__(self, semantic_memory: SemanticMemory):
        self.semantic = semantic_memory

    def infer_relations(
        self,
        entity_name: str,
        min_confidence: float = 0.3,
    ) -> List[InferredRelation]:
        # Get direct neighbors
        direct = self.semantic.get_related(entity_name, max_depth=1)
        direct_names = {r["name"] for r in direct}

        # Get 2-hop neighbors
        two_hop = self.semantic.get_related(entity_name, max_depth=2)
        two_hop_only = [
            r for r in two_hop
            if r["name"] not in direct_names and r["depth"] == 2
        ]

        inferred = []
        for r in two_hop_only:
            confidence = r.get("strength", 0.5)
            if confidence < min_confidence:
                continue
            evidence = f"{entity_name} --indirect--> {r['name']} (via {r['relation']})"
            inferred.append(InferredRelation(
                source=entity_name, target=r["name"],
                relation_type=f"inferred_{r.get('relation', 'related_to')}",
                confidence=confidence,
                evidence=evidence,
            ))
        return inferred

    def get_graph_subset(
        self,
        center_entity: str,
        radius: int = 2,
    ) -> Dict[str, Any]:
        related = self.semantic.get_related(center_entity, max_depth=radius)
        center = self.semantic.get_entity(center_entity)

        nodes_set = {center_entity}
        edges = []
        if center:
            for r in related:
                nodes_set.add(r["name"])
                edges.append({
                    "source": center_entity, "target": r["name"],
                    "type": r["relation"], "strength": r["strength"],
                })

        # Also get relations between non-center nodes within radius
        for r in related:
            sub_related = self.semantic.get_related(r["name"], max_depth=1)
            for sr in sub_related:
                if sr["name"] in nodes_set:
                    nodes_set.add(r["name"])
                    edges.append({
                        "source": r["name"], "target": sr["name"],
                        "type": sr["relation"], "strength": sr["strength"],
                    })

        nodes = []
        for name in nodes_set:
            entity = self.semantic.get_entity(name)
            nodes.append({
                "id": name,
                "type": entity["type"] if entity else "unknown",
            })

        return {"nodes": nodes, "edges": edges}
