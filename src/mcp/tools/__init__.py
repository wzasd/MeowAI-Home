"""MCP tools — core tool set for cat agents."""
import uuid
import time
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.memory import MemoryService


def post_message(
    thread: Any,
    content: str,
    role: str = "assistant",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Post a message to a thread.

    Args:
        thread: Thread object with add_message method
        content: Message content
        role: Message role (user/assistant/system)
        metadata: Optional metadata dict

    Returns:
        Dict with success status and message_id
    """
    message_id = str(uuid.uuid4())[:8]

    if hasattr(thread, "add_message"):
        thread.add_message(role, content, metadata=metadata)

    return {
        "success": True,
        "message_id": message_id,
        "thread_id": getattr(thread, "id", None),
    }


def get_thread_context(
    thread: Any,
    limit: int = 20,
    include_metadata: bool = False,
) -> Dict[str, Any]:
    """Get recent messages from a thread.

    Args:
        thread: Thread object with messages attribute
        limit: Maximum number of messages to return
        include_metadata: Whether to include message metadata

    Returns:
        Dict with messages list
    """
    messages = getattr(thread, "messages", [])

    # Get most recent messages
    recent = messages[-limit:] if len(messages) > limit else messages

    result = []
    for msg in recent:
        item = {
            "role": getattr(msg, "role", msg.get("role", "unknown")),
            "content": getattr(msg, "content", msg.get("content", "")),
            "timestamp": getattr(msg, "created_at", time.time()),
        }
        if include_metadata:
            item["metadata"] = getattr(msg, "metadata", {})
        result.append(item)

    return {
        "thread_id": getattr(thread, "id", None),
        "messages": result,
        "total": len(messages),
    }


def list_threads(
    db: Any,
    filter: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List available threads.

    Args:
        db: Database connection
        filter: Optional filter string
        limit: Maximum threads to return

    Returns:
        Dict with threads list
    """
    # Mock implementation - real would query DB
    threads = []
    if hasattr(db, "execute"):
        try:
            cursor = db.execute(
                "SELECT id, title, message_count FROM threads LIMIT ?",
                (limit,)
            )
            for row in cursor.fetchall():
                thread_id, title, msg_count = row
                if filter and filter.lower() not in title.lower():
                    continue
                threads.append({
                    "id": thread_id,
                    "title": title,
                    "message_count": msg_count,
                })
        except Exception:
            pass

    return {"threads": threads}


def create_rich_block(
    block_type: str,
    content: str,
    **kwargs,
) -> Dict[str, Any]:
    """Create a rich content block.

    Args:
        block_type: Type of block (code, diff, checklist, media)
        content: Block content
        **kwargs: Type-specific options

    Returns:
        Dict representing the rich block
    """
    block = {
        "type": block_type,
        "content": content,
        "created_at": time.time(),
    }

    if block_type == "code":
        block["language"] = kwargs.get("language", "text")
        block["line_numbers"] = kwargs.get("line_numbers", False)

    elif block_type == "diff":
        block["old_path"] = kwargs.get("old_path")
        block["new_path"] = kwargs.get("new_path")
        block["syntax"] = kwargs.get("syntax")

    elif block_type == "checklist":
        block["items"] = kwargs.get("items", [])

    elif block_type == "media":
        block["media_type"] = kwargs.get("media_type")  # image, audio, video
        block["url"] = kwargs.get("url")
        block["alt"] = kwargs.get("alt")

    return block


def request_permission(
    action: str,
    reason: str,
    timeout_seconds: float = 300.0,
) -> Dict[str, Any]:
    """Request user permission for sensitive action.

    Args:
        action: Action description
        reason: Why permission is needed
        timeout_seconds: How long to wait for response

    Returns:
        Dict with granted status
    """
    # Placeholder - real implementation would use async callback
    return {
        "granted": False,
        "action": action,
        "message": f"Permission required: {action}. Reason: {reason}",
        "timeout_seconds": timeout_seconds,
    }


def update_task(
    store: Any,
    title: Optional[str] = None,
    task_id: Optional[str] = None,
    status: Optional[str] = None,  # todo, doing, blocked, done
    description: Optional[str] = None,
    assignee: Optional[str] = None,
    block_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a task.

    Args:
        store: Task store object
        title: Task title (required for new tasks)
        task_id: Existing task ID (for updates)
        status: Task status
        description: Task description
        assignee: Assigned cat/agent
        block_reason: Reason if blocked

    Returns:
        Dict with success status and task_id
    """
    if task_id:
        # Update existing
        updates = {}
        if status:
            updates["status"] = status
        if description:
            updates["description"] = description
        if assignee:
            updates["assignee"] = assignee
        if block_reason:
            updates["block_reason"] = block_reason
            updates["status"] = "blocked"

        if hasattr(store, "update_task"):
            store.update_task(task_id, updates)

        return {"success": True, "task_id": task_id, "action": "updated"}
    else:
        # Create new
        if not title:
            raise ValueError("title required for new task")

        new_id = str(uuid.uuid4())[:8]
        task_data = {
            "id": new_id,
            "title": title,
            "status": status or "todo",
            "description": description,
            "assignee": assignee,
            "created_at": time.time(),
        }

        if hasattr(store, "create_task"):
            store.create_task(task_data)

        return {"success": True, "task_id": new_id, "action": "created"}


def list_tasks(
    store: Any,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
) -> Dict[str, Any]:
    """List tasks with optional filtering.

    Args:
        store: Task store object
        status: Filter by status
        assignee: Filter by assignee

    Returns:
        Dict with tasks list
    """
    tasks = []

    if hasattr(store, "list_tasks"):
        tasks = store.list_tasks(status=status, assignee=assignee)

    return {"tasks": tasks, "count": len(tasks)}


def _invoke_cat_single(cat_id: str, message: str) -> Dict[str, Any]:
    """Helper to invoke a single cat."""
    # Placeholder - real would call AgentRegistry
    return {
        "cat_id": cat_id,
        "response": f"Response from {cat_id}",
        "timestamp": time.time(),
    }


def multi_mention(
    cat_ids: List[str],
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Invoke multiple cats in parallel.

    Args:
        cat_ids: List of cat IDs to invoke (max 3)
        message: Message to send
        context: Optional context dict

    Returns:
        Dict with responses from each cat
    """
    if len(cat_ids) > 3:
        raise ValueError("Cannot invoke more than 3 cats at once")

    if not cat_ids:
        return {"responses": []}

    responses = []

    # Parallel invocation using ThreadPool
    with ThreadPoolExecutor(max_workers=len(cat_ids)) as executor:
        future_to_cat = {
            executor.submit(_invoke_cat_single, cat_id, message): cat_id
            for cat_id in cat_ids
        }

        for future in as_completed(future_to_cat):
            cat_id = future_to_cat[future]
            try:
                result = future.result()
                responses.append(result)
            except Exception as e:
                responses.append({
                    "cat_id": cat_id,
                    "error": str(e),
                    "timestamp": time.time(),
                })

    return {
        "responses": responses,
        "count": len(responses),
    }


def generate_document(
    content: str,
    output_format: str = "markdown",  # markdown, pdf, docx
    title: Optional[str] = None,
    template: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate document from content.

    Args:
        content: Document content (Markdown)
        output_format: Output format
        title: Document title
        template: Optional template name

    Returns:
        Dict with document info
    """
    doc_id = str(uuid.uuid4())[:8]

    # Placeholder - real would convert formats
    return {
        "doc_id": doc_id,
        "format": output_format,
        "title": title,
        "content_length": len(content),
        "status": "generated",
        "path": f"/tmp/doc_{doc_id}.{output_format}",
    }


def search_evidence(
    query: str,
    memory_types: Optional[List[str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search across all memory layers for evidence.

    Args:
        query: Search query
        memory_types: Types to search ['episodic', 'semantic', 'procedural']
        limit: Max results per type

    Returns:
        Dict with results grouped by memory type
    """
    service = MemoryService()
    types = memory_types or ["episodic", "semantic", "procedural"]

    results = {
        "query": query,
        "types_searched": types,
        "episodic": [],
        "semantic": [],
        "procedural": [],
    }

    if "episodic" in types:
        episodes = service.episodic.search(query, limit=limit)
        results["episodic"] = [
            {
                "id": ep["id"],
                "thread_id": ep["thread_id"],
                "cat_id": ep["cat_id"],
                "content": ep["content"][:200],
                "importance": ep["importance"],
                "created_at": ep["created_at"],
            }
            for ep in episodes
        ]

    if "semantic" in types:
        entities = service.semantic.search_entities(query, limit=limit)
        results["semantic"] = [
            {
                "id": ent["id"],
                "name": ent["name"],
                "type": ent["type"],
                "description": ent["description"][:200] if ent.get("description") else None,
            }
            for ent in entities
        ]

    if "procedural" in types:
        procedures = service.procedural.search(query, limit=limit)
        results["procedural"] = [
            {
                "id": proc["id"],
                "name": proc["name"],
                "category": proc["category"],
                "success_count": proc["success_count"],
                "fail_count": proc["fail_count"],
            }
            for proc in procedures
        ]

    results["total"] = len(results["episodic"]) + len(results["semantic"]) + len(results["procedural"])
    return results


# Export all tools
__all__ = [
    "post_message",
    "get_thread_context",
    "list_threads",
    "create_rich_block",
    "request_permission",
    "update_task",
    "list_tasks",
    "multi_mention",
    "generate_document",
    "search_evidence",
]
