"""Signal fetchers — RSS, JSON API, and Webpage content fetching."""

import abc
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from src.signals.sources import SourceConfig


@dataclass
class FetchedArticle:
    """Article fetched from a source."""
    url: str
    title: str
    content: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    summary: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def content_hash(self) -> str:
        """Generate hash for deduplication."""
        content = f"{self.title}:{self.content[:500]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class BaseFetcher(abc.ABC):
    """Base class for content fetchers."""

    def __init__(self, config: SourceConfig):
        self.config = config
        self.timeout = config.timeout

    @abc.abstractmethod
    async def fetch(self) -> List[FetchedArticle]:
        """Fetch articles from source."""
        pass

    def _should_include(self, text: str) -> bool:
        """Check if article matches source keywords."""
        if not self.config.keywords:
            return True
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.config.keywords)


class RSSFetcher(BaseFetcher):
    """Fetch articles from RSS/Atom feeds."""

    async def fetch(self) -> List[FetchedArticle]:
        """Fetch and parse RSS feed."""
        headers = self.config.headers or {}
        headers.setdefault("User-Agent", "MeowAI-Signals/1.0")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.config.url, headers=headers)
            response.raise_for_status()

        # feedparser works with bytes
        feed = feedparser.parse(response.content)
        articles = []

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))

            # Check keywords
            if not self._should_include(f"{title} {summary}"):
                continue

            # Parse published date
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (TypeError, ValueError):
                    pass
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                try:
                    published = datetime(*entry.updated_parsed[:6])
                except (TypeError, ValueError):
                    pass

            # Get URL
            url = entry.get("link", "")
            if url and not url.startswith(("http://", "https://")):
                url = urljoin(self.config.url, url)

            article = FetchedArticle(
                url=url,
                title=title,
                content=summary,  # Full content often not in RSS
                published_at=published,
                author=entry.get("author"),
                summary=summary,
                source_id=self.config.source_id,
                metadata={
                    "feed_title": feed.feed.get("title", ""),
                    "feed_url": self.config.url,
                    "entry_id": entry.get("id", ""),
                }
            )
            articles.append(article)

        return articles


