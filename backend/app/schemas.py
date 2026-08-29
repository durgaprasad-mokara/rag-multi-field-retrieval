"""
Pydantic v2 schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Document Schemas ─────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Schema for returning a document record."""
    id: int
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Schemas ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Schema for incoming chat messages."""
    question: str = Field(..., min_length=1, max_length=2000)
    document_id: Optional[int] = Field(
        default=None,
        description="Filter retrieval to a specific document. If null, searches all documents.",
    )


class SourceSnippet(BaseModel):
    """A retrieved chunk with source metadata."""
    document_name: str
    chunk_text: str
    score: Optional[float] = None


class ChatResponse(BaseModel):
    """Schema for chat responses."""
    answer: str
    sources: list[SourceSnippet] = []


class ChatMessageResponse(BaseModel):
    """Schema for chat messages retrieved from database history."""
    id: int
    document_id: Optional[int] = None
    question: str
    answer: str
    sources: list[SourceSnippet] = []
    created_at: datetime

    model_config = {"from_attributes": True}

