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

        # mode == "summarize"
        if not completed:
            return ""
        parts = []
        for r in completed:
            label = f"[{r.cat_id} ({r.node_id})]"
            parts.append(f"{label}\n{r.content}")
        return "\n\n---\n\n".join(parts)