class JSONFetcher(BaseFetcher):
    """Fetch articles from JSON API endpoints."""

    async def fetch(self) -> List[FetchedArticle]:
        """Fetch and parse JSON API response."""
        headers = self.config.headers or {}
        headers.setdefault("User-Agent", "MeowAI-Signals/1.0")
        headers.setdefault("Accept", "application/json")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.config.url, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Parse based on selectors config
        articles = []
        items = self._extract_items(data)

        for item in items:
            article = self._parse_item(item)
            if article and self._should_include(f"{article.title} {article.content}"):
                articles.append(article)

        return articles

    def _extract_items(self, data: Any) -> List[Dict]:
        """Extract list of items from JSON response."""
        selectors = self.config.selectors or {}
        items_path = selectors.get("items", "")

        if not items_path:
            # Assume data is a list
            return data if isinstance(data, list) else [data]

        # Navigate path like "data.articles"
        current = data
        for key in items_path.split("."):
            if isinstance(current, dict):
                current = current.get(key, [])
            else:
                return []

        return current if isinstance(current, list) else [current]

    def _parse_item(self, item: Dict) -> Optional[FetchedArticle]:
        """Parse a single JSON item into FetchedArticle."""
        selectors = self.config.selectors or {}

        title_field = selectors.get("title", "title")
        url_field = selectors.get("url", "url")
        content_field = selectors.get("content", "content")
        date_field = selectors.get("date", "published_at")
        author_field = selectors.get("author", "author")

        title = self._get_nested_value(item, title_field)
        if not title:
            return None

        url = self._get_nested_value(item, url_field, "")
        if url and not url.startswith(("http://", "https://")):
            url = urljoin(self.config.url, url)

        content = self._get_nested_value(item, content_field, "")
        author = self._get_nested_value(item, author_field)

        # Parse date
        published = None
        date_str = self._get_nested_value(item, date_field)
        if date_str:
            published = self._parse_date(str(date_str))

        return FetchedArticle(
            url=url or self.config.url,
            title=str(title),
            content=str(content),
            published_at=published,
            author=str(author) if author else None,
            summary=str(content)[:500] if content else None,
            source_id=self.config.source_id,
            metadata={"raw": item}
        )

    def _get_nested_value(self, data: Dict, path: str, default: Any = None) -> Any:
        """Get value from nested dict by dot-notation path."""
        if not path:
            return default

        current = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key, default)
            else:
                return default
        return current

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats."""
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %Z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str[:len(fmt) + 10], fmt)
            except ValueError:
                continue

        # Try ISO format with timezone
        try:
            # Remove timezone info for simplicity
            clean = re.sub(r'[+-]\d{2}:\d{2}$', '', date_str)
            clean = re.sub(r'Z$', '', clean)
            if '.' in clean:
                clean = clean.split('.')[0]
            return datetime.strptime(clean, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

        return None


class WebpageFetcher(BaseFetcher):
    """Fetch articles by scraping web pages."""

    async def fetch(self) -> List[FetchedArticle]:
        """Fetch and parse webpage."""
        headers = self.config.headers or {}
        headers.setdefault("User-Agent", "MeowAI-Signals/1.0")

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(self.config.url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        selectors = self.config.selectors or {}

        # Get article containers
        container_selector = selectors.get("container", "article")
        containers = soup.select(container_selector)

        if not containers:
            # Fallback: try common article patterns
            containers = soup.find_all(['article', 'div.post', 'div.entry'])

        if not containers:
            # Single page mode - treat whole page as one article
            return [self._parse_single_page(soup)]

        articles = []
        for container in containers:
            article = self._parse_container(container, soup)
            if article and self._should_include(f"{article.title} {article.content}"):
                articles.append(article)

        return articles

    def _parse_container(self, container: BeautifulSoup, soup: BeautifulSoup) -> Optional[FetchedArticle]:
        """Parse a single article container."""
        selectors = self.config.selectors or {}

        # Extract title
        title_selector = selectors.get("title", "h1, h2, .title")
        title_elem = container.select_one(title_selector)
        if not title_elem:
            title_elem = container.find(['h1', 'h2', 'h3'])

        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        # Extract content
        content_selector = selectors.get("content", ".content, .entry-content, p")
        content_elems = container.select(content_selector)

        if not content_elems:
            content_elems = container.find_all('p')

        content = '\n\n'.join(p.get_text(strip=True) for p in content_elems if p.get_text(strip=True))

        # Extract URL
        url = self.config.url
        link_elem = container.select_one(selectors.get("link", "a"))
        if link_elem and link_elem.get("href"):
            href = link_elem["href"]
            url = urljoin(self.config.url, href)

        # Extract date
        published = None
        date_selector = selectors.get("date", "time, .date, .published")
        date_elem = container.select_one(date_selector)
        if date_elem:
            date_str = date_elem.get("datetime") or date_elem.get_text(strip=True)
            published = self._parse_date(date_str)

        # Extract author
        author = None
        author_selector = selectors.get("author", ".author, [rel='author']")
        author_elem = container.select_one(author_selector)
        if author_elem:
            author = author_elem.get_text(strip=True)

        return FetchedArticle(
            url=url,
            title=title,
            content=content,
            published_at=published,
            author=author,
            summary=content[:500] if content else None,
            source_id=self.config.source_id,
            metadata={"fetched_from": self.config.url}
        )

    def _parse_single_page(self, soup: BeautifulSoup) -> FetchedArticle:
        """Parse entire page as single article."""
        # Extract title
        title_elem = soup.find('title') or soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "Untitled"

        # Extract main content
        content = ""
        main = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main:
            paragraphs = main.find_all('p')
            content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs)

        if not content:
            # Fallback: all paragraphs
            paragraphs = soup.find_all('p')
            content = '\n\n'.join(p.get_text(strip=True) for p in paragraphs[:20])

        return FetchedArticle(
            url=self.config.url,
            title=title,
            content=content,
            source_id=self.config.source_id,
            summary=content[:500] if content else None,
            metadata={"fetched_from": self.config.url, "mode": "single_page"}
        )

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string."""
        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%B %d, %Y",
            "%d %B %Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        return None
