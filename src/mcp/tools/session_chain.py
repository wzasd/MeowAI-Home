"""MCP Session Chain tools — for accessing session history and digests."""
from typing import Any, Dict, List, Optional


def list_session_chain(
    thread_id: str,
    manager: Any,
) -> Dict[str, Any]:
    """List all sessions in a thread's chain.

    Args:
        thread_id: Thread ID
        manager: SessionManager instance

    Returns:
        Dict with sessions list ordered by creation time
    """
    sessions = []

    if hasattr(manager, "list_by_thread"):
        records = manager.list_by_thread(thread_id)
        for record in records:
            sessions.append({
                "session_id": record.session_id,
                "cat_id": record.cat_id,
                "status": record.status.value if hasattr(record.status, "value") else str(record.status),
                "created_at": record.created_at,
            })

    return {
        "thread_id": thread_id,
        "sessions": sessions,
        "count": len(sessions),
    }


def read_session_events(
    session_id: str,
    view: str = "raw",  # raw, chat, handoff
    limit: Optional[int] = None,
    transcript: Any = None,
) -> Dict[str, Any]:
    """Read events from a sealed session transcript.

    Args:
        session_id: Session ID
        view: View format (raw, chat, handoff)
        limit: Max events to return
        transcript: TranscriptWriter instance

    Returns:
        Dict with events in requested format
    """
    if not transcript:
        return {"events": [], "format": view}

    events = []
    if hasattr(transcript, "read"):
        events = transcript.read(session_id, limit=limit)

    if view == "raw":
        return {
            "session_id": session_id,
            "events": events,
            "format": "raw",
            "count": len(events),
        }

    elif view == "chat":
        # Format as chat messages
        chat_messages = []
        for event in events:
            chat_messages.append({
                "role": event.get("role", "unknown"),
                "content": event.get("content", ""),
            })
        return {
            "session_id": session_id,
            "events": chat_messages,
            "format": "chat",
            "count": len(chat_messages),
        }

    elif view == "handoff":
        # Format for handoff (just key points)
        return {
            "session_id": session_id,
            "events": events,
            "format": "handoff",
            "note": "Use read_session_digest() for structured summary",
        }

    return {"events": events, "format": view}


def read_session_digest(
    session_id: str,
    transcript: Any,
) -> Optional[Dict[str, Any]]:
    """Read extractive digest from a session.

    Args:
        session_id: Session ID
        transcript: TranscriptWriter instance

    Returns:
        Digest dict with tool_names, file_paths, errors, counts
    """
    if not transcript:
        return None

    if hasattr(transcript, "digest"):
        return transcript.digest(session_id)

    return None


def read_invocation_detail(
    invocation_id: str,
    tracker: Any,
) -> Optional[Dict[str, Any]]:
    """Read detailed info about a specific invocation.

    Args:
        invocation_id: Invocation ID
        tracker: InvocationTracker instance

    Returns:
        Dict with invocation details or None
    """
    if not tracker:
        return None

    if hasattr(tracker, "get"):
        record = tracker.get(invocation_id)
        if record:
            return {
                "invocation_id": invocation_id,
                "cat_id": getattr(record, "cat_id", None),
                "thread_id": getattr(record, "thread_id", None),
                "status": getattr(record, "status", "unknown"),
                "started_at": getattr(record, "started_at", None),
                "completed_at": getattr(record, "completed_at", None),
                "duration_ms": getattr(record, "duration_ms", None),
            }

    return None


__all__ = [
    "list_session_chain",
    "read_session_events",
    "read_session_digest",
    "read_invocation_detail",
]