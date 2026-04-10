"""Process Evolution tests"""
import pytest
import tempfile
from pathlib import Path
from src.memory import MemoryDB, ProceduralMemory
from src.evolution.process_evolution import ProcessEvolution, OptimizationSuggestion


@pytest.fixture
def procedural():
    with tempfile.TemporaryDirectory() as tmpdir:
        db = MemoryDB(str(Path(tmpdir) / "test.db"))
        yield ProceduralMemory(db)


class TestProceduralFindByName:
    def test_find_by_name_category_found(self, procedural):
        pid = procedural.store_procedure("tdd", category="workflow", steps=["write", "implement"])
        result = procedural.find_by_name_category("tdd", "workflow")
        assert result is not None
        assert result["id"] == pid
        assert result["name"] == "tdd"

    def test_find_by_name_category_not_found(self, procedural):
        result = procedural.find_by_name_category("nonexistent", "workflow")
        assert result is None

    def test_find_by_name_category_different_category(self, procedural):
        procedural.store_procedure("review", category="workflow")
        result = procedural.find_by_name_category("review", "other")
        assert result is None


class TestProcessEvolutionStoreOrUpdate:
    def test_creates_new_procedure(self, procedural):
        pe = ProcessEvolution(procedural)
        pid = pe.store_or_update("tdd", category="workflow", steps=["write", "run"])
        assert pid > 0

    def test_deduplicates_same_name_category(self, procedural):
        pe = ProcessEvolution(procedural)
        pid1 = pe.store_or_update("tdd", category="workflow", steps=["write", "run"])
        pid2 = pe.store_or_update("tdd", category="workflow", steps=["write", "run"])
        assert pid1 == pid2

    def test_different_category_separate(self, procedural):
        pe = ProcessEvolution(procedural)
        pid1 = pe.store_or_update("review", category="workflow")
        pid2 = pe.store_or_update("review", category="custom")
        assert pid1 != pid2

    def test_record_use_on_success(self, procedural):
        pe = ProcessEvolution(procedural)
        pid = pe.store_or_update("tdd", category="workflow", success=True)
        proc = procedural.find_by_name_category("tdd", "workflow")
        assert proc["success_count"] == 1

    def test_record_use_on_failure(self, procedural):
        pe = ProcessEvolution(procedural)
        pid = pe.store_or_update("tdd", category="workflow", success=False)
        proc = procedural.find_by_name_category("tdd", "workflow")
        assert proc["fail_count"] == 1


class TestProcessEvolutionSuggestions:
    def _seed_procedures(self, procedural):
        # High success
        pid1 = procedural.store_procedure("stable_sop", category="workflow")
        for _ in range(8):
            procedural.record_use(pid1, success=True)
        for _ in range(2):
            procedural.record_use(pid1, success=False)
        # Low success
        pid2 = procedural.store_procedure("failing_sop", category="workflow")
        for _ in range(2):
            procedural.record_use(pid2, success=True)
        for _ in range(8):
            procedural.record_use(pid2, success=False)

    def test_suggestion_high_success(self, procedural):
        self._seed_procedures(procedural)
        pe = ProcessEvolution(procedural)
        suggestions = pe.get_suggestions(min_usage=3)
        high = [s for s in suggestions if s.procedure_name == "stable_sop"]
        assert len(high) == 1
        assert "推广" in high[0].suggestion

    def test_suggestion_low_success(self, procedural):
        self._seed_procedures(procedural)
        pe = ProcessEvolution(procedural)
        suggestions = pe.get_suggestions(min_usage=3)
        low = [s for s in suggestions if s.procedure_name == "failing_sop"]
        assert len(low) == 1
        assert "重新设计" in low[0].suggestion

    def test_suggestion_empty_when_no_data(self, procedural):
        pe = ProcessEvolution(procedural)
        assert pe.get_suggestions(min_usage=3) == []
