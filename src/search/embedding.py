"""Embedding provider interface with hash-based fallback"""
from abc import ABC, abstractmethod
from typing import List
import hashlib


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
