"""Signal API routes — articles and sources management."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.signals.store import ArticleStore
from src.signals.sources import SignalSource, SourceConfig, SourceTier, FetchMethod

router = APIRouter(prefix="/signals", tags=["signals"])

# Global instances (initialized on first use)
_article_store: Optional[ArticleStore] = None
_signal_source: Optional[SignalSource] = None


def get_article_store() -> ArticleStore:
    """Get or create article store singleton."""
    global _article_store
    if _article_store is None:
        _article_store = ArticleStore()
    return _article_store


def get_signal_source() -> SignalSource:
    """Get or create signal source singleton."""
    global _signal_source
    if _signal_source is None:
        _signal_source = SignalSource()
        # Load default sources if empty
        _load_default_sources(_signal_source)
    return _signal_source


def _load_default_sources(source: SignalSource) -> None:
    """Load default signal sources."""
    defaults = [
        SourceConfig(
            source_id="openai-blog",
            name="OpenAI Blog",
            url="https://openai.com/blog/rss.xml",
            method=FetchMethod.RSS,
            tier=SourceTier.P1,
            schedule="0 */4 * * *",
            enabled=True,
        ),
        SourceConfig(
            source_id="anthropic-blog",
            name="Anthropic Blog",
            url="https://www.anthropic.com/blog/rss.xml",
            method=FetchMethod.RSS,
            tier=SourceTier.P1,
            schedule="0 */4 * * *",
            enabled=True,
        ),
        SourceConfig(
            source_id="react-blog",
            name="React Blog",
            url="https://react.dev/rss.xml",
            method=FetchMethod.RSS,
            tier=SourceTier.P2,
            schedule="0 */8 * * *",
            enabled=False,
        ),
        SourceConfig(
            source_id="hackernews",
            name="Hacker News",
            url="https://hnrss.org/frontpage",
            method=FetchMethod.RSS,
            tier=SourceTier.P2,
            schedule="*/30 * * * *",
            enabled=True,
        ),
    ]
    for config in defaults:
        source.register(config)


# === Pydantic Models ===

class ArticleTierStr(str):
    """Article tier as string for API."""
    pass


class ArticleStatusStr(str):
    """Article status as string for API."""
    pass


class SignalArticle(BaseModel):
    """Signal article response model."""
    id: str
    title: str
    url: str
    source: str
    tier: str = Field(..., description="S, A, B, or C")
    status: str = Field(..., description="unread, reading, read, or starred")
    summary: str
    keywords: List[str] = Field(default_factory=list)
    publishedAt: str
    readTime: Optional[int] = None

    class Config:
        populate_by_name = True


class SignalSourceResp(BaseModel):
    """Signal source response model."""
    id: str
    name: str
    tier: str
    fetchMethod: str
    schedule: str
    lastFetchedAt: Optional[str] = None
    enabled: bool


class ArticlesResponse(BaseModel):
    """Articles list response."""
    articles: List[SignalArticle]
    total: int


class SourcesResponse(BaseModel):
    """Sources list response."""
    sources: List[SignalSourceResp]


class UpdateStatusRequest(BaseModel):
    """Update article status request."""
    status: str = Field(..., description="unread, reading, read, or starred")


class SearchResponse(BaseModel):
    """Search results response."""
    articles: List[SignalArticle]
    query: str


# === Helper Functions ===

def _map_tier(tier_value: str) -> str:
    """Map source tier to article tier."""
    tier_map = {
        "p0": "S",
        "p1": "S",
        "p2": "A",
        "p3": "B",
    }
    return tier_map.get(tier_value.lower(), "C")


def _db_article_to_response(db_article: Dict[str, Any]) -> SignalArticle:
    """Convert database article to API response."""
    # Extract keywords from metadata if available
    metadata = {}
    if db_article.get("metadata"):
        import json
        try:
            metadata = json.loads(db_article["metadata"])
        except json.JSONDecodeError:
            pass

    keywords = metadata.get("keywords", [])
    if not keywords and db_article.get("source_id"):
        # Default keywords based on source
        keywords = []

    # Calculate read time (rough estimate: 200 words per minute)
    content = db_article.get("content", "")
    word_count = len(content.split())
    read_time = max(1, word_count // 200)

    # Format published date
    published_at = db_article.get("published_at") or db_article.get("fetched_at")
    if published_at:
        # Ensure ISO format
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            published_at = dt.isoformat()
        except (ValueError, AttributeError):
            published_at = datetime.utcnow().isoformat()
    else:
        published_at = datetime.utcnow().isoformat()

    return SignalArticle(
        id=str(db_article.get("id", "")),
        title=db_article.get("title", "Untitled"),
        url=db_article.get("url", ""),
        source=db_article.get("source_id", "Unknown"),
        tier=_map_tier(db_article.get("tier", "p3")),
        status=db_article.get("status", "unread"),
        summary=db_article.get("summary", db_article.get("content", "")[:200]),
        keywords=keywords,
        publishedAt=published_at,
        readTime=read_time,
    )


def _source_config_to_response(config: SourceConfig) -> SignalSourceResp:
    """Convert source config to API response."""
    tier_map = {
        "p0": "S",
        "p1": "S",
        "p2": "A",
        "p3": "B",
    }

    return SignalSourceResp(
        id=config.source_id,
        name=config.name,
        tier=tier_map.get(config.tier.value, "C"),
        fetchMethod=config.method.value,
        schedule=config.schedule,
        lastFetchedAt=None,  # Would need to track this separately
        enabled=config.enabled,
    )


# === API Endpoints ===

@router.get("/articles", response_model=ArticlesResponse)
async def list_articles(
    status: Optional[str] = Query(None, description="Filter by status: unread, read, starred, archived"),
    tier: Optional[str] = Query(None, description="Filter by tier: S, A, B, C"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """List signal articles with optional filtering."""
    store = get_article_store()

    if status:
        articles = store.list_by_status(status, limit=limit)
    elif tier:
        # Map tier back to source tier
        tier_map = {"S": SourceTier.P1, "A": SourceTier.P2, "B": SourceTier.P3, "C": SourceTier.P3}
        source_tier = tier_map.get(tier.upper(), SourceTier.P3)
        articles = store.list_by_tier(source_tier, limit=limit)
    else:
        articles = store.list_recent(limit=limit, offset=offset)

    return {
        "articles": [_db_article_to_response(a) for a in articles],
        "total": len(articles),
    }


@router.get("/articles/search", response_model=SearchResponse)
async def search_articles(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """Full-text search articles."""
    store = get_article_store()
    articles = store.search(q, limit=limit)

    return {
        "articles": [_db_article_to_response(a) for a in articles],
        "query": q,
    }


@router.get("/articles/{article_id}", response_model=SignalArticle)
async def get_article(article_id: str) -> SignalArticle:
    """Get a single article by ID."""
    store = get_article_store()

    try:
        article_id_int = int(article_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    article = store.get_by_id(article_id_int)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return _db_article_to_response(article)


@router.patch("/articles/{article_id}/status")
async def update_article_status(article_id: str, request: UpdateStatusRequest) -> Dict[str, Any]:
    """Update article status (unread, read, starred, archived)."""
    store = get_article_store()

    try:
        article_id_int = int(article_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    success = store.update_status(article_id_int, request.status)
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"success": True, "id": article_id, "status": request.status}


@router.post("/articles/{article_id}/star")
async def star_article(article_id: str) -> Dict[str, Any]:
    """Star an article."""
    store = get_article_store()

    try:
        article_id_int = int(article_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid article ID")

    success = store.update_status(article_id_int, "starred")
    if not success:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"success": True, "id": article_id, "starred": True}


@router.get("/sources", response_model=SourcesResponse)
async def list_sources() -> Dict[str, Any]:
    """List all signal sources."""
    source = get_signal_source()
    configs = source.list_all()

    return {
        "sources": [_source_config_to_response(c) for c in configs],
    }


@router.post("/sources/{source_id}/refresh")
async def refresh_source(source_id: str) -> Dict[str, Any]:
    """Trigger a refresh of a source."""
    source = get_signal_source()
    config = source.get(source_id)

    if not config:
        raise HTTPException(status_code=404, detail="Source not found")

    # In a real implementation, this would trigger an async fetch job
    return {"success": True, "source_id": source_id, "message": "Refresh scheduled"}


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Get signal system statistics."""
    store = get_article_store()
    source = get_signal_source()

    stats = store.get_stats()

    return {
        "articles": stats,
        "sources": {
            "total": len(source.list_all()),
            "enabled": len(source.list_enabled()),
        },
    }
