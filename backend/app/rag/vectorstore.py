"""
Vector store abstraction — Integrates Qdrant (default) and ChromaDB.
"""
import os
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_qdrant import QdrantVectorStore
from langchain_chroma import Chroma
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointIdsList, Filter, FieldCondition, MatchValue
import chromadb

from app.rag.embeddings import get_embeddings

VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE", "qdrant").lower()

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "rag-multi-field-retrieval")
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")


def _get_qdrant_client() -> QdrantClient:
    """Return a Qdrant client instance."""
    return QdrantClient(url=QDRANT_URL)


def init_collection() -> None:
    """Create or recreate the collection for the active vector store."""
    if VECTOR_STORE_TYPE == "chroma":
        # Chroma creates the collection automatically upon instantiation.
        # Just ensure the directory exists.
        os.makedirs(CHROMA_PERSIST_DIRECTORY, exist_ok=True)
        print(f"ℹ️  ChromaDB directory ready: {CHROMA_PERSIST_DIRECTORY}")
        return

    # Qdrant Initialization
    client = _get_qdrant_client()
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
                    for k, v in vectors_config.items():
                        current_size = getattr(v, "size", None) or (v.get("size") if isinstance(v, dict) else None)
                        if current_size:
                            break

            if current_size is not None and current_size != embedding_dim:
                print(f"⚠️ Vector size mismatch (existing: {current_size}, model: {embedding_dim}). Recreating Qdrant collection '{COLLECTION_NAME}'...")
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
def get_vectorstore() -> VectorStore:
    """Return a singleton VectorStore instance (Qdrant or Chroma)."""
    embeddings = get_embeddings()
    
    if VECTOR_STORE_TYPE == "chroma":
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIRECTORY
        )
        
    # Default to Qdrant
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        url=QDRANT_URL,
    )


def add_documents(docs: list[Document], document_id: int) -> None:
    """Embed and upsert document chunks into the active vector store."""
    import uuid
    # Sanitize metadata to ensure compatibility with Chroma (which doesn't support UUID objects)
    for doc in docs:
        if hasattr(doc, "metadata"):
            for k, v in doc.metadata.items():
                if isinstance(v, uuid.UUID):
                    doc.metadata[k] = str(v)

    vs = get_vectorstore()
    
    # LangChain Chroma and Qdrant abstractions both support add_documents uniformly.
    vs.add_documents(docs)
    print(f"✅ Added {len(docs)} chunks for document_id={document_id} to {VECTOR_STORE_TYPE}")


def delete_by_document_id(document_id: str) -> None:
    """Remove all vectors associated with a document_id from the active vector store."""
    if VECTOR_STORE_TYPE == "chroma":
        vs = get_vectorstore()
        # Chroma allows deleting by metadata using the internal collection
        try:
            # Langchain's Chroma wrapper exposes the underlying chromadb collection via `_collection`
            vs._collection.delete(where={"document_id": str(document_id)})
            print(f"🗑️  Deleted vectors for document_id={document_id} from ChromaDB")
        except Exception as e:
            print(f"⚠️ Failed to delete document from ChromaDB: {e}")
        return

    # Qdrant Deletion
    client = _get_qdrant_client()
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
        print(f"🗑️  Deleted {len(all_point_ids)} vectors for document_id={document_id} from Qdrant")
