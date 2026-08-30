"""
Pydantic v2 schemas for API request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Document Type Schemas ─────────────────────────────────────

class DocumentTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class DocumentTypeResponse(DocumentTypeBase):
    id: int
    category_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: Optional[int] = 0

    model_config = {"from_attributes": True}


# ── Category Schemas ──────────────────────────────────────────

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    type_count: Optional[int] = 0
    document_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class CategoryWithTypesResponse(CategoryResponse):
    types: List[DocumentTypeResponse] = []

    model_config = {"from_attributes": True}


# ── Document Schemas ──────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Schema for returning a document record."""
    id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    type_id: Optional[int] = None
    type_name: Optional[str] = None
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ── Chat & Session Schemas ────────────────────────────────────

class SourceSnippet(BaseModel):
    """A retrieved chunk with source metadata."""
    document_name: str
    chunk_text: str
    page_number: Optional[int] = None
    score: Optional[float] = None


class ChatSessionCreate(BaseModel):
    """Create a new chat session locked to a specific document or set of documents."""
    document_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    title: Optional[str] = None


class ChatMessageItem(BaseModel):
    id: int
    role: str
    question: Optional[str] = None
    answer: str
    sources: List[SourceSnippet] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    """Schema for a document-locked chat session."""
    id: str
    document_id: Optional[int] = None
    document_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    type_id: Optional[int] = None
    type_name: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: Optional[int] = 0

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: List[ChatMessageItem] = []

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    """Schema for incoming chat messages within a locked document session."""
    session_id: Optional[str] = Field(
        default=None,
        description="The active locked chat session ID.",
    )
    document_id: Optional[int] = Field(
        default=None,
        description="Direct document ID if starting/targeting without explicit session ID.",
    )
    document_ids: Optional[List[int]] = Field(
        default=None,
        description="List of document IDs for multi-document scoped chat.",
    )
    question: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Schema for chat responses."""
    session_id: str
    document_id: Optional[int] = None
    document_name: str
    answer: str
    sources: List[SourceSnippet] = []


class ChatMessageResponse(BaseModel):
    """Schema for chat messages retrieved from database history."""
    id: int
    session_id: Optional[str] = None
    document_id: Optional[int] = None
    role: str = "assistant"
    question: Optional[str] = None
    answer: str
    sources: List[SourceSnippet] = []
    created_at: datetime

    model_config = {"from_attributes": True}
