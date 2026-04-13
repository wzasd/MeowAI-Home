"""Embedding provider interface with hash-based fallback"""
from abc import ABC, abstractmethod
from typing import List, Optional
import hashlib
import os
import logging

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        ...


class HashEmbedding(EmbeddingProvider):
    """Deterministic hash-based pseudo-embedding for testing/small deployments.

    No external API needed. Not semantically meaningful but suitable for
    testing and basic similarity search.
    """

    def __init__(self, dim: int = 128):
        self._dim = dim

    async def embed(self, text: str) -> List[float]:
        """Generate deterministic hash-based pseudo-embedding."""
        tokens = text.lower().split()
        if not tokens:
            return [0.0] * self._dim

        vec = [0.0] * self._dim
        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for d in range(self._dim):
                seed = h + d + i
                vec[d] += (seed % 1000) / 1000.0 - 0.5

        # Normalize to unit vector
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def dimension(self) -> int:
        return self._dim


def create_embedding_provider(
    provider_type: Optional[str] = None,
    **kwargs
) -> EmbeddingProvider:
    """Factory function to create embedding provider.

    Provider types:
    - "openai": OpenAI API (requires OPENAI_API_KEY)
    - "sentence_transformers": Local model (requires sentence-transformers)
    - "hash": Deterministic hash-based (default, no dependencies)

    Args:
        provider_type: Type of provider, or None to auto-detect from env
        **kwargs: Provider-specific arguments

    Returns:
        EmbeddingProvider instance
    """
    if provider_type is None:
        provider_type = os.getenv("EMBEDDING_PROVIDER", "hash").lower()

    if provider_type == "openai":
        try:
            from src.search.providers.openai import OpenAIEmbeddingProvider
            return OpenAIEmbeddingProvider(**kwargs)
        except ValueError as e:
            logger.warning(f"OpenAI provider failed: {e}, falling back to hash")
            return HashEmbedding()

    elif provider_type in ("sentence_transformers", "sentence-transformers", "local"):
        try:
            from src.search.providers.sentence_transformers import SentenceTransformersProvider
            return SentenceTransformersProvider(**kwargs)
        except ImportError as e:
            logger.warning(f"sentence-transformers not available: {e}, falling back to hash")
            return HashEmbedding()

    elif provider_type == "hash":
        return HashEmbedding(**kwargs)

    else:
        logger.warning(f"Unknown provider type: {provider_type}, using hash")
        return HashEmbedding(**kwargs)
