"""Pydantic schemas for MeowAI Home API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Request schemas ---

class ThreadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cat_id: str = Field(default="orange")
    project_path: Optional[str] = Field(default=None, description="Git repository root path for Workspace integration")


class ThreadRename(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ThreadUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    current_cat_id: Optional[str] = None


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
    project_path: Optional[str] = None


class ThreadDetailResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    current_cat_id: str
    is_archived: bool
    messages: list[MessageResponse]
    project_path: Optional[str] = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool


class MessageSendResponse(BaseModel):
    status: str
    invocation_id: str


class SessionStatusResponse(BaseModel):
    session_id: str
    cat_id: str
    cat_name: str
    status: str  # active, sealing, sealed
    created_at: float
    seal_started_at: Optional[float] = None


class ExtractedTaskResponse(BaseModel):
    title: str
    why: str
    owner_cat_id: Optional[str] = None
    status: str
    confidence: float
    extracted_by: str


class TaskListResponse(BaseModel):
    thread_id: str
    tasks: list[ExtractedTaskResponse]
    count: int


class ThreadSummaryResponse(BaseModel):
    thread_id: str
    message_count: int
    conclusions: list[str]
    open_questions: list[str]
    key_files: list[str]
    next_steps: list[str]
    summary_text: str
