"""Tests for ArticleQuery."""
import pytest
from datetime import datetime, timedelta

from src.signals.fetchers import FetchedArticle
from src.signals.query import ArticleFilter, ArticleQuery
from src.signals.sources import SourceTier
from src.signals.store import ArticleStore


@pytest.fixture
def query(tmp_path):
    db_path = str(tmp_path / "test_query.db")
    store = ArticleStore(db_path=db_path)
    return ArticleQuery(store=store)


@pytest.fixture
def sample_articles():
    return [
        FetchedArticle(
            url="https://example.com/python",
            title="Python Programming",
            content="Learn Python",
            source_id="source-a",
        ),
        FetchedArticle(
            url="https://example.com/js",
            title="JavaScript Guide",
            content="JS tutorial",
            source_id="source-b",
        ),
        FetchedArticle(
            url="https://example.com/ai",
            title="AI Overview",
            content="Artificial Intelligence",
            source_id="source-a",
        ),
    ]


class TestArticleQuery:
    def test_inbox(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        inbox = query.inbox(limit=10)
        assert len(inbox) == 3
        assert all(a["status"] == "unread" for a in inbox)

    def test_recent(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        recent = query.recent(hours=24, limit=10)
        assert len(recent) == 3

    def test_by_source(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        source_a = query.by_source("source-a")
        assert len(source_a) == 2
        assert all(a["source_id"] == "source-a" for a in source_a)

    def test_by_tier(self, query, sample_articles):
        query.store.store(sample_articles[0], tier=SourceTier.P0)
        query.store.store(sample_articles[1], tier=SourceTier.P1)

        p0 = query.by_tier(SourceTier.P0)
        assert len(p0) == 1
        assert p0[0]["tier"] == "p0"

    def test_get(self, query, sample_articles):
        query.store.store(sample_articles[0])

        article_hash = sample_articles[0].content_hash
        retrieved = query.store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        result = query.get(article_id)
        assert result is not None
        assert result["title"] == "Python Programming"

    def test_mark_read(self, query, sample_articles):
        query.store.store(sample_articles[0])

        article_hash = sample_articles[0].content_hash
        retrieved = query.store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        result = query.mark_read(article_id)
        assert result is True

        updated = query.get(article_id)
        assert updated["status"] == "read"

    def test_unread_count(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        assert query.unread_count() == 3

        # Mark one as read
        article_hash = sample_articles[0].content_hash
        retrieved = query.store.get_by_hash(article_hash)
        query.mark_read(retrieved["id"])

        assert query.unread_count() == 2

    def test_stats(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        stats = query.stats()
        assert stats["total"] == 3
        assert stats["unread"] == 3

    def test_filter_by_status(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        # Mark one as read
        article_hash = sample_articles[0].content_hash
        retrieved = query.store.get_by_hash(article_hash)
        query.mark_read(retrieved["id"])

        criteria = ArticleFilter(status="read")
        results = query.filter(criteria)
        assert len(results) == 1
        assert results[0]["status"] == "read"

    def test_filter_by_source(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        criteria = ArticleFilter(source_id="source-a")
        results = query.filter(criteria)
        assert len(results) == 2
        assert all(r["source_id"] == "source-a" for r in results)

    def test_filter_by_tier(self, query, sample_articles):
        query.store.store(sample_articles[0], tier=SourceTier.P0)
        query.store.store(sample_articles[1], tier=SourceTier.P1)

        criteria = ArticleFilter(tier=SourceTier.P0)
        results = query.filter(criteria)
        assert len(results) == 1
        assert results[0]["tier"] == "p0"

    def test_filter_with_search(self, query, sample_articles):
        for article in sample_articles:
            query.store.store(article)

        criteria = ArticleFilter(search_query="Python")
        results = query.filter(criteria)
        assert len(results) >= 1
        assert any("Python" in r["title"] for r in results)


class TestArticleFilter:
    def test_filter_creation(self):
        criteria = ArticleFilter(
            status="unread",
            source_id="test-source",
            tier=SourceTier.P1,
            search_query="python",
        )
        assert criteria.status == "unread"
        assert criteria.source_id == "test-source"
        assert criteria.tier == SourceTier.P1
        assert criteria.search_query == "python"

    def test_filter_defaults(self):
        criteria = ArticleFilter()
        assert criteria.status is None
        assert criteria.source_id is None
        assert criteria.tier is None
