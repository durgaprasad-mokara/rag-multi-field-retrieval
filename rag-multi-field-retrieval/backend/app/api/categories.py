"""
Category and Document Type management API routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Category, DocumentType, Document
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryWithTypesResponse,
    DocumentTypeCreate,
    DocumentTypeUpdate,
    DocumentTypeResponse,
)

router = APIRouter(prefix="/categories", tags=["Categories & Types"])


# ── Categories ────────────────────────────────────────────────

@router.get("", response_model=List[CategoryWithTypesResponse])
def get_categories(db: Session = Depends(get_db)):
    """List all categories with nested document types and counts."""
    categories = db.query(Category).order_by(Category.name.asc()).all()
    results = []

    for cat in categories:
        types_res = []
        for dt in cat.types:
            doc_count = db.query(func.count(Document.id)).filter(Document.type_id == dt.id).scalar() or 0
            types_res.append(
                DocumentTypeResponse(
                    id=dt.id,
                    category_id=dt.category_id,
                    name=dt.name,
                    description=dt.description,
                    created_at=dt.created_at,
                    updated_at=dt.updated_at,
                    document_count=doc_count,
                )
            )

        cat_doc_count = db.query(func.count(Document.id)).filter(Document.category_id == cat.id).scalar() or 0
        results.append(
            CategoryWithTypesResponse(
                id=cat.id,
                name=cat.name,
                description=cat.description,
                created_at=cat.created_at,
                updated_at=cat.updated_at,
                type_count=len(cat.types),
                document_count=cat_doc_count,
                types=types_res,
            )
        )

    return results


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(category_in: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category."""
    existing = db.query(Category).filter(func.lower(Category.name) == category_in.name.strip().lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category_in.name.strip()}' already exists.",
        )

    cat = Category(
        name=category_in.name.strip(),
        description=category_in.description.strip() if category_in.description else None,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        created_at=cat.created_at,
        updated_at=cat.updated_at,
        type_count=0,
        document_count=0,
    )


@router.get("/{category_id}", response_model=CategoryWithTypesResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a single category with its document types."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    types_res = []
    for dt in cat.types:
        doc_count = db.query(func.count(Document.id)).filter(Document.type_id == dt.id).scalar() or 0
        types_res.append(
            DocumentTypeResponse(
                id=dt.id,
                category_id=dt.category_id,
                name=dt.name,
                description=dt.description,
                created_at=dt.created_at,
                updated_at=dt.updated_at,
                document_count=doc_count,
            )
        )

    cat_doc_count = db.query(func.count(Document.id)).filter(Document.category_id == cat.id).scalar() or 0
    return CategoryWithTypesResponse(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        created_at=cat.created_at,
        updated_at=cat.updated_at,
        type_count=len(cat.types),
        document_count=cat_doc_count,
        types=types_res,
    )


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, category_in: CategoryUpdate, db: Session = Depends(get_db)):
    """Update a category."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    if category_in.name is not None:
        existing = db.query(Category).filter(
            func.lower(Category.name) == category_in.name.strip().lower(),
            Category.id != category_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{category_in.name.strip()}' already exists.",
            )
        cat.name = category_in.name.strip()

    if category_in.description is not None:
        cat.description = category_in.description.strip() or None

    db.commit()
    db.refresh(cat)

    type_count = db.query(func.count(DocumentType.id)).filter(DocumentType.category_id == cat.id).scalar() or 0
    doc_count = db.query(func.count(Document.id)).filter(Document.category_id == cat.id).scalar() or 0

    return CategoryResponse(
        id=cat.id,
        name=cat.name,
        description=cat.description,
        created_at=cat.created_at,
        updated_at=cat.updated_at,
        type_count=type_count,
        document_count=doc_count,
    )


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a category and all its types and documents."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    db.delete(cat)
    db.commit()
    return {"message": f"Category '{cat.name}' and all associated types and documents deleted successfully."}


# ── Document Types ────────────────────────────────────────────

@router.get("/{category_id}/types", response_model=List[DocumentTypeResponse])
def get_document_types(category_id: int, db: Session = Depends(get_db)):
    """List all document types under a category."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    types = db.query(DocumentType).filter(DocumentType.category_id == category_id).order_by(DocumentType.name.asc()).all()
    results = []
    for dt in types:
        doc_count = db.query(func.count(Document.id)).filter(Document.type_id == dt.id).scalar() or 0
        results.append(
            DocumentTypeResponse(
                id=dt.id,
                category_id=dt.category_id,
                name=dt.name,
                description=dt.description,
                created_at=dt.created_at,
                updated_at=dt.updated_at,
                document_count=doc_count,
            )
        )
    return results


@router.post("/{category_id}/types", response_model=DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
def create_document_type(category_id: int, type_in: DocumentTypeCreate, db: Session = Depends(get_db)):
    """Create a new document type under a category."""
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found.")

    existing = db.query(DocumentType).filter(
        DocumentType.category_id == category_id,
        func.lower(DocumentType.name) == type_in.name.strip().lower(),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document type '{type_in.name.strip()}' already exists in category '{cat.name}'.",
        )

    dt = DocumentType(
        category_id=category_id,
        name=type_in.name.strip(),
        description=type_in.description.strip() if type_in.description else None,
    )
    db.add(dt)
    db.commit()
    db.refresh(dt)

    return DocumentTypeResponse(
        id=dt.id,
        category_id=dt.category_id,
        name=dt.name,
        description=dt.description,
        created_at=dt.created_at,
        updated_at=dt.updated_at,
        document_count=0,
    )


@router.put("/types/{type_id}", response_model=DocumentTypeResponse)
def update_document_type(type_id: int, type_in: DocumentTypeUpdate, db: Session = Depends(get_db)):
    """Update a document type."""
    dt = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    if not dt:
        raise HTTPException(status_code=404, detail="Document type not found.")

    if type_in.name is not None:
        existing = db.query(DocumentType).filter(
            DocumentType.category_id == dt.category_id,
            func.lower(DocumentType.name) == type_in.name.strip().lower(),
            DocumentType.id != type_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document type '{type_in.name.strip()}' already exists in this category.",
            )
        dt.name = type_in.name.strip()

    if type_in.description is not None:
        dt.description = type_in.description.strip() or None

    db.commit()
    db.refresh(dt)

    doc_count = db.query(func.count(Document.id)).filter(Document.type_id == dt.id).scalar() or 0
    return DocumentTypeResponse(
        id=dt.id,
        category_id=dt.category_id,
        name=dt.name,
        description=dt.description,
        created_at=dt.created_at,
        updated_at=dt.updated_at,
        document_count=doc_count,
    )


@router.delete("/types/{type_id}")
def delete_document_type(type_id: int, db: Session = Depends(get_db)):
    """Delete a document type and its associated documents."""
    dt = db.query(DocumentType).filter(DocumentType.id == type_id).first()
    if not dt:
        raise HTTPException(status_code=404, detail="Document type not found.")

    db.delete(dt)
    db.commit()
    return {"message": f"Document type '{dt.name}' and all associated documents deleted successfully."}
