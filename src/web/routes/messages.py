"""Message history REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.thread import ThreadManager
from src.web.dependencies import get_thread_manager
from src.web.schemas import MessageListResponse, MessageResponse

router = APIRouter()


@router.get("/threads/{thread_id}/messages", response_model=MessageListResponse)
async def get_messages(
    thread_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    total = len(thread.messages)
    messages = thread.messages[offset:offset + limit]
    has_more = (offset + limit) < total

    return MessageListResponse(
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                cat_id=m.cat_id,
                timestamp=m.timestamp,
            )
            for m in messages
        ],
        has_more=has_more,
    )
