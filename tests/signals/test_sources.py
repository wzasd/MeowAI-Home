"""Tests for SignalSource and SourceConfig."""
import pytest

from src.signals.sources import FetchMethod, SignalSource, SourceConfig, SourceTier


class TestSourceConfig:
    def test_source_config_creation(self):
        config = SourceConfig(
            source_id="hacker-news",
            name="Hacker News",
            url="https://news.ycombinator.com/rss",
            method=FetchMethod.RSS,
            tier=SourceTier.P1,
            schedule="hourly",
            keywords=["python", "ai"],
        )
        assert config.source_id == "hacker-news"
        assert config.name == "Hacker News"
        assert config.tier == SourceTier.P1
        assert config.enabled is True

    def test_default_values(self):
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com",
            method=FetchMethod.JSON,
        )
        assert config.tier == SourceTier.P2
        assert config.schedule == "daily"
        assert config.keywords == []
        assert config.timeout == 30


class TestSignalSource:
    def test_register_source(self):
        registry = SignalSource()
        config = SourceConfig(
            source_id="test",
            name="Test Source",
            url="https://example.com/rss",
            method=FetchMethod.RSS,
        )
        registry.register(config)

        retrieved = registry.get("test")
        assert retrieved is not None
        assert retrieved.name == "Test Source"

    def test_unregister_source(self):
        registry = SignalSource()
        config = SourceConfig(
            source_id="test",
            name="Test",
            url="https://example.com",
            method=FetchMethod.RSS,
        )
        registry.register(config)
        assert registry.unregister("test") is True
        assert registry.get("test") is None
        assert registry.unregister("nonexistent") is False

    def test_list_all(self):
        registry = SignalSource()
        registry.register(SourceConfig("s1", "S1", "https://a.com", FetchMethod.RSS))
        registry.register(SourceConfig("s2", "S2", "https://b.com", FetchMethod.JSON))

        all_sources = registry.list_all()
        assert len(all_sources) == 2

    def test_list_enabled(self):
        registry = SignalSource()
        registry.register(SourceConfig("s1", "S1", "https://a.com", FetchMethod.RSS, enabled=True))
        registry.register(SourceConfig("s2", "S2", "https://b.com", FetchMethod.JSON, enabled=False))

        enabled = registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].source_id == "s1"

    def test_list_by_tier(self):
        registry = SignalSource()
        registry.register(SourceConfig("s1", "S1", "https://a.com", FetchMethod.RSS, tier=SourceTier.P0))
        registry.register(SourceConfig("s2", "S2", "https://b.com", FetchMethod.RSS, tier=SourceTier.P1))
        registry.register(SourceConfig("s3", "S3", "https://c.com", FetchMethod.RSS, tier=SourceTier.P0))

        p0_sources = registry.list_by_tier(SourceTier.P0)
        assert len(p0_sources) == 2
        assert all(s.tier == SourceTier.P0 for s in p0_sources)

    def test_list_by_method(self):
        registry = SignalSource()
        registry.register(SourceConfig("s1", "S1", "https://a.com", FetchMethod.RSS))
        registry.register(SourceConfig("s2", "S2", "https://b.com", FetchMethod.JSON))

        rss_sources = registry.list_by_method(FetchMethod.RSS)
        assert len(rss_sources) == 1
        assert rss_sources[0].source_id == "s1"

    def test_update_source(self):
        registry = SignalSource()
        registry.register(SourceConfig("s1", "S1", "https://a.com", FetchMethod.RSS, enabled=True))

        result = registry.update("s1", enabled=False, timeout=60)
        assert result is True

        source = registry.get("s1")
        assert source.enabled is False
        assert source.timeout == 60

    def test_update_nonexistent(self):
        registry = SignalSource()
        assert registry.update("nonexistent", enabled=False) is False

    def test_yaml_export_import(self):
        registry = SignalSource()
        registry.register(SourceConfig(
            source_id="test",
            name="Test Source",
            url="https://example.com/rss",
            method=FetchMethod.RSS,
            tier=SourceTier.P1,
            keywords=["python"],
        ))

        yaml_str = registry.to_yaml()
        assert "test" in yaml_str
        assert "Test Source" in yaml_str
        assert "python" in yaml_str

        # Import into new registry
        new_registry = SignalSource()
        new_registry.from_yaml(yaml_str)

        source = new_registry.get("test")
        assert source is not None
        assert source.name == "Test Source"
        assert source.tier == SourceTier.P1
        assert "python" in source.keywords
