"""Signals module — content aggregation and signal processing."""

from src.signals.sources import SignalSource, SourceTier, SourceConfig
from src.signals.fetchers import RSSFetcher, JSONFetcher, WebpageFetcher
from src.signals.processor import SourceProcessor
from src.signals.store import ArticleStore
from src.signals.query import ArticleQuery


__all__ = [
    "SignalSource",
    "SourceTier",
    "SourceConfig",
    "RSSFetcher",
    "JSONFetcher",
    "WebpageFetcher",
    "SourceProcessor",
    "ArticleStore",
    "ArticleQuery",
]
