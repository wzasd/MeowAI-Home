"""Thread CRUD REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List

from src.thread import ThreadManager
from src.web.dependencies import get_thread_manager
from src.web.schemas import (
    ThreadCreate,
    ThreadRename,
    ThreadUpdate,
    ThreadResponse,
    ThreadDetailResponse,
    ThreadListResponse,
    SessionStatusResponse,
    ExtractedTaskResponse,
    TaskListResponse,
    ThreadSummaryResponse,
)

router = APIRouter()


def _thread_to_response(thread) -> ThreadResponse:
    return ThreadResponse(
        id=thread.id,
        name=thread.name,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        current_cat_id=thread.current_cat_id,
        is_archived=thread.is_archived,
        message_count=len(thread.messages),
        project_path=thread.project_path,
    )


def _thread_to_detail(thread) -> ThreadDetailResponse:
    from src.web.schemas import MessageResponse
    return ThreadDetailResponse(
        id=thread.id,
        name=thread.name,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        current_cat_id=thread.current_cat_id,
        is_archived=thread.is_archived,
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                cat_id=m.cat_id,
                timestamp=m.timestamp,
            )
            for m in thread.messages
        ],
        project_path=thread.project_path,
    )


@router.post("/threads", response_model=ThreadDetailResponse)
async def create_thread(
    body: ThreadCreate,
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.create(body.name, body.cat_id, body.project_path)
    return _thread_to_detail(thread)


@router.get("/threads", response_model=ThreadListResponse)
async def list_threads(
    tm: ThreadManager = Depends(get_thread_manager),
):
    threads = await tm.list()
    return ThreadListResponse(
        threads=[_thread_to_response(t) for t in threads]
    )


@router.get("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def get_thread(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return _thread_to_detail(thread)


@router.patch("/threads/{thread_id}", response_model=ThreadDetailResponse)
async def update_thread(
    thread_id: str,
    body: ThreadUpdate,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Update thread (rename and/or switch cat)."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if body.name:
        await tm.rename(thread_id, body.name)
    if body.current_cat_id is not None:
        thread = await tm.get(thread_id)
        if thread:
            thread.current_cat_id = body.current_cat_id
            await tm.update_thread(thread)

    thread = await tm.get(thread_id)
    return _thread_to_detail(thread)


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    success = await tm.delete(thread_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "deleted"}


@router.post("/threads/{thread_id}/archive", response_model=ThreadDetailResponse)
async def archive_thread(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    await tm.archive(thread_id)
    thread = await tm.get(thread_id)
    return _thread_to_detail(thread)


@router.get("/threads/{thread_id}/sessions", response_model=List[SessionStatusResponse])
async def get_thread_sessions(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Get all sessions for a thread with their status."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    from src.session.manager import SessionManager
    from src.models.cat_registry import CatRegistry

    session_mgr = SessionManager()
    # Use the global singleton which has loaded breeds
    cat_registry = CatRegistry()
    # If it's empty, try getting from app import context
    if not cat_registry.get_all_ids():
        from src.models.cat_registry import cat_registry as global_reg
        cat_registry = global_reg

    sessions = session_mgr.list_by_thread(thread_id)
    result = []
    for session in sessions:
        cat = cat_registry.get(session.cat_id)
        cat_name = cat.display_name if cat else session.cat_id
        result.append(
            SessionStatusResponse(
                session_id=session.session_id,
                cat_id=session.cat_id,
                cat_name=cat_name,
                status=session.status.value,
                created_at=session.created_at,
                seal_started_at=session.seal_started_at,
            )
        )
    return result


@router.get("/threads/{thread_id}/tasks", response_model=TaskListResponse)
async def get_thread_tasks(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Extract tasks from thread messages."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    from src.orchestration.task_extractor import TaskExtractor

    extractor = TaskExtractor()
    messages = [
        {"content": m.content, "role": m.role, "cat_id": m.cat_id}
        for m in thread.messages
    ]
    tasks = extractor.extract(messages)

    return TaskListResponse(
        thread_id=thread_id,
        tasks=[
            ExtractedTaskResponse(
                title=t.title,
                why=t.why,
                owner_cat_id=t.owner_cat_id,
                status=t.status.value,
                confidence=t.confidence,
                extracted_by=t.extracted_by,
            )
            for t in tasks
        ],
        count=len(tasks),
    )


@router.get("/threads/{thread_id}/summary", response_model=ThreadSummaryResponse)
async def get_thread_summary(
    thread_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Generate or retrieve thread summary."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    from src.orchestration.auto_summarizer import AutoSummarizer

    summarizer = AutoSummarizer(min_messages=5, cooldown_seconds=0)
    messages = [
        {"content": m.content, "role": m.role, "cat_id": m.cat_id}
        for m in thread.messages
    ]
    summary = summarizer.summarize(thread_id, messages)

    if not summary:
        return ThreadSummaryResponse(
            thread_id=thread_id,
            message_count=len(thread.messages),
            conclusions=[],
            open_questions=[],
            key_files=[],
            next_steps=[],
            summary_text="消息不足，无法生成摘要。",
        )

    return ThreadSummaryResponse(
        thread_id=summary.thread_id,
        message_count=summary.message_count,
        conclusions=summary.conclusions,
        open_questions=summary.open_questions,
        key_files=summary.key_files,
        next_steps=summary.next_steps,
        summary_text=summary.summary_text,
    )
