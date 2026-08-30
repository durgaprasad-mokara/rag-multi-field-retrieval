"""
SQLAlchemy ORM models for Multi-Category, Multi-Type, Document-Specific RAG.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Category(Base):
    """Represents a document category (e.g., Company, Education, Student, Business, etc.)."""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
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

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
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

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    type_id = Column(Integer, ForeignKey("document_types.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)        # pdf, docx, txt, md, csv, xlsx, html
    file_size = Column(Integer, default=0)                # bytes
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="processing")     # processing | ready | error
    uploaded_at = Column(DateTime, default=func.now())

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

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
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

    id = Column(String(64), primary_key=True, index=True)  # UUID or session token
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    type_id = Column(Integer, ForeignKey("document_types.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at.asc()")

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} document_id={self.document_id}>"


class ChatMessage(Base):
    """Represents a stored chat conversation message in PostgreSQL."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(20), nullable=False)               # user | assistant
    question = Column(Text, nullable=True)                  # question text (for user or context)
    answer = Column(Text, nullable=False)                   # message content / response
    sources = Column(Text, nullable=True)                   # JSON string of source snippets
    created_at = Column(DateTime, default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role!r}>"
