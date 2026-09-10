"""
SQLAlchemy ORM models for Multi-Category, Multi-Type, Document-Specific RAG.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, ForeignKey, func, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    """Represents a document category (e.g., Company, Education, Student, Business, etc.)."""
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    types = relationship("DocumentType", back_populates="category", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


class DocumentType(Base):
    """Represents a document type under a category (e.g., Study Materials, Policies, Employees)."""
    __tablename__ = "document_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="types")
    documents = relationship("Document", back_populates="doc_type", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<DocumentType id={self.id} category_id={self.category_id} name={self.name!r}>"


class Document(Base):
    """Represents an uploaded document in PostgreSQL."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="CASCADE"), nullable=True, index=True)
    document_name = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    mime_type = Column(String(150), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    source_type = Column(String(50), nullable=False, default="document")
    storage_path = Column(Text, nullable=True)
    processing_status = Column(String(50), nullable=False, default="pending")
    processing_error = Column(Text, nullable=True)
    total_pages = Column(Integer, nullable=True)
    total_chunks = Column(Integer, nullable=True)
    metadata_col = Column("metadata", JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    file_path = Column(String(500), nullable=True)
    
    # Aliases for frontend backward compatibility
    @property
    def filename(self):
        return self.document_name or self.original_filename
        
    @property
    def chunk_count(self):
        return self.total_chunks or 0
        
    @property
    def status(self):
        return self.processing_status
        
    @property
    def uploaded_at(self):
        return self.created_at

    # Relationships
    category = relationship("Category", back_populates="documents")
    doc_type = relationship("DocumentType", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.status!r}>"


class DocumentChunk(Base):
    """Represents a text chunk stored for a document."""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc_id={self.document_id} chunk_index={self.chunk_index}>"


class ChatSession(Base):
    """
    Represents a locked chat session scoped strictly to a single document.
    """
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_name = Column(String(255), nullable=True)
    selected_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    selected_type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    selected_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    voice_enabled = Column(Boolean, nullable=False, default=False)
    voice_response_enabled = Column(Boolean, nullable=False, default=False)
    metadata_col = Column("metadata", JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    # Aliases for backward compatibility in backend code
    @property
    def document_id(self):
        return self.selected_document_id

    @property
    def category_id(self):
        return self.selected_category_id

    @property
    def type_id(self):
        return self.selected_type_id

    @property
    def title(self):
        return self.session_name

    # Relationships
    document = relationship("Document", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at.asc()")

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} document_id={self.selected_document_id}>"


class ChatMessage(Base):
    """Represents a stored chat conversation message in PostgreSQL."""
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    input_type = Column(String(30), nullable=False, default="text")
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    type_id = Column(UUID(as_uuid=True), ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    requested_fields = Column(JSONB, nullable=False, default=[])
    answered_fields = Column(JSONB, nullable=False, default=[])
    retrieval_metadata = Column(JSONB, nullable=False, default={})
    response_time_ms = Column(Numeric, nullable=True)
    tts_enabled = Column(Boolean, nullable=False, default=False)
    tts_status = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Aliases for backward compatibility
    @property
    def question(self):
        return self.content if self.role == "user" else None
        
    @property
    def answer(self):
        return self.content if self.role == "assistant" else None
        
    @property
    def sources(self):
        return self.retrieval_metadata.get("sources_json") if self.retrieval_metadata else None

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    chart = relationship("ChartOutput", back_populates="message", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role!r}>"


class ChartOutput(Base):
    """Represents chart data generated during a chat session."""
    __tablename__ = "chart_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    chat_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chart_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    message = relationship("ChatMessage", back_populates="chart")
    document = relationship("Document")

    def __repr__(self) -> str:
        return f"<ChartOutput id={self.id} msg_id={self.chat_message_id}>"
