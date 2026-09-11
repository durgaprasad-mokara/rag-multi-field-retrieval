import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Document, DocumentChunk, Category, DocumentType
from app.rag.vectorstore import _get_qdrant_client, COLLECTION_NAME, add_documents, delete_by_document_id
from app.rag.chunker import split_documents
from app.rag.loader import load_document

router = APIRouter(prefix="/api/debug", tags=["Debug"])


@router.get("/document/{document_id}")
def inspect_document(document_id: UUID, db: Session = Depends(get_db)):
    """Inspect the ingestion status and Qdrant points of a given document ID."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in PostgreSQL.")

    cat = db.query(Category).filter(Category.id == doc.category_id).first()
    dt = db.query(DocumentType).filter(DocumentType.id == doc.type_id).first()

    # Get PostgreSQL chunks count
    pg_chunks = db.query(func.count(DocumentChunk.id)).filter(DocumentChunk.document_id == document_id).scalar()

    # Get Qdrant points count
    client = _get_qdrant_client()
    try:
        qdrant_points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter={"must": [{"key": "metadata.document_id", "match": {"value": str(document_id)}}]},
            limit=10000,
            with_payload=False,
            with_vectors=False,
        )
        qdrant_count = len(qdrant_points)
    except Exception as e:
        qdrant_count = -1
        qdrant_error = str(e)
    else:
        qdrant_error = None

    return {
        "document_name": doc.document_name,
        "document_id": str(doc.id),
        "category_id": str(doc.category_id),
        "category_name": cat.name if cat else None,
        "type_id": str(doc.type_id),
        "type_name": dt.name if dt else None,
        "processing_status": doc.processing_status,
        "processing_error": doc.processing_error,
        "pg_chunk_count": pg_chunks,
        "qdrant_point_count": qdrant_count,
        "qdrant_error": qdrant_error,
        "file_path": doc.file_path,
        "file_size": doc.file_size,
    }


@router.post("/reprocess/{document_id}")
def reprocess_document(document_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Idempotent function to re-chunk and re-embed a document if data is missing."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    def _reprocess():
        with next(get_db()) as db_session:
            current_doc = db_session.query(Document).filter(Document.id == document_id).first()
            if not current_doc:
                return

            try:
                current_doc.processing_status = "processing"
                db_session.commit()

                # Re-load
                raw_docs = load_document(current_doc.file_path)
                if not raw_docs:
                    raise ValueError("No text extracted.")

                cat = db_session.query(Category).filter(Category.id == current_doc.category_id).first()
                dt = db_session.query(DocumentType).filter(DocumentType.id == current_doc.type_id).first()

                chunks = split_documents(
                    documents=raw_docs,
                    document_id=current_doc.id,
                    filename=current_doc.document_name,
                    category_id=current_doc.category_id,
                    category_name=cat.name if cat else "",
                    type_id=current_doc.type_id,
                    type_name=dt.name if dt else "",
                )

                # Clear old data
                db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
                db_session.commit()
                delete_by_document_id(str(document_id))

                # Insert new data
                for chunk in chunks:
                    db_chunk = DocumentChunk(
                        document_id=current_doc.id,
                        chunk_index=chunk.metadata.get("chunk_index", 0),
                        content=chunk.page_content,
                        page_number=chunk.metadata.get("page_number"),
                    )
                    db_session.add(db_chunk)

                add_documents(chunks, document_id=str(current_doc.id))

                current_doc.total_chunks = len(chunks)
                current_doc.processing_status = "ready"
                current_doc.processing_error = None
                db_session.commit()
                print(f"✅ Reprocessed document {document_id}")

            except Exception as e:
                current_doc.processing_status = "error"
                current_doc.processing_error = str(e)
                db_session.commit()
                print(f"❌ Reprocessing failed for {document_id}: {e}")

    background_tasks.add_task(_reprocess)
    return {"message": "Reprocessing started in the background."}
