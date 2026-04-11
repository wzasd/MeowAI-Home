"""Tests for fetchers module."""
from datetime import datetime

import pytest

from src.signals.fetchers import FetchedArticle, JSONFetcher, RSSFetcher, WebpageFetcher
from src.signals.sources import FetchMethod, SourceConfig, SourceTier


class TestFetchedArticle:
    def test_article_creation(self):
        article = FetchedArticle(
            url="https://example.com/article",
            title="Test Article",
            content="This is the content",
            author="John Doe",
        )
        assert article.url == "https://example.com/article"
        assert article.title == "Test Article"
        assert article.author == "John Doe"

    def test_content_hash(self):
        article = FetchedArticle(
            url="https://example.com/article",
            title="Test Article",
            content="This is the content",
        )
        hash1 = article.content_hash

        # Same content should give same hash
        article2 = FetchedArticle(
            url="https://example.com/article",
            title="Test Article",
            content="This is the content",
        )
        assert article2.content_hash == hash1

        # Different content should give different hash
        article3 = FetchedArticle(
            url="https://example.com/article",
            title="Test Article",
            content="Different content",
        )
        assert article3.content_hash != hash1

    def test_metadata_defaults(self):
        article = FetchedArticle(
            url="https://example.com",
            title="Test",
            content="Content",
        )
        assert article.metadata == {}


class TestJSONFetcher:
    def test_parse_date(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com/api",
            method=FetchMethod.JSON,
        )
        fetcher = JSONFetcher(config)

        # ISO format
        dt = fetcher._parse_date("2024-01-15T10:30:00")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)

        # With Z
        dt = fetcher._parse_date("2024-01-15T10:30:00Z")
        assert dt == datetime(2024, 1, 15, 10, 30, 0)

        # Date only
        dt = fetcher._parse_date("2024-01-15")
        assert dt == datetime(2024, 1, 15)

        # Invalid date
        assert fetcher._parse_date("invalid") is None

    def test_get_nested_value(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com/api",
            method=FetchMethod.JSON,
        )
        fetcher = JSONFetcher(config)

        data = {"a": {"b": {"c": "value"}}}
        assert fetcher._get_nested_value(data, "a.b.c") == "value"
        assert fetcher._get_nested_value(data, "a.b") == {"c": "value"}
        assert fetcher._get_nested_value(data, "x.y", "default") == "default"

    def test_extract_items(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com/api",
            method=FetchMethod.JSON,
            selectors={"items": "data.articles"},
        )
        fetcher = JSONFetcher(config)

        data = {"data": {"articles": [{"id": 1}, {"id": 2}]}}
        items = fetcher._extract_items(data)
        assert len(items) == 2

    def test_extract_items_no_selector(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com/api",
            method=FetchMethod.JSON,
        )
        fetcher = JSONFetcher(config)

        # List input
        data = [{"id": 1}, {"id": 2}]
        items = fetcher._extract_items(data)
        assert len(items) == 2

        # Dict input (wrapped in list)
        data = {"id": 1}
        items = fetcher._extract_items(data)
        assert len(items) == 1


class TestBaseFetcher:
    def test_should_include_no_keywords(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com",
            method=FetchMethod.RSS,
            keywords=[],
        )
        fetcher = RSSFetcher(config)

        # No keywords means include all
        assert fetcher._should_include("any content") is True

    def test_should_include_with_keywords(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com",
            method=FetchMethod.RSS,
            keywords=["python", "ai"],
        )
        fetcher = RSSFetcher(config)

        assert fetcher._should_include("This is about Python") is True
        assert fetcher._should_include("AI and machine learning") is True
        assert fetcher._should_include("JavaScript tutorial") is False
