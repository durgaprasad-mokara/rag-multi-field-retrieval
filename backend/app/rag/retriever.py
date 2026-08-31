"""
Retriever — wraps the Qdrant vector store as a LangChain retriever with automatic chunk deduplication,
document filtering, context compression, and dynamic token-budget management.
Supports single document and multi-document filtered scopes.
"""
from typing import Optional, Any, Union, List
from pydantic import Field
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from app.rag.vectorstore import get_vectorstore
from app.rag.deduplicator import deduplicate_documents, deduplicate_sentences, normalize_text


def compress_retrieved_context(documents: list[Document], max_token_chars: int = 4500) -> list[Document]:
    """
    Compress retrieved chunks to fit within the token budget, removing redundant sections and sentences.
    """
    compressed: list[Document] = []
    current_chars = 0
    seen_content = set()

    for doc in documents:
        clean = doc.page_content.strip()
        if not clean:
            continue
        
        # Deduplicate sentences within chunk
        clean = deduplicate_sentences(clean)
        norm = normalize_text(clean)
        if norm in seen_content:
            continue
        seen_content.add(norm)

        if current_chars + len(clean) > max_token_chars and compressed:
            break

        doc.page_content = clean
        compressed.append(doc)
        current_chars += len(clean)

    return compressed


class DeduplicatedRetriever(BaseRetriever):
    """Retriever wrapper that strips exact and near-duplicate chunks and compresses context."""
    base_retriever: Any = Field(...)
    similarity_threshold: float = 0.85
    max_context_chars: int = 4500

    def _get_relevant_documents(
        self, query: str, *, run_manager: Optional[CallbackManagerForRetrieverRun] = None
    ) -> list[Document]:
        raw_docs = self.base_retriever.invoke(query)
        deduped = deduplicate_documents(raw_docs, similarity_threshold=self.similarity_threshold)
        return compress_retrieved_context(deduped, max_token_chars=self.max_context_chars)


def get_retriever(
    document_ids: Optional[Union[int, List[int]]] = None,
    k: int = 5,
    target_response_time: Optional[float] = 2.0,
) -> BaseRetriever:
    """
    Return an optimized LangChain retriever backed by Qdrant with deduplication and token compression.

    Args:
        document_ids: Single document ID or list of document IDs to scope search.
        k: Number of top results to retrieve before deduplication.
        target_response_time: User's performance target in seconds to adapt k and context budget.
    """
    vs = get_vectorstore()

    # Dynamic k and token budget based on target response time
    if target_response_time is not None:
        if target_response_time <= 1.0:
            effective_k = min(k, 3)
            max_chars = 2500
        elif target_response_time <= 5.0:
            effective_k = k
            max_chars = 4500
        else:
            effective_k = max(k, 6)
            max_chars = 8000
    else:
        effective_k = k
        max_chars = 4500

    search_kwargs: dict[str, Any] = {"k": max(effective_k, 5)}

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
    return DeduplicatedRetriever(base_retriever=base, max_context_chars=max_chars)

