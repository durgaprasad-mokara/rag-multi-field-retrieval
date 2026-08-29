"""
Retriever — wraps the Qdrant vector store as a LangChain retriever.
"""
from typing import Optional
from langchain_core.retrievers import BaseRetriever
from app.rag.vectorstore import get_vectorstore


def get_retriever(document_id: Optional[int] = None, k: int = 5) -> BaseRetriever:
    """
    Return a LangChain retriever backed by Qdrant.

    Args:
        document_id: If provided, filter retrieval to only this document's chunks.
        k: Number of top results to return.
    """
    vs = get_vectorstore()

    search_kwargs = {"k": k}

    if document_id is not None:
        search_kwargs["filter"] = {
            "must": [
                {
                    "key": "metadata.document_id",
                    "match": {"value": document_id},
                }
            ]
        }

    return vs.as_retriever(search_type="similarity", search_kwargs=search_kwargs)
