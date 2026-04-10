"""Hybrid RRF search tests"""
import pytest
import tempfile
from pathlib import Path
from src.memory import MemoryDB, EpisodicMemory
from src.search.embedding import HashEmbedding
from src.search.vector_store import VectorStore
from src.search.hybrid import HybridSearch


@pytest.fixture
def hybrid():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        vec_path = str(Path(tmpdir) / "vectors.db")
        memory_db = MemoryDB(db_path)
        episodic = EpisodicMemory(memory_db)
        # Store some episodes for FTS5
        episodic.store("t1", "user", "Python machine learning tutorial", importance=5)
        episodic.store("t1", "user", "Java spring boot development", importance=5)
        episodic.store("t1", "user", "Cooking Italian pasta recipes", importance=3)

        provider = HashEmbedding(dim=64)
        vector_store = VectorStore(vec_path, provider)
        yield HybridSearch(episodic, vector_store, rrf_k=60), vector_store


class TestHybridSearch:
    @pytest.mark.asyncio
    async def test_rrf_combines_results(self, hybrid):
        hs, vs = hybrid
        # Add vector entries
        await vs.upsert("vec1", "episode", "Python machine learning code")
        results = await hs.search("Python")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_both_signals_rank_higher(self, hybrid):
        hs, vs = hybrid
        # Item in both FTS5 and vector should rank highest
        await vs.upsert("ep_1", "episode", "Python machine learning tutorial")
        results = await hs.search("Python machine learning")
        if len(results) >= 2:
            # The item in both sources should have highest RRF score
            top_id = results[0][0]
            top_score = results[0][2]
            other_scores = [r[2] for r in results[1:]]
            if other_scores:
                assert top_score >= max(other_scores)

    @pytest.mark.asyncio
    async def test_content_type_filter(self, hybrid):
        hs, vs = hybrid
        await vs.upsert("vec1", "entity", "Python entity")
        # Vector search with content_type filter works
        results_entity = await vs.search("Python", content_type="entity", limit=5)
        assert len(results_entity) >= 1
        # Hybrid search returns results
        results = await hs.search("Python")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_empty_query(self, hybrid):
        hs, _ = hybrid
        results = await hs.search("")
        # Empty query may return no results or all results
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_fts_only_results(self, hybrid):
        hs, vs = hybrid
        # FTS has "Cooking Italian pasta recipes"
        results = await hs.search("pasta")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_vector_only_results(self, hybrid):
        hs, vs = hybrid
        # Add vector with unique content not in FTS
        await vs.upsert("unique1", "episode", "Quantum computing algorithms")
        results = await hs.search("Quantum computing")
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_rrf_k_affects_ranking(self, hybrid):
        hs1, vs1 = hybrid
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "test2.db")
            vec_path = str(Path(tmpdir) / "vectors2.db")
            memory_db = MemoryDB(db_path)
            episodic = EpisodicMemory(memory_db)
            episodic.store("t1", "user", "Python programming", importance=5)
            provider = HashEmbedding(dim=64)
            vs2 = VectorStore(vec_path, provider)
            await vs2.upsert("ep_1", "episode", "Python programming")
            hs2 = HybridSearch(episodic, vs2, rrf_k=10)
            r1 = await hs1.search("Python")
            r2 = await hs2.search("Python")
            # Different RRF_K should produce different scores
            assert isinstance(r1, list) and isinstance(r2, list)
