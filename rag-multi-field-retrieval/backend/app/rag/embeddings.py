"""
Embedding model — supports local FastEmbed (CPU, no API key needed) and OpenAI.
"""
import os
from functools import lru_cache
from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Return a singleton embeddings instance (local FastEmbed by default or OpenAI if configured)."""
    provider = os.getenv("EMBEDDING_PROVIDER", "fastembed").lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        return OpenAIEmbeddings(model=model)
    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        model = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(model_name=model)
    else:
        # Default local fastembed (ONNX, ultra fast, no API key required)
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
        model = os.getenv("FASTEMBED_MODEL", os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))
        if not model or "text-embedding" in model:
            model = "BAAI/bge-small-en-v1.5"
        return FastEmbedEmbeddings(model_name=model)

