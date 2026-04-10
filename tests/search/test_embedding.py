"""Embedding provider tests"""
import pytest
from src.search.embedding import HashEmbedding


@pytest.fixture
def embedder():
    return HashEmbedding(dim=64)


class TestHashEmbedding:
    @pytest.mark.asyncio
    async def test_returns_correct_dimension(self, embedder):
        vec = await embedder.embed("hello world")
        assert len(vec) == 64
        assert embedder.dimension() == 64

    @pytest.mark.asyncio
    async def test_same_text_same_embedding(self, embedder):
        vec1 = await embedder.embed("hello world")
        vec2 = await embedder.embed("hello world")
        assert vec1 == vec2

    @pytest.mark.asyncio
    async def test_different_text_different_embedding(self, embedder):
        vec1 = await embedder.embed("hello world")
        vec2 = await embedder.embed("goodbye moon")
        # Should differ in at least some dimensions
        diffs = sum(1 for a, b in zip(vec1, vec2) if abs(a - b) > 0.001)
        assert diffs > 0

    @pytest.mark.asyncio
    async def test_embedding_is_normalized(self, embedder):
        vec = await embedder.embed("some text here")
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 0.001

    @pytest.mark.asyncio
    async def test_empty_text_returns_zero_vector(self, embedder):
        vec = await embedder.embed("")
        assert all(v == 0.0 for v in vec)

    @pytest.mark.asyncio
    async def test_dimension_configurable(self):
        e32 = HashEmbedding(dim=32)
        vec = await e32.embed("test")
        assert len(vec) == 32
        assert e32.dimension() == 32
