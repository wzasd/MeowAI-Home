"""Memory REST API endpoints"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/memory", tags=["memory"])

# Global instance (set during app initialization)
memory_service = None


def set_memory_service(service):
    global memory_service
    memory_service = service


@router.get("/search")
async def search_memory(
    q: str = Query(..., description="Search query"),
    type: Optional[str] = Query(None, description="Content type filter"),
    limit: int = Query(10, ge=1, le=50),
):
    """Hybrid search across episodic, semantic, and procedural memory."""
    if not memory_service:
        raise HTTPException(500, "Memory service not initialized")

    results = []

    # Episodic search
    episodes = memory_service.episodic.search(q, limit=limit)
    for ep in episodes:
        results.append({
            "type": "episode",
            "id": ep.get("id"),
            "content": ep.get("content", ""),
            "thread_id": ep.get("thread_id"),
            "importance": ep.get("importance"),
        })

    # Semantic search
    entities = memory_service.semantic.search_entities(q, limit=limit // 2)
    for ent in entities:
        results.append({
            "type": "entity",
            "id": ent.get("id"),
            "name": ent.get("name"),
            "entity_type": ent.get("type"),
        })

    return {"query": q, "results": results[:limit]}


@router.get("/entities")
async def list_entities(
    type: Optional[str] = Query(None, description="Entity type filter"),
    limit: int = Query(20, ge=1, le=100),
):
    """List semantic memory entities."""
    if not memory_service:
        raise HTTPException(500, "Memory service not initialized")

    entities = memory_service.semantic.get_all(limit=limit)
    if type:
        entities = [e for e in entities if e.get("type") == type]

    return entities


@router.get("/relations")
async def get_entity_relations(
    entity: str = Query(..., description="Entity name"),
    max_depth: int = Query(2, ge=1, le=5),
):
    """Get relations for an entity."""
    if not memory_service:
        raise HTTPException(500, "Memory service not initialized")

    related = memory_service.semantic.get_related(entity, max_depth=max_depth)
    return {
        "entity": entity,
        "relations": related,
    }
