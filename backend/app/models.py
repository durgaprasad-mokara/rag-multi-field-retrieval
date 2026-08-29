"""
SQLAlchemy ORM models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Document(Base):
    """Represents an uploaded document in PostgreSQL."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)          # pdf, txt, docx, md, csv, html
    file_size = Column(Integer, default=0)               # bytes
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="processing")        # processing | ready | error
    uploaded_at = Column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r} status={self.status!r}>"


class ChatMessage(Base):
    """Represents a stored chat conversation in PostgreSQL."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=True)
    question = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    sources = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} question={self.question[:20]!r}>"

