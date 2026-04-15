"""Tests for ArticleStore."""
import pytest

from src.signals.fetchers import FetchedArticle
from src.signals.sources import SourceTier
from src.signals.store import ArticleStore


@pytest.fixture
def store(tmp_path):
    db_path = str(tmp_path / "test_articles.db")
    return ArticleStore(db_path=db_path)


@pytest.fixture
def sample_article():
    return FetchedArticle(
        url="https://example.com/article",
        title="Test Article",
        content="This is test content for the article.",
        author="Test Author",
        summary="Test summary",
        source_id="test-source",
        metadata={"key": "value"},
    )


class TestArticleStore:
    def test_store_new_article(self, store, sample_article):
        result = store.store(sample_article)
        assert result is True  # New article

        # Duplicate should return False
        result = store.store(sample_article)
        assert result is False

    def test_get_by_hash(self, store, sample_article):
        store.store(sample_article)

        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)

        assert retrieved is not None
        assert retrieved["title"] == "Test Article"
        assert retrieved["content_hash"] == article_hash

    def test_get_by_id(self, store, sample_article):
        store.store(sample_article)

        # Get the ID
        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        # Get by ID
        by_id = store.get_by_id(article_id)
        assert by_id is not None
        assert by_id["title"] == "Test Article"

    def test_get_nonexistent(self, store):
        assert store.get_by_hash("nonexistent") is None
        assert store.get_by_id(99999) is None

    def test_list_recent(self, store, sample_article):
        store.store(sample_article)

        recent = store.list_recent(limit=10)
        assert len(recent) == 1
        assert recent[0]["title"] == "Test Article"

    def test_list_by_source(self, store):
        article1 = FetchedArticle(
            url="https://example.com/1",
            title="Article 1",
            content="Content 1",
            source_id="source-a",
        )
        article2 = FetchedArticle(
            url="https://example.com/2",
            title="Article 2",
            content="Content 2",
            source_id="source-b",
        )
        store.store(article1)
        store.store(article2)

        source_a = store.list_by_source("source-a")
        assert len(source_a) == 1
        assert source_a[0]["source_id"] == "source-a"

    def test_list_by_status(self, store, sample_article):
        store.store(sample_article)

        unread = store.list_by_status("unread")
        assert len(unread) == 1

        read = store.list_by_status("read")
        assert len(read) == 0

    def test_list_by_tier(self, store, sample_article):
        store.store(sample_article, tier=SourceTier.P0)

        p0 = store.list_by_tier(SourceTier.P0)
        assert len(p0) == 1

        p1 = store.list_by_tier(SourceTier.P1)
        assert len(p1) == 0

    def test_mark_read(self, store, sample_article):
        store.store(sample_article)

        # Get ID
        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        # Mark as read
        result = store.mark_read(article_id)
        assert result is True

        # Check status
        updated = store.get_by_id(article_id)
        assert updated["status"] == "read"

    def test_mark_archived(self, store, sample_article):
        store.store(sample_article)

        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        result = store.mark_archived(article_id)
        assert result is True

        updated = store.get_by_id(article_id)
        assert updated["status"] == "archived"

    def test_delete(self, store, sample_article):
        store.store(sample_article)

        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        result = store.delete(article_id)
        assert result is True

        assert store.get_by_id(article_id) is None

    def test_search(self, store):
        article1 = FetchedArticle(
            url="https://example.com/1",
            title="Python Programming",
            content="Learn Python programming basics.",
        )
        article2 = FetchedArticle(
            url="https://example.com/2",
            title="JavaScript Guide",
            content="JavaScript programming tutorial.",
        )
        store.store(article1)
        store.store(article2)

        # Search for Python
        results = store.search("Python")
        assert len(results) >= 1
        assert any("Python" in r["title"] for r in results)

    def test_get_existing_hashes(self, store):
        article1 = FetchedArticle(
            url="https://example.com/1",
            title="Article 1",
            content="Content 1",
        )
        store.store(article1)

        existing = store.get_existing_hashes({article1.content_hash})
        assert article1.content_hash in existing

    def test_store_many(self, store):
        articles = [
            FetchedArticle(
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                content=f"Content {i}",
            )
            for i in range(5)
        ]

        count = store.store_many(articles)
        assert count == 5

        # Second time should return 0 (all duplicates)
        count = store.store_many(articles)
        assert count == 0

    def test_get_stats(self, store, sample_article):
        store.store(sample_article, tier=SourceTier.P1)

        stats = store.get_stats()
        assert stats["total"] == 1
        assert stats["unread"] == 1
        assert stats["by_tier"]["p1"] == 1
        assert stats["by_tier"]["p0"] == 0

    def test_update_status(self, store, sample_article):
        store.store(sample_article)

        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        result = store.update_status(article_id, "read")
        assert result is True

        updated = store.get_by_id(article_id)
        assert updated["status"] == "read"

    def test_notes(self, store, sample_article):
        store.store(sample_article)

        article_hash = sample_article.content_hash
        retrieved = store.get_by_hash(article_hash)
        article_id = retrieved["id"]

        # Default notes should be empty
        assert store.get_notes(article_id) == ""

        # Save notes
        result = store.save_notes(article_id, "This is a study note.")
        assert result is True
        assert store.get_notes(article_id) == "This is a study note."

        # Update notes
        store.save_notes(article_id, "Updated note.")
        assert store.get_notes(article_id) == "Updated note."

    def test_notes_nonexistent(self, store):
        assert store.get_notes(99999) == ""
        assert store.save_notes(99999, "note") is False
