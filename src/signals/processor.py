"""Source processor — fetch, filter, dedup, store pipeline."""

import logging
from typing import Callable, Dict, List, Optional, Set

from src.signals.fetchers import (
    BaseFetcher,
    FetchedArticle,
    JSONFetcher,
    RSSFetcher,
    WebpageFetcher,
)
from src.signals.sources import FetchMethod, SignalSource, SourceConfig, SourceTier
from src.signals.store import ArticleStore

logger = logging.getLogger(__name__)


class SourceProcessor:
    """Processes sources through fetch → filter → dedup → store → notify pipeline."""

    def __init__(
        self,
        source_registry: Optional[SignalSource] = None,
        article_store: Optional[ArticleStore] = None,
    ):
        self.sources = source_registry or SignalSource()
        self.store = article_store or ArticleStore()
        self._fetcher_map: Dict[FetchMethod, type] = {
            FetchMethod.RSS: RSSFetcher,
            FetchMethod.JSON: JSONFetcher,
            FetchMethod.WEBPAGE: WebpageFetcher,
        }
        self._notification_handlers: List[Callable] = []

    def register_notifier(self, handler: Callable) -> None:
        """Register a notification handler for new articles."""
        self._notification_handlers.append(handler)

    def get_fetcher(self, config: SourceConfig) -> BaseFetcher:
        """Get appropriate fetcher for source config."""
        fetcher_class = self._fetcher_map.get(config.method)
        if not fetcher_class:
            raise ValueError(f"Unknown fetch method: {config.method}")
        return fetcher_class(config)

    async def process_source(self, source_id: str) -> Dict:
        """Process a single source."""
        config = self.sources.get(source_id)
        if not config:
            return {"error": f"Source not found: {source_id}"}

        if not config.enabled:
            return {"source_id": source_id, "processed": 0, "skipped": "disabled"}

        logger.info(f"Processing source: {source_id} ({config.name})")

        try:
            fetcher = self.get_fetcher(config)
            articles = await fetcher.fetch()

            # Deduplication
            new_articles = await self._dedup_articles(articles)

            # Store new articles
            stored_count = 0
            for article in new_articles:
                article.source_id = source_id
                if self.store.store(article, tier=config.tier):
                    stored_count += 1
                    await self._notify_new_article(article, config)

            result = {
                "source_id": source_id,
                "fetched": len(articles),
                "new": stored_count,
                "tier": config.tier.value,
            }
            logger.info(f"Source {source_id}: fetched {len(articles)}, new {stored_count}")
            return result

        except Exception as e:
            logger.error(f"Error processing source {source_id}: {e}")
            return {
                "source_id": source_id,
                "error": str(e),
            }

    async def process_all(self) -> List[Dict]:
        """Process all enabled sources."""
        sources = self.sources.list_enabled()
        results = []
        for source in sources:
            result = await self.process_source(source.source_id)
            results.append(result)
        return results

    async def process_by_tier(self, tier: SourceTier) -> List[Dict]:
        """Process all sources of a specific tier."""
        sources = self.sources.list_by_tier(tier)
        results = []
        for source in sources:
            if source.enabled:
                result = await self.process_source(source.source_id)
                results.append(result)
        return results

    async def _dedup_articles(self, articles: List[FetchedArticle]) -> List[FetchedArticle]:
        """Filter out articles that already exist in database."""
        hashes = {a.content_hash for a in articles}
        existing = self.store.get_existing_hashes(hashes)
        return [a for a in articles if a.content_hash not in existing]

    async def _notify_new_article(self, article: FetchedArticle, config: SourceConfig) -> None:
        """Notify handlers about new article."""
        for handler in self._notification_handlers:
            try:
                handler(article, config)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

    def get_stats(self) -> Dict:
        """Get processing stats."""
        return {
            "sources_total": len(self.sources.list_all()),
            "sources_enabled": len(self.sources.list_enabled()),
            "articles": self.store.get_stats(),
        }

    def select_sources_for_run(self, tier: Optional[SourceTier] = None) -> List[SourceConfig]:
        """Select sources for a processing run."""
        if tier:
            return [s for s in self.sources.list_by_tier(tier) if s.enabled]
        return self.sources.list_enabled()
