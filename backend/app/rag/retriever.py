"""
Retriever — wraps the Qdrant vector store as a LangChain retriever with automatic chunk deduplication and document filtering.
Supports single document and multi-document filtered scopes.
"""
from typing import Optional, Any, Union, List
from pydantic import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from app.rag.vectorstore import get_vectorstore
from app.rag.deduplicator import deduplicate_documents


class DeduplicatedRetriever(BaseRetriever):
    """Retriever wrapper that strips exact and near-duplicate chunks."""
    base_retriever: Any = Field(...)
    similarity_threshold: float = 0.85

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> list[Document]:
        raw_docs = self.base_retriever.invoke(query)
        return deduplicate_documents(raw_docs, similarity_threshold=self.similarity_threshold)


def get_retriever(document_ids: Optional[Union[int, List[int]]] = None, k: int = 5) -> BaseRetriever:
    """
    Return a LangChain retriever backed by Qdrant with deduplication.

    Args:
        document_ids: Single document ID or list of document IDs to scope search.
        k: Number of top results to retrieve before deduplication.
    """
    vs = get_vectorstore()

    # Retrieve candidate chunks to account for deduplication
    search_kwargs: dict[str, Any] = {"k": max(k, 6)}

    if document_ids is not None:
        if isinstance(document_ids, (list, tuple, set)):
            ids_list = [int(i) for i in document_ids if i is not None]
            if len(ids_list) == 1:
                search_kwargs["filter"] = Filter(
                    must=[
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchValue(value=ids_list[0]),
                        )
                    ]
                )
            elif len(ids_list) > 1:
                search_kwargs["filter"] = Filter(
                    must=[
                        FieldCondition(
                            key="metadata.document_id",
                            match=MatchAny(any=ids_list),
                        )
                    ]
                )
        else:
            search_kwargs["filter"] = Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=int(document_ids)),
                    )
                ]
            )

    base = vs.as_retriever(search_type="similarity", search_kwargs=search_kwargs)
    return DeduplicatedRetriever(base_retriever=base)
