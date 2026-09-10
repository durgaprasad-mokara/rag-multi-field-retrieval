"""
Vector store — Qdrant integration for document storage and retrieval.
"""
import os
from functools import lru_cache

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointIdsList, Filter, FieldCondition, MatchValue

from app.rag.embeddings import get_embeddings

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "documents")


def _get_client() -> QdrantClient:
    """Return a Qdrant client instance."""
    return QdrantClient(url=QDRANT_URL)


def init_collection() -> None:
    """Create or recreate the Qdrant collection to match the active embedding model's dimension."""
    client = _get_client()
    embeddings = get_embeddings()
    sample_vector = embeddings.embed_query("test")
    embedding_dim = len(sample_vector)

    collections = [c.name for c in client.get_collections().collections]
    
    if COLLECTION_NAME in collections:
        try:
            collection_info = client.get_collection(COLLECTION_NAME)
            vectors_config = collection_info.config.params.vectors
            current_size = None
            
            if hasattr(vectors_config, "size"):
                current_size = vectors_config.size
            elif isinstance(vectors_config, dict):
                if "size" in vectors_config:
                    current_size = vectors_config["size"]
                else:
                    # Handle named vectors
                    for k, v in vectors_config.items():
                        current_size = getattr(v, "size", None) or (v.get("size") if isinstance(v, dict) else None)
                        if current_size:
                            break

            if current_size is not None and current_size != embedding_dim:
                print(f"⚠️ Vector size mismatch (existing: {current_size}, model: {embedding_dim}). Recreating collection '{COLLECTION_NAME}'...")
                client.delete_collection(COLLECTION_NAME)
                collections.remove(COLLECTION_NAME)
        except Exception as e:
            print(f"⚠️ Could not verify Qdrant collection size due to validation error: {e}. Assuming correct.")

    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=embedding_dim,
                distance=Distance.COSINE,
            ),
        )
        print(f"✅ Created Qdrant collection: {COLLECTION_NAME} (dimension: {embedding_dim})")
    else:
        print(f"ℹ️  Qdrant collection ready: {COLLECTION_NAME} (dimension: {embedding_dim})")


@lru_cache(maxsize=1)
def get_vectorstore() -> QdrantVectorStore:
    """Return a singleton QdrantVectorStore instance."""
    return QdrantVectorStore.from_existing_collection(
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        url=QDRANT_URL,
    )


def add_documents(docs: list[Document], document_id: int) -> None:
    """Embed and upsert document chunks into Qdrant."""
    vs = get_vectorstore()
    vs.add_documents(docs)
    print(f"✅ Added {len(docs)} chunks for document_id={document_id}")


def delete_by_document_id(document_id: str) -> None:
    """Remove all vectors associated with a document_id from Qdrant."""
    client = _get_client()

    # Scroll through all points matching this document_id and delete them
    offset = None
    all_point_ids = []

    while True:
        results, offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.document_id",
                        match=MatchValue(value=str(document_id)),
                    )
                ]
            ),
            limit=100,
            offset=offset,
        )
        all_point_ids.extend([p.id for p in results])
        if offset is None:
            break

    if all_point_ids:
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=PointIdsList(points=all_point_ids),
        )
        print(f"🗑️  Deleted {len(all_point_ids)} vectors for document_id={document_id}")
