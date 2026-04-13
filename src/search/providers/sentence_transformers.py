"""Sentence-transformers local embedding provider for offline/self-hosted use."""
import os
from typing import List, Optional
import logging

from src.search.embedding import EmbeddingProvider

logger = logging.getLogger(__name__)


class SentenceTransformersProvider(EmbeddingProvider):
    """Local sentence-transformers embedding (no API calls).

    Recommended models:
    - "all-MiniLM-L6-v2" (384 dim, fast, good quality)
    - "all-mpnet-base-v2" (768 dim, better quality)
    - "BAAI/bge-small-zh" (512 dim, optimized for Chinese)

    First call downloads model (~80-400MB).
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv(
            "SENTENCE_TRANSFORMERS_MODEL", self.DEFAULT_MODEL
        )
        self._model = None
        self._dimensions: Optional[int] = None

    def _load_model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(f"Loading sentence-transformers model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._dimensions = self._model.get_sentence_embedding_dimension()
                logger.info(f"Model loaded, dimension: {self._dimensions}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
        return self._model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding locally."""
        if not text.strip():
            self._load_model()
            return [0.0] * self._dimensions

        model = self._load_model()
        # sentence-transformers is synchronous, run in thread pool
        import asyncio

        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, model.encode, text)
        return embedding.tolist()

    def embed_sync(self, text: str) -> List[float]:
        """Synchronous embedding generation."""
        if not text.strip():
            self._load_model()
            return [0.0] * self._dimensions

        model = self._load_model()
        return model.encode(text).tolist()

    def dimension(self) -> int:
        if self._dimensions is None:
            self._load_model()
        return self._dimensions
