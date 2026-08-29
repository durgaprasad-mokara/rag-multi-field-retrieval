"""
Document loader — dispatches to the right LangChain loader by file extension.
"""
import os
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    BSHTMLLoader,
    Docx2txtLoader,
)


def load_document(file_path: str) -> list[Document]:
    """
    Load a document from disk and return a list of LangChain Document objects.

    Supported formats: .pdf, .txt, .md, .docx, .csv, .html
    """
    ext = os.path.splitext(file_path)[1].lower()

    loader_map = {
        ".pdf": lambda: PyPDFLoader(file_path),
        ".txt": lambda: TextLoader(file_path, encoding="utf-8"),
        ".md": lambda: TextLoader(file_path, encoding="utf-8"),
        ".docx": lambda: Docx2txtLoader(file_path),
        ".csv": lambda: CSVLoader(file_path, encoding="utf-8"),
        ".html": lambda: BSHTMLLoader(file_path, open_encoding="utf-8"),
    }

    loader_factory = loader_map.get(ext)
    if loader_factory is None:
        raise ValueError(f"Unsupported file type: {ext}")

    loader = loader_factory()
    documents = loader.load()

    # Ensure each document has the source metadata
    for doc in documents:
        doc.metadata["source"] = file_path

    return documents
