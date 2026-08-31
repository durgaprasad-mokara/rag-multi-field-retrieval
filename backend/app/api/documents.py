"""
Document management API routes supporting Category and Type hierarchy.
"""
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, DocumentChunk, Category, DocumentType, ChatSession
from app.schemas import DocumentResponse
from app.rag.loader import load_document
from app.rag.chunker import split_documents
from app.rag.vectorstore import add_documents, delete_by_document_id

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls", ".html", ".htm", ".json", ".log",
    ".mp4", ".webm", ".mov", ".mkv", ".avi", ".m4v", ".flv", ".mp3", ".wav", ".m4a"
}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    category_id: int = Form(...),
    type_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """
    Upload a document under a specific Category and Type, index it with RAG,
    and persist metadata and chunks in PostgreSQL and Qdrant.
    """
    # ── Validate category and type ───────────────────────────
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Invalid category_id. Category does not exist.")

    dt = db.query(DocumentType).filter(DocumentType.id == type_id, DocumentType.category_id == category_id).first()
    if not dt:
        raise HTTPException(status_code=400, detail="Invalid type_id or type does not belong to the selected category.")

    # ── Validate file extension ──────────────────────────────
    filename = file.filename or "untitled"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # ── Save file to disk ────────────────────────────────────
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_filename = f"{filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = os.path.getsize(file_path)

    # ── Create DB record ─────────────────────────────────────
    doc = Document(
        category_id=category_id,
        type_id=type_id,
        filename=filename,
        file_path=file_path,
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
        if not raw_docs:
            raise ValueError("No text content could be extracted from document.")

        # 2. Chunk documents
        chunks = split_documents(
            documents=raw_docs,
            document_id=doc.id,
            filename=filename,
            category_id=cat.id,
            category_name=cat.name,
            type_id=dt.id,
            type_name=dt.name,
        )

        if not chunks:
            raise ValueError("Document yielded 0 chunks after splitting.")

        # 3. Store chunks in PostgreSQL
        for chunk in chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=chunk.metadata.get("chunk_index", 0),
                content=chunk.page_content,
                page_number=chunk.metadata.get("page_number"),
            )
            db.add(db_chunk)

        # 4. Embed and upsert into Qdrant
        add_documents(chunks, document_id=doc.id)

        # 5. Mark ready in DB
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        db.commit()
        db.refresh(doc)

    except Exception as e:
        doc.status = "error"
        db.commit()
        print(f"❌ Document indexing failed for id={doc.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process and index document: {str(e)}",
        )

    return DocumentResponse(
        id=doc.id,
        category_id=doc.category_id,
        category_name=cat.name,
        type_id=doc.type_id,
        type_name=dt.name,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
    )


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    category_id: Optional[int] = None,
    type_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all documents with category and type names, optionally filtered."""
    query = db.query(Document)
    if category_id is not None:
        query = query.filter(Document.category_id == category_id)
    if type_id is not None:
        query = query.filter(Document.type_id == type_id)

    documents = query.order_by(Document.uploaded_at.desc()).all()
    results = []

    for d in documents:
        cat_name = d.category.name if d.category else None
        type_name = d.doc_type.name if d.doc_type else None
        results.append(
            DocumentResponse(
                id=d.id,
                category_id=d.category_id,
                category_name=cat_name,
                type_id=d.type_id,
                type_name=type_name,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                chunk_count=d.chunk_count,
                status=d.status,
                uploaded_at=d.uploaded_at,
            )
        )

    return results


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get a single document metadata."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentResponse(
        id=doc.id,
        category_id=doc.category_id,
        category_name=doc.category.name if doc.category else None,
        type_id=doc.type_id,
        type_name=doc.doc_type.name if doc.doc_type else None,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        chunk_count=doc.chunk_count,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
    )


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    Delete a document: removes from disk, PostgreSQL, and deletes vectors from Qdrant.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 1. Remove file from disk
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    # 2. Delete vectors from Qdrant
    try:
        delete_by_document_id(document_id)
    except Exception as e:
        print(f"⚠️ Warning: Failed to delete Qdrant vectors for doc {document_id}: {e}")

    # 3. Delete from database (cascades to chunks and chat sessions)
    db.delete(doc)
    db.commit()

    return {"message": f"Document '{doc.filename}' and all its index data deleted successfully."}
