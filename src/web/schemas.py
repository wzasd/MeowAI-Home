"""Pydantic schemas for MeowAI Home API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Request schemas ---

class ThreadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cat_id: str = Field(default="orange")


class ThreadRename(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class MessageSend(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    cat_id: Optional[str] = None


# --- Response schemas ---

class MessageResponse(BaseModel):
    role: str
    content: str
    cat_id: Optional[str] = None
    timestamp: datetime


class ThreadResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    current_cat_id: str
    is_archived: bool
    message_count: int


class ThreadDetailResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    current_cat_id: str
    is_archived: bool
    messages: list[MessageResponse]


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool


class MessageSendResponse(BaseModel):
    status: str
    invocation_id: str
