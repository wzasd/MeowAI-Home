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

        for edge in self.edges:
            if edge.from_node not in node_ids:
                errors.append(f"Edge references missing source node: {edge.from_node}")
            if edge.to_node not in node_ids:
                errors.append(f"Edge references missing target node: {edge.to_node}")

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
