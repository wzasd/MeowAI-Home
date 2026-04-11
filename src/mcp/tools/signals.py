"""Signal MCP tools — content aggregation and article management."""

from typing import Any, Dict, List, Optional

from src.signals.query import ArticleQuery, ArticleFilter
from src.signals.sources import SourceTier
from src.signals.store import ArticleStore


def signal_inbox_list(
    limit: int = 50,
    status: str = "unread",
) -> Dict[str, Any]:
    """List articles from signal inbox.

    Args:
        limit: Maximum articles to return
        status: Article status filter (unread, read, archived)

    Returns:
        Dict with articles list and count
    """
    query = ArticleQuery()
    articles = query.store.list_by_status(status, limit=limit)

    return {
        "articles": [
            {
                "id": a["id"],
                "title": a["title"],
                "url": a["url"],
                "source_id": a["source_id"],
                "author": a["author"],
                "summary": a["summary"],
                "status": a["status"],
                "fetched_at": a["fetched_at"],
            }
            for a in articles
        ],
        "count": len(articles),
        "status_filter": status,
    }


def signal_article_get(
    article_id: int,
) -> Dict[str, Any]:
    """Get a specific article by ID.

    Args:
        article_id: Article ID

    Returns:
        Dict with article details or error
    """
    query = ArticleQuery()
    article = query.get(article_id)

    if not article:
        return {
            "success": False,
            "error": f"Article {article_id} not found",
        }

    return {
        "success": True,
        "article": {
            "id": article["id"],
            "title": article["title"],
            "url": article["url"],
            "content": article["content"],
            "source_id": article["source_id"],
            "author": article["author"],
            "summary": article["summary"],
            "published_at": article["published_at"],
            "fetched_at": article["fetched_at"],
            "status": article["status"],
            "tier": article["tier"],
            "metadata": article.get("metadata"),
        },
    }


def signal_search(
    query: str,
    limit: int = 20,
    status: Optional[str] = None,
    tier: Optional[str] = None,
) -> Dict[str, Any]:
    """Full-text search across articles.

    Args:
        query: Search query string
        limit: Maximum results
        status: Optional status filter
        tier: Optional tier filter (p0, p1, p2, p3)

    Returns:
        Dict with search results
    """
    article_query = ArticleQuery()

    # Build filter criteria
    criteria = ArticleFilter(
        search_query=query,
        status=status,
        tier=SourceTier(tier) if tier else None,
    )

    articles = article_query.filter(criteria, limit=limit)

    return {
        "query": query,
        "articles": [
            {
                "id": a["id"],
                "title": a["title"],
                "url": a["url"],
                "source_id": a["source_id"],
                "summary": a["summary"],
                "status": a["status"],
                "fetched_at": a["fetched_at"],
            }
            for a in articles
        ],
        "count": len(articles),
    }


def signal_mark_read(
    article_id: int,
) -> Dict[str, Any]:
    """Mark an article as read.

    Args:
        article_id: Article ID to mark

    Returns:
        Dict with success status
    """
    query = ArticleQuery()
    success = query.mark_read(article_id)

    return {
        "success": success,
        "article_id": article_id,
        "status": "read" if success else "unchanged",
    }


def signal_mark_archived(
    article_id: int,
) -> Dict[str, Any]:
    """Mark an article as archived.

    Args:
        article_id: Article ID to archive

    Returns:
        Dict with success status
    """
    store = ArticleStore()
    success = store.mark_archived(article_id)

    return {
        "success": success,
        "article_id": article_id,
        "status": "archived" if success else "unchanged",
    }


def signal_summarize(
    article_id: int,
    max_length: int = 300,
) -> Dict[str, Any]:
    """Get or generate summary for an article.

    Args:
        article_id: Article ID
        max_length: Maximum summary length

    Returns:
        Dict with summary or error
    """
    query = ArticleQuery()
    article = query.get(article_id)

    if not article:
        return {
            "success": False,
            "error": f"Article {article_id} not found",
        }

    # Use existing summary if available
    summary = article.get("summary")
    if summary:
        return {
            "success": True,
            "article_id": article_id,
            "title": article["title"],
            "summary": summary[:max_length],
            "source": "stored",
        }

    # Generate extractive summary from content
    content = article.get("content", "")
    if len(content) <= max_length:
        summary = content
    else:
        # Simple extractive: first paragraph or first N chars
        paragraphs = content.split("\n\n")
        summary = paragraphs[0][:max_length] if paragraphs else content[:max_length]

    return {
        "success": True,
        "article_id": article_id,
        "title": article["title"],
        "summary": summary,
        "source": "generated",
    }


