"""Vector store tests"""
import pytest
import tempfile
from pathlib import Path
from src.search.vector_store import VectorStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield VectorStore(str(Path(tmpdir) / "test_vectors.db"))


class TestVectorStore:
    @pytest.mark.asyncio
    async def test_upsert_stores_embedding(self, store):
        await store.upsert("ep1", "episode", "Hello world")
        results = await store.search("Hello world", limit=5)
        assert len(results) == 1
        assert results[0][0] == "ep1"
        assert "Hello" in results[0][1]

    @pytest.mark.asyncio
    async def test_upsert_same_id_updates(self, store):
        await store.upsert("ep1", "episode", "Original text")
        await store.upsert("ep1", "episode", "Updated text")
        results = await store.search("Updated", limit=5)
        assert len(results) == 1
        assert "Updated" in results[0][1]

    @pytest.mark.asyncio
    async def test_search_ordered_by_similarity(self, store):
        await store.upsert("ep1", "episode", "Python programming language")
        await store.upsert("ep2", "episode", "Java programming language")
        await store.upsert("ep3", "episode", "Cooking recipes for dinner")
        results = await store.search("Python code", limit=3)
        assert len(results) == 3
        # Python should rank higher than cooking
        ids = [r[0] for r in results]
        assert ids.index("ep1") < ids.index("ep3")

    @pytest.mark.asyncio
    async def test_search_with_content_type_filter(self, store):
        await store.upsert("ep1", "episode", "Python programming")
        await store.upsert("en1", "entity", "Python programming")
        results = await store.search("Python", content_type="episode", limit=5)
        assert len(results) == 1
        assert results[0][0] == "ep1"

    @pytest.mark.asyncio
    async def test_search_empty_store(self, store):
        results = await store.search("anything", limit=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_content_types_coexist(self, store):
        await store.upsert("ep1", "episode", "Machine learning basics")
        await store.upsert("en1", "entity", "Machine learning")
        await store.upsert("pr1", "procedure", "ML workflow steps")
        all_results = await store.search("Machine learning", limit=10)
        assert len(all_results) == 3

    @pytest.mark.asyncio
    async def test_delete_by_content_id(self, store):
        await store.upsert("ep1", "episode", "Test content")
        assert store.delete("ep1", "episode") is True
        results = await store.search("Test", limit=5)
        assert results == []
        assert store.delete("ep1", "episode") is False

    @pytest.mark.asyncio
    async def test_batch_upsert(self, store):
        import time
        start = time.time()
        for i in range(100):
            await store.upsert(f"ep{i}", "episode", f"Document number {i} about topic")
        elapsed = time.time() - start
        assert elapsed < 5.0  # Should complete well under 5s
        results = await store.search("Document", limit=10)
        assert len(results) == 10
