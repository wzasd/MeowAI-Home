"""Session chain REST endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from src.session.chain import SessionChain, SessionStatus
from src.models.cat_registry import CatRegistry
from src.web.dependencies import get_session_chain, get_cat_registry

router = APIRouter()


class SessionResponse(BaseModel):
    session_id: str
    cat_id: str
    cat_name: str
    status: str
    created_at: float
    consecutive_restore_failures: int
    message_count: int = 0
    tokens_used: int = 0
    latency_ms: int = 0
    turn_count: int = 0
    cli_command: str = ""
    default_model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    budget_max_prompt: int = 0
    budget_max_context: int = 0


class SessionListResponse(BaseModel):
    """List of sessions for a thread."""

    sessions: List[SessionResponse]
    thread_id: str


class SessionActionResponse(BaseModel):
    success: bool
    session_id: str
    status: str
    message: str


def _build_response(
    record, cat_name: str, cli_command: str = "", default_model: str = "", budget_max_prompt: int = 0, budget_max_context: int = 0
) -> SessionResponse:
    return SessionResponse(
        session_id=record.session_id,
        cat_id=record.cat_id,
        cat_name=cat_name,
        status=record.status.value,
        created_at=record.created_at,
        consecutive_restore_failures=record.consecutive_restore_failures,
        message_count=record.message_count,
        tokens_used=record.tokens_used,
        latency_ms=record.latency_ms,
        turn_count=record.turn_count,
        cli_command=cli_command,
        default_model=default_model,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        cache_read_tokens=record.cache_read_tokens,
        cache_creation_tokens=record.cache_creation_tokens,
        budget_max_prompt=budget_max_prompt,
        budget_max_context=budget_max_context,
    )


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
            cli_cmd = cat.cli_command if cat else ""
            model = cat.default_model if cat else ""
            budget_max_prompt = cat.budget.max_prompt_tokens if cat and cat.budget else 0
            budget_max_context = cat.budget.max_context_tokens if cat and cat.budget else 0
            for record in records:
                sessions.append(_build_response(record, cat_name, cli_cmd, model, budget_max_prompt, budget_max_context))

    sessions.sort(key=lambda x: x.created_at)

    return sessions


@router.get(
    "/threads/{thread_id}/cats/{cat_id}/sessions", response_model=List[SessionResponse]
)
async def list_cat_sessions(
    thread_id: str,
    cat_id: str,
    session_chain: SessionChain = Depends(get_session_chain),
    cat_registry: CatRegistry = Depends(get_cat_registry),
):
    sessions = []

    key = (cat_id, thread_id)
    cat = cat_registry.get(cat_id)
    cat_name = cat.display_name if cat else cat_id
    cli_cmd = cat.cli_command if cat else ""
    model = cat.default_model if cat else ""
    budget_max_prompt = cat.budget.max_prompt_tokens if cat and cat.budget else 0
    budget_max_context = cat.budget.max_context_tokens if cat and cat.budget else 0

    if key in session_chain._chains:
        for record in session_chain._chains[key]:
            sessions.append(_build_response(record, cat_name, cli_cmd, model, budget_max_prompt, budget_max_context))

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
                cli_cmd = cat.cli_command if cat else ""
                model = cat.default_model if cat else ""
                budget_max_prompt = cat.budget.max_prompt_tokens if cat and cat.budget else 0
                budget_max_context = cat.budget.max_context_tokens if cat and cat.budget else 0
                return _build_response(record, cat_name, cli_cmd, model, budget_max_prompt, budget_max_context)

    raise HTTPException(status_code=404, detail="Session not found")
