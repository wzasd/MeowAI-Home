"""Evidence API routes — knowledge search and retrieval."""

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.evidence.store import EvidenceDoc, EvidenceStore

router = APIRouter(prefix="/evidence", tags=["evidence"])

# Singleton store
_store: Optional[EvidenceStore] = None


def get_store() -> EvidenceStore:
    """Get or create evidence store singleton."""
    global _store
    if _store is None:
        _store = EvidenceStore()
    return _store


# === Pydantic Models ===

EvidenceConfidence = Literal["high", "mid", "low"]
EvidenceSourceType = Literal["decision", "phase", "discussion", "commit"]
EvidenceStatus = Literal["draft", "pending", "published", "archived"]


class EvidenceResult(BaseModel):
    """Evidence search result."""
    id: int
    title: str
    anchor: str
    snippet: str
    confidence: EvidenceConfidence
    source_type: EvidenceSourceType
    status: Optional[EvidenceStatus] = None


class EvidenceSearchResponse(BaseModel):
    """Evidence search response."""
    results: List[EvidenceResult]
    degraded: bool
    degrade_reason: Optional[str] = None


class EvidenceDocCreate(BaseModel):
    """Create evidence document request."""
    title: str
    anchor: str = ""
    summary: str = ""
    content: str = ""
    kind: EvidenceSourceType = "discussion"
    source: str = ""
    confidence: EvidenceConfidence = "mid"
    status: EvidenceStatus = "published"


class EvidenceStatusResponse(BaseModel):
    """Evidence store status response."""
    backend: str
    healthy: bool
    total: int
    by_kind: dict
    last_updated: Optional[str] = None


def _kind_to_source_type(kind: str) -> str:
    """Map kind to source type."""
    mapping = {
        "decision": "decision",
        "plan": "phase",
        "discussion": "discussion",
        "commit": "commit",
    }
    return mapping.get(kind, "discussion")


def _db_to_result(doc: dict) -> EvidenceResult:
    """Convert database doc to API result."""
    snippet = doc.get("summary", "") or doc.get("content", "")
    if len(snippet) > 200:
        snippet = snippet[:200] + "..."

    return EvidenceResult(
        id=doc.get("id", 0),
        title=doc.get("title", "Untitled"),
        anchor=doc.get("anchor", ""),
        snippet=snippet,
        confidence=doc.get("confidence", "mid"),
        source_type=_kind_to_source_type(doc.get("kind", "discussion")),
        status=doc.get("status"),
    )


# === API Endpoints ===

@router.get("/search", response_model=EvidenceSearchResponse)
async def search_evidence(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=20),
) -> EvidenceSearchResponse:
    """Search evidence documents."""
    store = get_store()

    try:
        docs = store.search(q, limit=limit)
        results = [_db_to_result(d) for d in docs]
        return EvidenceSearchResponse(results=results, degraded=False)
    except Exception as e:
        return EvidenceSearchResponse(
            results=[],
            degraded=True,
            degrade_reason=str(e),
        )


@router.get("/status", response_model=EvidenceStatusResponse)
async def get_evidence_status() -> EvidenceStatusResponse:
    """Get evidence store status."""
    store = get_store()
    status = store.get_status()
    return EvidenceStatusResponse(**status)


@router.post("/docs", response_model=dict)
async def create_evidence_doc(doc: EvidenceDocCreate) -> dict:
    """Create an evidence document."""
    store = get_store()
    evidence_doc = EvidenceDoc(
        title=doc.title,
        anchor=doc.anchor,
        summary=doc.summary,
        content=doc.content,
        kind=doc.kind,
        source=doc.source,
        confidence=doc.confidence,
        status=doc.status,
    )
    row_id = store.store(evidence_doc)
    return {"id": row_id, "title": doc.title}


@router.get("/docs", response_model=dict)
async def list_evidence_docs(
    kind: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """List evidence documents."""
    store = get_store()

    if kind:
        docs = store.list_by_kind(kind, limit=limit)
    else:
        docs = store.list_recent(limit=limit, offset=offset)

    return {
        "docs": [_db_to_result(d).model_dump() for d in docs],
        "total": len(docs),
    }


@router.get("/docs/{doc_id}")
async def get_evidence_doc(doc_id: int) -> dict:
    """Get a single evidence document."""
    store = get_store()
    doc = store.get_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/docs/{doc_id}")
async def delete_evidence_doc(doc_id: int) -> dict:
    """Delete an evidence document."""
    store = get_store()
    success = store.delete(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True}
