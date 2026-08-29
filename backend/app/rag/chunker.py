"""
Document chunker — splits documents into smaller pieces for embedding.
"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def split_documents(
    documents: list[Document],
    document_id: int,
    filename: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Document]:
    """
    Split a list of LangChain Documents into smaller chunks.

    Each chunk gets metadata: document_id, filename, chunk_index.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    # Enrich metadata for each chunk
    for i, chunk in enumerate(chunks):
        chunk.metadata.update(
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
            }
        )

    return chunks
