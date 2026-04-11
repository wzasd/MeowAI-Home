"""Article query — high-level query interface for articles."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.signals.sources import SourceTier
from src.signals.store import ArticleStore


@dataclass
class ArticleFilter:
    """Filter criteria for article queries."""
    status: Optional[str] = None  # 'unread', 'read', 'archived'
    source_id: Optional[str] = None
    tier: Optional[SourceTier] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search_query: Optional[str] = None


class ArticleQuery:
    """High-level query interface for articles."""

    def __init__(self, store: Optional[ArticleStore] = None):
        self.store = store or ArticleStore()

    def inbox(self, limit: int = 50) -> List[Dict]:
        """Get unread articles, newest first."""
        return self.store.list_by_status('unread', limit=limit)

    def recent(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """Get articles from the last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        # Get all recent and filter
        articles = self.store.list_recent(limit=limit * 2)
        cutoff = since.isoformat()
        return [
            a for a in articles
            if a.get('fetched_at', '') >= cutoff
        ][:limit]

    def by_source(self, source_id: str, limit: int = 50) -> List[Dict]:
        """Get articles from a specific source."""
        return self.store.list_by_source(source_id, limit=limit)

    def by_tier(self, tier: SourceTier, limit: int = 50) -> List[Dict]:
        """Get articles by priority tier."""
        return self.store.list_by_tier(tier, limit=limit)

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Full-text search across articles."""
        return self.store.search(query, limit=limit)

    def filter(self, criteria: ArticleFilter, limit: int = 50) -> List[Dict]:
        """Query with multiple filter criteria."""
        # Start with search if provided
        if criteria.search_query:
            articles = self.store.search(criteria.search_query, limit=limit * 2)
        elif criteria.source_id:
            articles = self.store.list_by_source(criteria.source_id, limit=limit * 2)
        elif criteria.tier:
            articles = self.store.list_by_tier(criteria.tier, limit=limit * 2)
        elif criteria.status:
            articles = self.store.list_by_status(criteria.status, limit=limit * 2)
        else:
            articles = self.store.list_recent(limit=limit * 2)

        # Apply additional filters
        results = []
        for article in articles:
            if criteria.status and article.get('status') != criteria.status:
                continue
            if criteria.source_id and article.get('source_id') != criteria.source_id:
                continue
            if criteria.tier and article.get('tier') != criteria.tier.value:
                continue
            if criteria.date_from:
                fetched = article.get('fetched_at', '')
                if fetched < criteria.date_from.isoformat():
                    continue
            if criteria.date_to:
                fetched = article.get('fetched_at', '')
                if fetched > criteria.date_to.isoformat():
                    continue
            results.append(article)

        return results[:limit]

    def get(self, article_id: int) -> Optional[Dict]:
        """Get article by ID."""
        return self.store.get_by_id(article_id)

    def stats(self) -> Dict[str, Any]:
        """Get article statistics."""
        return self.store.get_stats()

    def mark_read(self, article_id: int) -> bool:
        """Mark article as read."""
        return self.store.mark_read(article_id)

    def mark_archived(self, article_id: int) -> bool:
        """Mark article as archived."""
        return self.store.mark_archived(article_id)

    def unread_count(self) -> int:
        """Get count of unread articles."""
        stats = self.store.get_stats()
        return stats.get('unread', 0)

    def top_keywords(self, limit: int = 20) -> List[tuple]:
        """Extract top keywords from recent articles (simple frequency)."""
        articles = self.store.list_recent(limit=100)
        from collections import Counter
        import re

        word_counts = Counter()
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'and', 'but', 'or', 'yet', 'so', 'if',
                     'because', 'although', 'though', 'while', 'where', 'when',
                     'that', 'which', 'who', 'whom', 'whose', 'what', 'this',
                     'these', 'those', 'i', 'me', 'my', 'myself', 'we', 'our',
                     'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it',
                     'its', 'they', 'them', 'their', 's', 't', 'just', 'don',
                     'now', 'll', 'm', 're', 've', 'd', 'got', 'get', 'go',
                     'new', 'said', 'say', 'says', 'one', 'two', 'three'}

        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            # Simple word extraction
            words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            for word in words:
                if word not in stopwords:
                    word_counts[word] += 1

        return word_counts.most_common(limit)
