"""Process Evolution — track and optimize SOP workflows"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.memory import ProceduralMemory


@dataclass
class OptimizationSuggestion:
    procedure_name: str
    category: str
    success_rate: float
    usage_count: int
    suggestion: str


class ProcessEvolution:
    def __init__(self, procedural_memory: ProceduralMemory):
        self.procedural = procedural_memory

    def store_or_update(
        self,
        name: str,
        category: str = "workflow",
        steps: List[str] = None,
        trigger_conditions: List[str] = None,
        outcomes: Dict[str, Any] = None,
        success: bool = True,
    ) -> int:
        existing = self.procedural.find_by_name_category(name, category)
        if existing:
            self.procedural.record_use(existing["id"], success=success)
            return existing["id"]
        pid = self.procedural.store_procedure(
            name=name, category=category,
            steps=steps, trigger_conditions=trigger_conditions,
            outcomes=outcomes,
        )
        self.procedural.record_use(pid, success=success)
        return pid

    def get_suggestions(self, min_usage: int = 3, limit: int = 5) -> List[OptimizationSuggestion]:
        practices = self.procedural.get_best_practices(min_successes=min_usage, limit=limit * 2)
        all_procs = self.procedural.get_by_category("workflow", limit=50)

        all_with_counts = []
        seen_ids = set()
        for p in practices + all_procs:
            if p["id"] in seen_ids:
                continue
            seen_ids.add(p["id"])
            total = p["success_count"] + p["fail_count"]
            if total < min_usage:
                continue
            rate = p["success_count"] / total if total > 0 else 0
            all_with_counts.append({
                "name": p["name"], "category": p.get("category", "workflow"),
                "rate": rate, "total": total,
            })

        suggestions = []
        for item in all_with_counts[:limit]:
            rate = item["rate"]
            if rate >= 0.8:
                text = "流程表现稳定，建议作为标准SOP推广"
            elif rate >= 0.5:
                text = "流程部分失败，建议检查失败步骤并优化"
            else:
                text = "流程失败率过高，建议重新设计触发条件"
            suggestions.append(OptimizationSuggestion(
                procedure_name=item["name"],
                category=item["category"],
                success_rate=rate,
                usage_count=item["total"],
                suggestion=text,
            ))
        return suggestions
