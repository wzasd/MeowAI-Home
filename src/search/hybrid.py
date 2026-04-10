"""Hybrid search combining FTS5 BM25 with vector cosine similarity via RRF"""
from typing import Dict, List, Optional, Tuple

from typing import TYPE_CHECKING
from src.search.vector_store import VectorStore

if TYPE_CHECKING:
    from src.memory import EpisodicMemory


class HybridSearch:
    """Reciprocal Rank Fusion of FTS5 and vector search results."""

    def __init__(self, episodic_memory: 'EpisodicMemory', vector_store: VectorStore, rrf_k: int = 60):
        self.episodic = episodic_memory
        self.vector_store = vector_store
        self.rrf_k = rrf_k
        self._text_map: Dict[str, str] = {}

    async def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Tuple[str, str, float]]:
        """Hybrid search: FTS5 + vector with Reciprocal Rank Fusion.

        Returns: [(content_id, content_text, rrf_score)]
        """
        self._text_map = {}

        # 1. FTS5 BM25 results from episodic memory
        fts_results = self._fts_search(query, content_type, limit=limit * 2)

        # 2. Vector similarity results
        vec_results = await self.vector_store.search(query, content_type, limit=limit * 2)

        # 3. RRF fusion
        scores: Dict[str, float] = {}
        for rank, (cid, text, _) in enumerate(fts_results):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            self._text_map[cid] = text

        for rank, (cid, text, _) in enumerate(vec_results):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (self.rrf_k + rank + 1)
            self._text_map.setdefault(cid, text)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(cid, self._text_map.get(cid, ""), score) for cid, score in ranked[:limit]]

    def _fts_search(
        self,
        query: str,
        content_type: Optional[str],
        limit: int,
    ) -> List[Tuple[str, str, float]]:
        """FTS5 search via existing episodic memory."""
        if not query.strip():
            return []

        try:
            # Use EpisodicMemory.search for FTS5 results
            episodes = self.episodic.search(query, limit=limit)
            results = []
            for ep in episodes:
                cid = f"ep_{ep.get('id', id(ep))}"
                text = ep.get("content", "")
                results.append((cid, text, 0.0))  # Score placeholder — RRF uses rank
            return results
        except Exception:
            return []
