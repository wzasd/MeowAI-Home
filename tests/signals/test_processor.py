"""Tests for SourceProcessor."""
import pytest

from src.signals.fetchers import FetchedArticle
from src.signals.processor import SourceProcessor
from src.signals.sources import FetchMethod, SignalSource, SourceConfig, SourceTier
from src.signals.store import ArticleStore


@pytest.fixture
def processor(tmp_path):
    db_path = str(tmp_path / "test_processor.db")
    registry = SignalSource()
    store = ArticleStore(db_path=db_path)
    return SourceProcessor(source_registry=registry, article_store=store)


@pytest.fixture
def sample_config():
    return SourceConfig(
        source_id="test-source",
        name="Test Source",
        url="https://example.com/rss",
        method=FetchMethod.RSS,
        tier=SourceTier.P1,
        enabled=True,
    )


class TestSourceProcessor:
    def test_get_fetcher_rss(self, processor, sample_config):
        fetcher = processor.get_fetcher(sample_config)
        from src.signals.fetchers import RSSFetcher
        assert isinstance(fetcher, RSSFetcher)

    def test_get_fetcher_json(self, processor):
        config = SourceConfig(
            source_id="json-source",
            name="JSON Source",
            url="https://example.com/api",
            method=FetchMethod.JSON,
        )
        fetcher = processor.get_fetcher(config)
        from src.signals.fetchers import JSONFetcher
        assert isinstance(fetcher, JSONFetcher)

    def test_get_fetcher_webpage(self, processor):
        config = SourceConfig(
            source_id="web-source",
            name="Web Source",
            url="https://example.com/news",
            method=FetchMethod.WEBPAGE,
        )
        fetcher = processor.get_fetcher(config)
        from src.signals.fetchers import WebpageFetcher
        assert isinstance(fetcher, WebpageFetcher)

    def test_get_fetcher_unknown(self, processor):
        config = SourceConfig(
            source_id="unknown",
            name="Unknown",
            url="https://example.com",
            method="unknown",  # type: ignore
        )
        with pytest.raises(ValueError):
            processor.get_fetcher(config)

    def test_select_sources_for_run(self, processor):
        processor.sources.register(SourceConfig(
            source_id="s1",
            name="S1",
            url="https://a.com",
            method=FetchMethod.RSS,
            tier=SourceTier.P0,
            enabled=True,
        ))
        processor.sources.register(SourceConfig(
            source_id="s2",
            name="S2",
            url="https://b.com",
            method=FetchMethod.RSS,
            tier=SourceTier.P1,
            enabled=True,
        ))
        processor.sources.register(SourceConfig(
            source_id="s3",
            name="S3",
            url="https://c.com",
            method=FetchMethod.RSS,
            tier=SourceTier.P0,
            enabled=False,
        ))

        # All enabled
        all_enabled = processor.select_sources_for_run()
        assert len(all_enabled) == 2

        # By tier
        p0_only = processor.select_sources_for_run(tier=SourceTier.P0)
        assert len(p0_only) == 1
        assert p0_only[0].source_id == "s1"

    def test_get_stats(self, processor, sample_config):
        processor.sources.register(sample_config)

        stats = processor.get_stats()
        assert stats["sources_total"] == 1
        assert stats["sources_enabled"] == 1
        assert "articles" in stats

    def test_register_notifier(self, processor):
        calls = []

        def handler(article, config):
            calls.append((article, config))

        processor.register_notifier(handler)
        assert len(processor._notification_handlers) == 1


class TestSourceProcessorDedup:
    @pytest.mark.asyncio
    async def test_dedup_articles(self, processor):
        article1 = FetchedArticle(
            url="https://example.com/1",
            title="Article 1",
            content="Content 1",
        )
        article2 = FetchedArticle(
            url="https://example.com/2",
            title="Article 2",
            content="Content 2",
        )

        # Store first article
        processor.store.store(article1)

        # Dedup should filter out existing article
        articles = [article1, article2]
        new_articles = await processor._dedup_articles(articles)

        assert len(new_articles) == 1
        assert new_articles[0].title == "Article 2"
