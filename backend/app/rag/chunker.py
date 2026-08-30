"""
Document chunker — splits documents into smaller pieces for embedding.
Preserves structure, handles lists and tables, and enriches hierarchical metadata.
"""
from typing import Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def split_documents(
    documents: list[Document],
    document_id: int,
    filename: str,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Document]:
    """
    Split a list of LangChain Documents into smaller chunks with rich hierarchical metadata.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "; ", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    valid_chunks = []
    chunk_idx = 0
    for chunk in chunks:
        content = chunk.page_content.strip()
        if not content or len(content) < 5:
            continue

        chunk.page_content = content
        
        # Preserve page number from loader if present
        page_num = chunk.metadata.get("page")
        if page_num is not None:
            try:
                page_num = int(page_num) + 1  # 1-indexed
            except Exception:
                page_num = None

        chunk.metadata.update(
            {
                "document_id": document_id,
                "category_id": category_id,
                "category_name": category_name or "",
                "type_id": type_id,
                "type_name": type_name or "",
                "filename": filename,
                "page_number": page_num,
                "chunk_index": chunk_idx,
            }
        )
        valid_chunks.append(chunk)
        chunk_idx += 1

    return valid_chunks
