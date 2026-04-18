"""Message history REST endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.thread import ThreadManager
from src.web.dependencies import get_thread_manager
from src.web.schemas import MessageListResponse, MessageResponse

router = APIRouter()


class MessageEditRequest(BaseModel):
    content: str


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
    # Return the most recent messages in ascending order for display
    start = max(0, total - limit - offset)
    end = total - offset
    messages = thread.messages[start:end]
    has_more = start > 0

    return MessageListResponse(
        messages=[
            MessageResponse(
                id=str(m.id) if m.id else "",
                role=m.role,
                content=m.content,
                cat_id=m.cat_id,
                timestamp=m.timestamp,
                metadata=m.metadata,
            )
            for m in messages
        ],
        has_more=has_more,
    )


@router.patch("/threads/{thread_id}/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    thread_id: str,
    message_id: str,
    body: MessageEditRequest,
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    success = await tm.edit_message(thread_id, message_id, body.content)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")

    # Re-fetch thread to get updated message
    thread = await tm.get(thread_id)
    for m in thread.messages:
        if str(m.id) == message_id:
            return MessageResponse(
                id=str(m.id) if m.id else "",
                role=m.role,
                content=m.content,
                cat_id=m.cat_id,
                timestamp=m.timestamp,
                metadata=m.metadata,
            )

    raise HTTPException(status_code=404, detail="Message not found")


@router.delete("/threads/{thread_id}/messages/{message_id}")
async def delete_message(
    thread_id: str,
    message_id: str,
    tm: ThreadManager = Depends(get_thread_manager),
):
    thread = await tm.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    success = await tm.delete_message(thread_id, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"status": "deleted", "message_id": message_id}
