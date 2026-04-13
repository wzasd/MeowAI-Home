"""OpenAI embedding provider for semantic search."""
import os
from typing import List, Optional
import aiohttp
import asyncio

from src.search.embedding import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API embedding provider.

    Supports text-embedding-3-small, text-embedding-3-large, text-embedding-ada-002.
    Default: text-embedding-3-small (1536 dimensions, good performance/cost ratio)
    """

    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_DIMENSION = 1536
    API_BASE = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._dimensions = dimensions or self._get_default_dimensions(self.model)

        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key."
            )

    def _get_default_dimensions(self, model: str) -> int:
        """Get default dimensions for model."""
        dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dims.get(model, self.DEFAULT_DIMENSION)

    async def embed(self, text: str) -> List[float]:
        """Generate embedding via OpenAI API."""
        if not text.strip():
            return [0.0] * self._dimensions

        url = f"{self.API_BASE}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": text[:8191],  # OpenAI token limit
            "model": self.model,
        }
        # Add dimensions parameter for v3 models
        if "text-embedding-3" in self.model and self._dimensions:
            payload["dimensions"] = self._dimensions

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"OpenAI API error: {resp.status} - {error_text}")

                data = await resp.json()
                return data["data"][0]["embedding"]

    def dimension(self) -> int:
        return self._dimensions


class OpenAIEmbeddingProviderSync(EmbeddingProvider):
    """Synchronous wrapper for OpenAI embedding (for non-async contexts)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ):
        self._async_provider = OpenAIEmbeddingProvider(api_key, model, dimensions)
        self._dimensions = self._async_provider._dimensions

    def embed(self, text: str) -> List[float]:
        """Generate embedding synchronously."""
        return asyncio.run(self._async_provider.embed(text))

    def dimension(self) -> int:
        return self._dimensions