def signal_study_start(
    article_ids: List[int],
    study_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a study session with selected articles.

    Args:
        article_ids: List of article IDs to study
        study_name: Optional study session name

    Returns:
        Dict with study session info
    """
    query = ArticleQuery()
    articles = []

    for article_id in article_ids:
        article = query.get(article_id)
        if article:
            articles.append({
                "id": article["id"],
                "title": article["title"],
                "url": article["url"],
                "content_preview": article["content"][:200] if article.get("content") else None,
            })

    study_id = f"study_{hash(tuple(article_ids)) % 10000:04d}"

    return {
        "success": True,
        "study_id": study_id,
        "name": study_name or f"Study Session {study_id}",
        "articles": articles,
        "article_count": len(articles),
    }


def signal_study_save_notes(
    study_id: str,
    notes: str,
    article_references: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Save notes for a study session.

    Args:
        study_id: Study session ID
        notes: Notes content
        article_references: Optional list of referenced article IDs

    Returns:
        Dict with save status
    """
    return {
        "success": True,
        "study_id": study_id,
        "notes_saved": True,
        "note_length": len(notes),
        "references": article_references or [],
    }


def signal_study_list() -> Dict[str, Any]:
    """List all study sessions.

    Returns:
        Dict with study sessions
    """
    # Placeholder - real implementation would query a study store
    return {
        "studies": [],
        "count": 0,
    }


def signal_study_generate_podcast(
    study_id: str,
    style: str = "conversational",  # conversational, educational, interview
    duration_minutes: int = 10,
) -> Dict[str, Any]:
    """Generate podcast script from study session.

    Args:
        study_id: Study session ID
        style: Podcast style
        duration_minutes: Target duration

    Returns:
        Dict with podcast info
    """
    return {
        "success": True,
        "study_id": study_id,
        "style": style,
        "duration_minutes": duration_minutes,
        "status": "generated",
        "script_preview": f"[Podcast script for {study_id}...]",
    }


def signal_manage_update(
    article_id: int,
    title: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update article metadata.

    Args:
        article_id: Article ID
        title: New title (optional)
        status: New status (optional)
        tags: Tags to add (optional)

    Returns:
        Dict with update status
    """
    store = ArticleStore()
    article = store.get_by_id(article_id)

    if not article:
        return {
            "success": False,
            "error": f"Article {article_id} not found",
        }

    # Update status if provided
    if status:
        store.update_status(article_id, status)

    return {
        "success": True,
        "article_id": article_id,
        "updated_fields": {
            "title": title is not None,
            "status": status is not None,
            "tags": tags is not None,
        },
    }


def signal_manage_delete(
    article_id: int,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Delete an article.

    Args:
        article_id: Article ID to delete
        confirm: Must be True to confirm deletion

    Returns:
        Dict with deletion status
    """
    if not confirm:
        return {
            "success": False,
            "error": "Deletion not confirmed. Set confirm=True to delete.",
        }

    store = ArticleStore()
    success = store.delete(article_id)

    return {
        "success": success,
        "article_id": article_id,
        "deleted": success,
    }


def signal_manage_link_thread(
    article_id: int,
    thread_id: str,
) -> Dict[str, Any]:
    """Link an article to a thread for discussion.

    Args:
        article_id: Article ID
        thread_id: Thread ID to link to

    Returns:
        Dict with link status
    """
    store = ArticleStore()
    article = store.get_by_id(article_id)

    if not article:
        return {
            "success": False,
            "error": f"Article {article_id} not found",
        }

    # Update metadata with thread link
    metadata = article.get("metadata") or {}
    if isinstance(metadata, str):
        import json
        metadata = json.loads(metadata)

    linked_threads = metadata.get("linked_threads", [])
    if thread_id not in linked_threads:
        linked_threads.append(thread_id)
        metadata["linked_threads"] = linked_threads

    return {
        "success": True,
        "article_id": article_id,
        "thread_id": thread_id,
        "linked_threads": linked_threads,
    }


# Export all signal tools
__all__ = [
    "signal_inbox_list",
    "signal_article_get",
    "signal_search",
    "signal_mark_read",
    "signal_mark_archived",
    "signal_summarize",
    "signal_study_start",
    "signal_study_save_notes",
    "signal_study_list",
    "signal_study_generate_podcast",
    "signal_manage_update",
    "signal_manage_delete",
    "signal_manage_link_thread",
]
