"""Thread CRUD REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.thread import ThreadManager
from src.web.dependencies import get_thread_manager
from src.web.schemas import (
    ThreadCreate,
    ThreadRename,
    ThreadResponse,
    ThreadDetailResponse,
    ThreadListResponse,
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
                metadata=m.metadata,
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
    body: ThreadRename,
    tm: ThreadManager = Depends(get_thread_manager),
):
    """Update thread (rename)."""
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if body.name:
        await tm.rename(thread_id, body.name)

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
