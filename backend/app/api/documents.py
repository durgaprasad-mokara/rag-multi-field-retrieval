"""
Document management API routes.
"""
import os
import shutil
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document
from app.schemas import DocumentResponse
from app.rag.loader import load_document
from app.rag.chunker import split_documents
from app.rag.vectorstore import add_documents, delete_by_document_id

router = APIRouter(tags=["Documents"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md", ".csv", ".html"}


@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a document, ingest it into the RAG pipeline, and store metadata."""
    # ── Validate file extension ──────────────────────────────
    filename = file.filename or "untitled"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Save file to disk ────────────────────────────────────
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    # ── Create DB record ─────────────────────────────────────
    doc = Document(
        filename=filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # ── RAG ingestion pipeline ───────────────────────────────
    try:
        # 1. Load raw documents
        raw_docs = load_document(file_path)

        # 2. Split into chunks
        chunks = split_documents(raw_docs, document_id=doc.id, filename=filename)

        # 3. Embed and store in Qdrant
        add_documents(chunks, document_id=doc.id)

        # 4. Update DB record
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        db.commit()
        db.refresh(doc)

    except Exception as e:
        doc.status = "error"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return doc


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return docs


@router.delete("/documents/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document from PostgreSQL and its vectors from Qdrant."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove vectors from Qdrant
    try:
        delete_by_document_id(document_id)
    except Exception:
        pass  # Qdrant cleanup is best-effort

    # Remove file from disk
    file_path = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove DB record
    db.delete(doc)
    db.commit()

    return {"message": f"Document '{doc.filename}' deleted successfully"}
