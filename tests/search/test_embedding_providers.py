"""Tests for embedding providers."""

import os
import pytest

from src.search.embedding import create_embedding_provider, HashEmbedding
from src.search.providers.openai import OpenAIEmbeddingProvider
from src.search.cache import EmbeddingCache
import tempfile


class TestCreateEmbeddingProvider:
    """Tests for provider factory function."""

    def test_create_hash_provider(self):
        """Test creating hash provider."""
        provider = create_embedding_provider("hash")
        assert isinstance(provider, HashEmbedding)
        assert provider.dimension() == 128

    def test_create_hash_with_custom_dim(self):
        """Test creating hash provider with custom dimension."""
        provider = create_embedding_provider("hash", dim=256)
        assert provider.dimension() == 256

    def test_create_unknown_provider_fallback_to_hash(self):
        """Test unknown provider type falls back to hash."""
        provider = create_embedding_provider("unknown_provider_xyz")
        assert isinstance(provider, HashEmbedding)

    def test_create_from_env(self, monkeypatch):
        """Test provider creation from environment variable."""
        monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
        provider = create_embedding_provider()
        assert isinstance(provider, HashEmbedding)

    def test_default_is_hash(self):
        """Test default provider is hash when env not set."""
        # Clear env var if set
        old_val = os.environ.pop("EMBEDDING_PROVIDER", None)
        try:
            provider = create_embedding_provider()
            assert isinstance(provider, HashEmbedding)
        finally:
            if old_val:
                os.environ["EMBEDDING_PROVIDER"] = old_val


class TestHashEmbeddingAsync:
    """Async tests for HashEmbedding."""

    @pytest.mark.asyncio
    async def test_embed_async(self):
        """Test async embed method."""
        provider = HashEmbedding(dim=128)
        vec = await provider.embed("hello world")
        assert len(vec) == 128
        assert all(-1.0 <= v <= 1.0 for v in vec)

    @pytest.mark.asyncio
    async def test_embed_consistency(self):
        """Test same text produces same embedding."""
        provider = HashEmbedding()
        vec1 = await provider.embed("test text")
        vec2 = await provider.embed("test text")
        assert vec1 == vec2

    @pytest.mark.asyncio
    async def test_embed_different_texts(self):
        """Test different texts produce different embeddings."""
        provider = HashEmbedding()
        vec1 = await provider.embed("hello")
        vec2 = await provider.embed("world")
        assert vec1 != vec2


class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    @pytest.fixture
    def cache(self):
        """Create temp cache for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        cache = EmbeddingCache(db_path, provider_name="test", dimension=128)
        yield cache
        # Cleanup
        import os
        os.unlink(db_path)

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("never cached text")
        assert result is None

    def test_cache_set_and_get(self, cache):
        """Test setting and getting from cache."""
        text = "test text for caching"
        embedding = [0.1] * 128

        cache.set(text, embedding)
        retrieved = cache.get(text)

        assert retrieved is not None
        assert len(retrieved) == 128
        assert all(abs(a - b) < 0.0001 for a, b in zip(embedding, retrieved))

    def test_cache_invalidation(self, cache):
        """Test cache invalidation."""
        text = "text to invalidate"
        embedding = [0.2] * 128

        cache.set(text, embedding)
        assert cache.get(text) is not None

        cache.invalidate(text)
        assert cache.get(text) is None

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        stats = cache.stats()
        assert "total_entries" in stats
        assert stats["total_entries"] == 0

        cache.set("text", [0.1] * 128)
        stats = cache.stats()
        assert stats["total_entries"] == 1

    def test_cache_clear(self, cache):
        """Test clearing cache."""
        cache.set("text1", [0.1] * 128)
        cache.set("text2", [0.2] * 128)

        cache.clear()
        assert cache.get("text1") is None
        assert cache.get("text2") is None


class TestVectorStoreWithCache:
    """Tests for VectorStore with caching enabled."""

    @pytest.fixture
    def store(self):
        """Create temp vector store with cache."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = VectorStore(db_path, use_cache=True)
        yield store
        # Cleanup
        import os
        os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_provider_info(self, store):
        """Test getting provider info."""
        info = store.get_provider_info()
        assert "type" in info
        assert "dimension" in info
        assert "has_cache" in info
        assert info["has_cache"] is True

    def test_cache_stats_from_store(self, store):
        """Test getting cache stats through store."""
        stats = store.cache_stats()
        assert stats is not None
        assert "total_entries" in stats

    def test_clear_cache_through_store(self, store):
        """Test clearing cache through store."""
        assert store.clear_cache() is True
        stats = store.cache_stats()
        assert stats["total_entries"] == 0


# Import here to avoid issues if dependencies not installed
try:
    from src.search.vector_store import VectorStore
except ImportError:
    pass
