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
        merged = ResultAggregator.aggregate(_make_results(), mode="merge")
        assert "Part A" in merged
        assert "Part B" in merged
        assert "Part C failed" not in merged

    def test_last_mode(self):
        assert ResultAggregator.aggregate(_make_results(), mode="last") == "Part B"

    def test_merge_empty(self):
        assert ResultAggregator.aggregate([], mode="merge") == ""

    def test_last_empty(self):
        assert ResultAggregator.aggregate([], mode="last") == ""

    def test_merge_single(self):
        r = NodeResult(node_id="a", cat_id="orange", content="Solo", status="completed")
        assert ResultAggregator.aggregate([r], mode="merge") == "Solo"

    def test_summarize_concatenates_with_labels(self):
        results = _make_results()[:2]
        result = ResultAggregator.aggregate(results, mode="summarize")
        assert "orange" in result
        assert "Part A" in result
