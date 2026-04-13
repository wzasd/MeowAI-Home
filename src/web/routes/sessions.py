"""Session chain REST endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.session.chain import SessionChain, SessionStatus
from src.models.cat_registry import CatRegistry
from src.web.dependencies import get_session_chain, get_cat_registry

router = APIRouter()


class SessionResponse(BaseModel):
    """Session record response - matches frontend expectations."""
    session_id: str
    cat_id: str
    cat_name: str
    status: str  # "active" | "sealed"
    created_at: float
    consecutive_restore_failures: int


class SessionListResponse(BaseModel):
    """List of sessions for a thread."""
    sessions: List[SessionResponse]
    thread_id: str


class SessionActionResponse(BaseModel):
    """Session action result."""
    success: bool
    session_id: str
    status: str
    message: str


@router.get("/threads/{thread_id}/sessions", response_model=List[SessionResponse])
async def list_thread_sessions(
    thread_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
    cat_registry: CatRegistry = Depends(get_cat_registry),
):
    """Get all sessions for a thread across all cats."""
    sessions = []

    # Get all sessions from the chain for this thread
    for (cat_id, tid), records in session_chain._chains.items():
        if tid == thread_id:
            cat = cat_registry.get(cat_id)
            cat_name = cat.display_name if cat else cat_id
            for record in records:
                sessions.append(SessionResponse(
                    session_id=record.session_id,
                    cat_id=record.cat_id,
                    cat_name=cat_name,
                    status=record.status.value,
                    created_at=record.created_at,
                    consecutive_restore_failures=record.consecutive_restore_failures,
                ))

    # Sort by creation time (oldest first for timeline view)
    sessions.sort(key=lambda x: x.created_at)

    return sessions


@router.get("/threads/{thread_id}/cats/{cat_id}/sessions", response_model=List[SessionResponse])
async def list_cat_sessions(
    thread_id: str,
    cat_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
    cat_registry: CatRegistry = Depends(get_cat_registry),
):
    """Get sessions for a specific cat in a thread."""
    sessions = []

    key = (cat_id, thread_id)
    cat = cat_registry.get(cat_id)
    cat_name = cat.display_name if cat else cat_id

    if key in session_chain._chains:
        for record in session_chain._chains[key]:
            sessions.append(SessionResponse(
                session_id=record.session_id,
                cat_id=record.cat_id,
                cat_name=cat_name,
                status=record.status.value,
                created_at=record.created_at,
                consecutive_restore_failures=record.consecutive_restore_failures,
            ))

    # Sort by creation time
    sessions.sort(key=lambda x: x.created_at)

    return sessions


@router.post("/sessions/{session_id}/seal", response_model=SessionActionResponse)
async def seal_session(
    session_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
):
    """Manually seal a session."""
    # Find the session
    found_record = None
    for (cat_id, thread_id), records in session_chain._chains.items():
        for record in records:
            if record.session_id == session_id:
                found_record = record
                break
        if found_record:
            break

    if not found_record:
        raise HTTPException(status_code=404, detail="Session not found")

    if found_record.status == SessionStatus.SEALED:
        return SessionActionResponse(
            success=True,
            session_id=session_id,
            status="sealed",
            message="Session is already sealed",
        )

    found_record.status = SessionStatus.SEALED

    return SessionActionResponse(
        success=True,
        session_id=session_id,
        status="sealed",
        message="Session sealed successfully",
    )


@router.post("/sessions/{session_id}/unseal", response_model=SessionActionResponse)
async def unseal_session(
    session_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
):
    """Manually unseal (reactivate) a session."""
    # Find the session
    found_record = None
    for (cat_id, thread_id), records in session_chain._chains.items():
        for record in records:
            if record.session_id == session_id:
                found_record = record
                break
        if found_record:
            break

    if not found_record:
        raise HTTPException(status_code=404, detail="Session not found")

    if found_record.status == SessionStatus.ACTIVE:
        return SessionActionResponse(
            success=True,
            session_id=session_id,
            status="active",
            message="Session is already active",
        )

    found_record.status = SessionStatus.ACTIVE
    found_record.consecutive_restore_failures = 0

    return SessionActionResponse(
        success=True,
        session_id=session_id,
        status="active",
        message="Session unsealed successfully",
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
    cat_registry: CatRegistry = Depends(get_cat_registry),
):
    """Get a specific session by ID."""
    for (cat_id, thread_id), records in session_chain._chains.items():
        for record in records:
            if record.session_id == session_id:
                cat = cat_registry.get(cat_id)
                cat_name = cat.display_name if cat else cat_id
                return SessionResponse(
                    session_id=record.session_id,
                    cat_id=record.cat_id,
                    cat_name=cat_name,
                    status=record.status.value,
                    created_at=record.created_at,
                    consecutive_restore_failures=record.consecutive_restore_failures,
                )

    raise HTTPException(status_code=404, detail="Session not found")
